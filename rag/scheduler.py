# -*-coding  : utf-8 -*-
# @Author    : zhangtao
# @File      : scheduler.py
# @Desc      : 服务生命周期内运行的夜间入库线程
# @Time      : 2026/11/6 10:50
# @Software  : PyCharm

import json
from services.material_vector_service import MaterialVectorService
from datetime import datetime, time
from hashlib import sha256
from pathlib import Path
from threading import Event, Thread
from zoneinfo import ZoneInfo

from core.LoggerDetector import logger
from rag.readers import extract_text


def in_window(now: time, start: time, end: time) -> bool:
    if start == end:
        return False
    return start <= now < end if start < end else now >= start or now < end


class IngestionScheduler:
    def __init__(self, config):
        self.config = config
        self.stop_event = Event()
        self.thread = Thread(target=self.run, name="rag-ingestion", daemon=False)
        self.start_time = time.fromisoformat(config.start_time)
        self.end_time = time.fromisoformat(config.end_time)
        if self.start_time == self.end_time:
            raise ValueError("start_time 与 end_time 不能相同")
        self.zone = ZoneInfo(config.rag_timezone)
        self.kb = None
        self.records = MaterialVectorService(config.application_db_patth)

    def allowed(self):
        return not self.stop_event.is_set() and in_window(
            datetime.now(self.zone).time(), self.start_time, self.end_time)

    def start(self):
        source_dir = Path(self.config.rag_source_dir).expanduser()
        source_dir.mkdir(parents=True, exist_ok=True)
        logger.info("知识库资料目录：{}", source_dir.resolve())
        self.thread.start()

    def stop(self):
        self.stop_event.set()
        self.thread.join()

    def run(self):
        while not self.stop_event.is_set():
            try:
                if self.allowed():
                    self.scan()
            except Exception:
                logger.exception("夜间知识库入库失败，下次扫描重试")
            self.stop_event.wait(self.config.rag_scan_interval_seconds)

    def scan(self):
        source_dir = Path(self.config.rag_source_dir).expanduser()
        if not source_dir.is_dir():
            logger.warning("知识库资料目录不存在：{}", source_dir)
            return
        self.records.initialize()
        signature = sha256(json.dumps({"model": self.config.embedding_model_path,
            "chunk_size": 800, "overlap": 120, "parser_version": 1,
            "collection": "archive_knowledge"}, sort_keys=True).encode()).hexdigest()
        for path in sorted(source_dir.rglob("*")):
            if not self.allowed():
                break
            if any(part.startswith('._') or part == '__MACOSX' for part in path.relative_to(source_dir).parts):
                continue
            if not path.is_file() or path.suffix.lower() not in {".txt", ".md", ".pdf", ".docx"}:
                continue
            record = None
            try:
                source = str(path.resolve())
                data = path.read_bytes()
                digest = sha256(data).hexdigest()
                record = self.records.claim(source, digest, signature,
                    getattr(self.config, 'rag_default_category_id', 'unassigned'))
                if record is None:
                    continue
                def can_continue():
                    return self.allowed() and self.records.active(record['id'])
                if not can_continue():
                    raise InterruptedError('入库窗口结束或记录被停用')
                text = extract_text(data, path.suffix)
                if self.kb is None:
                    from rag.indexing import KnowledgeBase
                    self.kb = KnowledgeBase()
                info = self.kb.write(text, source=source, metadata={
                    'category_id': record['category_id'], 'ingestion_id': record['id'],
                    'content_hash': digest}, should_continue=can_continue, return_info=True)
                self.records.finish(record['id'], 'completed', info=info)
                logger.info(f"资料入库处理结束：{source}")
            except InterruptedError as exc:
                if record:
                    self.records.finish(record['id'], 'interrupted', error=str(exc))
            except Exception as exc:
                if record:
                    self.records.finish(record['id'], 'failed', error=str(exc))
                logger.exception(f"资料入库未完成：{path}")
