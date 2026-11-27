# -*-coding : utf-8 -*-
# @Author   : zhangtao
# @FileName : material_callback_service.py
# @Desc     : 
# @Time     : 2026/11/27 10:40
# @Software : PyCharm

from datetime import datetime, timezone, timedelta
from sqlalchemy import select

from core.db import get_database_pool, orm_session
from models.material_callback_model import MaterialCallbackModel as Callback

class MaterialCallbackService:
    def __init__(self, config):
        self.config = config
        self.pool = get_database_pool(config.application_db_path)

    def initialize(self):
        with orm_session(self.pool, immediate=True) as session:
            Callback.__table__.create(session.connection(), checkfirst=True)

    def enqueue(self, category, material, version, success):
        with orm_session(self.pool, immediate=True) as session:
            row = session.get(Callback, (category, material))
            if row and row.version == version and row.success == int(success):
                return
            if row is None:
                row = Callback(category_id = category, material_id = material)
                session.add(row)

            row.version, row.success, row.status = version, int(success), 'pending'
            row.attempts, row.next_attempt, row.error = 0, '', ''

    def flush(self, api, allowed):
        now = datetime.now(timezone.utc).isoformat()
        with orm_session(self.pool) as session:
            pending = [(r.category_id, r.material_id) for r in session.scalars(
                select(Callback)
                .where(
                    Callback.status == 'pending',
                    Callback.next_attempt <= now,
                )
            )]

        for key in pending:
            if not allowed():
                break

            with orm_session(self.pool, immediate=True) as session:
                row = session.get(Callback, key)
                if row.status != 'pending':
                    continue

                row.attempts += 1
                try:
                    api.callback(
                        {
                            'category_id': row.category_id,
                            'material_id': row.material_id,
                            'success': bool(row.success)
                        }
                    )

                    row.status, row.error = 'sent', ''
                except Exception as exc:
                    row.error = str(exc)[:2000]
                    delay = min(3600, self.config.material_callback_retry_seconds * 2 ** min(row.attempts - 1, 6))
                    row.next_attempt = (datetime.now(timezone.utc) + timedelta(seconds=delay)).isoformat()