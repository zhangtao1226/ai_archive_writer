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
        self.records = MaterialVectorService(config.application_db_path)

    def allowed(self):
        return not self.stop_event.is_set() and in_window(
            datetime.now(self.zone).time(), self.start_time, self.end_time)

    def start(self):
        if not self.config.material_api_base_url:
            raise ValueError('定时入库需要配置 material_api_base_url')
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
        from services.material_catalog_service import MaterialCatalogClient, iter_materials, material_text
        from services.material_callback_service import MaterialCallbackService
        from urllib.parse import quote
        callbacks = MaterialCallbackService(self.config)
        self.records.initialize()
        callbacks.initialize()
        signature = sha256(json.dumps({'model':self.config.embedding_model_path,'chunk_size':800,
            'overlap':120,'parser_version':2},sort_keys=True).encode()).hexdigest()
        with MaterialCatalogClient(self.config) as api:
            callbacks.flush(api,self.allowed)
            materials = list(iter_materials(api.categories()))
            for category, info, material in materials:
                if not self.allowed(): break
                base = 'material://' + quote(category,safe='') + '/' + quote(material['id'],safe='')
                versions = []
                errors = []
                interrupted = False
                metadata = {'category_id':category,'material_id':material['id'],
                    'catalog_path':info.get('catalog_path',''), 'title':material.get('tm',''),
                    'archive_code':material.get('dh','')}
                def ingest(data, suffix, source, meta):
                    digest=sha256(data).hexdigest()
                    versions.append((source,digest))
                    record=self.records.claim(source,digest,signature,category)
                    if record is None:
                        if self.records.completed(source,digest,signature): return
                        raise InterruptedError('素材已停用、删除或由其他任务处理')
                    try:
                        def allowed(): return self.allowed() and self.records.active(record['id'])
                        if not allowed(): raise InterruptedError('入库窗口结束')
                        text=extract_text(data,suffix)
                        if self.kb is None:
                            from rag.indexing import KnowledgeBase
                            self.kb=KnowledgeBase()
                        old_ids = self.kb.collection.get(where={'source':source})['ids']
                        vector_info=self.kb.write(text,source=source,metadata={**meta,
                            'ingestion_id':record['id'],'content_hash':digest},should_continue=allowed,return_info=True)
                        stale = sorted(set(old_ids) - set(vector_info['chunk_ids']))
                        if stale:
                            self.kb.collection.delete(ids=stale)
                        self.records.finish(record['id'],'completed',info=vector_info)
                        if not self.records.completed(source,digest,signature): raise InterruptedError('素材状态变化')
                    except InterruptedError as exc:
                        self.records.finish(record['id'],'interrupted',error=str(exc)); raise
                    except Exception as exc:
                        self.records.finish(record['id'],'failed',error=str(exc)); raise
                try:
                    ingest(material_text(info,material).encode(),'.txt',base+'/description',
                           {**metadata,'source_type':'description'})
                except InterruptedError: interrupted=True
                except Exception as exc: errors.append(str(exc))
                attachments=material.get('attachments') or []
                if not isinstance(attachments,list):
                    errors.append('attachments 必须为数组'); attachments=[]
                for attachment in attachments:
                    if interrupted or not self.allowed(): interrupted=True; break
                    try:
                        if not isinstance(attachment,dict) or not attachment.get('attachment_id'):
                            raise ValueError('附件缺少 attachment_id')
                        data=api.attachment(attachment,self.allowed)
                        ingest(data,'.'+attachment.get('file_ext','').lower().lstrip('.'),
                            base+'/attachment/'+quote(attachment['attachment_id'],safe=''),
                            {**metadata,'source_type':'attachment','attachment_id':attachment['attachment_id'],
                             'file_name':attachment.get('file_name','')})
                    except InterruptedError: interrupted=True; break
                    except Exception as exc: errors.append(str(exc))
                if interrupted: continue
                version=sha256(json.dumps([material,versions,signature],sort_keys=True,ensure_ascii=False).encode()).hexdigest()
                callbacks.enqueue(category,material['id'],version,not errors)
                if errors: logger.error(f'素材入库失败 category_id={category} material_id={material["id"]} errors={errors}')
                callbacks.flush(api,self.allowed)
