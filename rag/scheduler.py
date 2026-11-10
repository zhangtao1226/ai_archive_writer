# -*-coding  : utf-8 -*-
# @Author    : zhangtao
# @File      : scheduler.py
# @Desc      : 服务生命周期内运行的夜间入库线程
# @Time      : 2026/11/6 10:50
# @Software  : PyCharm

from core.db import get_database_pool
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
        state_path = Path(self.config.knowledge_db_patth) / "ingestion_state.sqlite3"
        with get_database_pool(state_path).connection() as state:
            state.execute("CREATE TABLE IF NOT EXISTS files (path TEXT PRIMARY KEY, digest TEXT)")
            for path in sorted(source_dir.rglob("*")):
                if not self.allowed():
                    break
                if any(part.startswith('._') or part == '__MACOSX' for part in path.relative_to(source_dir).parts):
                    continue
                if not path.is_file() or path.suffix.lower() not in {".txt", ".md", ".pdf", ".docx"}:
                    logger.warning("未读取到资料", path)
                    continue
                try:
                    # 写事务串行化多个服务进程，成功后才记录内容指纹。
                    state.execute("BEGIN IMMEDIATE")
                    source = str(path.resolve())
                    data = path.read_bytes()
                    digest = sha256(data).hexdigest()
                    row = state.execute("SELECT digest FROM files WHERE path=?", (source,)).fetchone()
                    if row and row[0] == digest:
                        state.rollback()
                        continue
                    if self.kb is None:
                        from rag.indexing import KnowledgeBase
                        self.kb = KnowledgeBase()
                    if not self.allowed():
                        state.rollback()
                        break
                    self.kb.write(extract_text(data, path.suffix), source=source, should_continue=self.allowed)
                    state.execute("INSERT OR REPLACE INTO files VALUES (?, ?)", (source, digest))
                    state.commit()
                    logger.info("知识库入库成功：{}", source)
                except Exception:
                    state.rollback()
                    logger.exception("资料入库未完成：{}", path)
