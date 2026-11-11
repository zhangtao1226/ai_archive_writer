# -*-coding  : utf-8 -*-
# @Author    : zhangtao
# @File      : material_vector_service.py
# @Desc      : 
# @Time      : 2026/11/11 14:35
# @Software  : PyCharm

import json
from sqlalchemy import select
from core.db import get_database_pool, orm_session
from models.material_vector_model import MaterialVectorModel, utc_now


class MaterialVectorService:
    def __init__(self, path):
        self.pool = get_database_pool(path)

    def initialize(self):
        with orm_session(self.pool, immediate=True) as session:
            MaterialVectorModel.__table__.create(session.connection(), checkfirst=True)

    def claim(self, source, digest, signature, category_id='unassigned'):
        with orm_session(self.pool, immediate=True) as session:
            previous = session.scalars(select(MaterialVectorModel).where(
                MaterialVectorModel.source_path == source).order_by(MaterialVectorModel.created_at.desc())).all()
            # 同一路径关闭、删除或正在处理时，不以新版本绕过管理状态。
            if any(r.is_deleted or not r.enabled or r.status == 'running' for r in previous):
                return None
            if previous:
                category_id = previous[0].category_id
            row = next((r for r in previous if r.content_hash == digest and r.index_signature == signature), None)
            if row and row.status == 'completed':
                return None
            if row is None:
                row = MaterialVectorModel(category_id=category_id, source_path=source,
                                          content_hash=digest, index_signature=signature)
                session.add(row)
            else:
                row.retry_count += 1
            row.status = 'running'
            row.started_at = utc_now()
            row.completed_at = None
            row.error_message = ''
            session.flush()
            return {'id': row.id, 'category_id': row.category_id}

    def active(self, record_id):
        with orm_session(self.pool) as session:
            row = session.get(MaterialVectorModel, record_id)
            return bool(row and row.enabled and not row.is_deleted and row.status == 'running')

    def finish(self, record_id, status, info=None, error=''):
        with orm_session(self.pool, immediate=True) as session:
            row = session.get(MaterialVectorModel, record_id)
            if row is None:
                return
            if status == 'completed' and (not row.enabled or row.is_deleted):
                status = 'interrupted'
            row.status = status
            row.error_message = error[:4000]
            if info is not None:
                row.vector_info = json.dumps(info, ensure_ascii=False)
            row.completed_at = utc_now() if status == 'completed' else None
            row.updated_at = utc_now()