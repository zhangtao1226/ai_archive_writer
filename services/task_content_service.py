# -*-coding  : utf-8 -*-
# @Author    : zhangtao
# @File      : task_content_service.py
# @Desc      :
# @Time      : 2026/11/6 10:50
# @Software  : PyCharm
import json
from datetime import datetime, timezone
from uuid import uuid4
from sqlalchemy import select
from core.db import get_database_pool, orm_session
from models.task_model import TaskModel
from models.task_content_model import TaskContentModel


class TaskContentService:
    def __init__(self, db_path=None):
        if db_path is None:
            from core.config import configs
            db_path = configs.application_db_patth
        self.pool = get_database_pool(db_path)

    def initialize(self):
        with orm_session(self.pool, immediate=True) as session:
            TaskContentModel.metadata.create_all(session.connection())

    @staticmethod
    def _decode(model):
        return {c.name: getattr(model, c.name) for c in TaskContentModel.__table__.columns}

    @staticmethod
    def _query(task_id, user_id):
        return select(TaskContentModel).join(TaskModel).where(
            TaskModel.task_id == task_id, TaskModel.user_id == user_id)

    def create(self, task_id, user_id, section_id, body, model_name=''):
        if not isinstance(body, str) or not body.strip() or not isinstance(model_name, str):
            raise ValueError('正文必须为非空字符串，模型名称必须为字符串')
        with orm_session(self.pool, immediate=True) as session:
            task = session.scalar(select(TaskModel).where(TaskModel.task_id == task_id, TaskModel.user_id == user_id))
            if task is None:
                raise ValueError('任务不存在或无权访问')
            node = next((n for n in json.loads(task.outline_snapshot).get('nodes', []) if n['id'] == section_id), None)
            if not node or not node.get('generate_body'):
                raise ValueError('章节不存在或不是正文节点')
            if session.scalar(self._query(task_id, user_id).where(TaskContentModel.section_id == section_id)):
                raise ValueError('章节正文已存在，请使用带修订号的更新操作')
            now = datetime.now(timezone.utc).isoformat()
            model = TaskContentModel(
                content_id=str(uuid4()),
                task_id=task_id,
                section_id=section_id,
                title=node['title'],
                body=body,
                model_name=model_name,
                revision=1,
                created_at=now,
                updated_at=now
            )
            session.add(model)
            session.flush()
            return self._decode(model)

    def get(self, task_id, user_id, section_id):
        with orm_session(self.pool) as session:
            model = session.scalar(self._query(task_id, user_id).where(TaskContentModel.section_id == section_id))
            return self._decode(model) if model else None

    def list(self, task_id, user_id, limit=20, offset=0):
        if type(limit) is not int or type(offset) is not int or not 1 <= limit <= 100 or offset < 0:
            raise ValueError('分页参数无效')
        with orm_session(self.pool) as session:
            return [self._decode(m) for m in session.scalars(self._query(task_id, user_id).order_by(
                TaskContentModel.created_at, TaskContentModel.content_id).limit(limit).offset(offset))]

    def update(self, task_id, user_id, section_id, body, expected_revision):
        if not isinstance(body, str) or not body.strip():
            raise ValueError('正文必须为非空字符串')
        return self._change(task_id, user_id, section_id, expected_revision, body)

    def delete(self, task_id, user_id, section_id, expected_revision):
        return self._change(task_id, user_id, section_id, expected_revision, None)

    def _change(self, task_id, user_id, section_id, expected_revision, body):
        if type(expected_revision) is not int or expected_revision < 1:
            raise ValueError('修订号必须为正整数')
        with orm_session(self.pool, immediate=True) as session:
            model = session.scalar(self._query(task_id, user_id).where(TaskContentModel.section_id == section_id))
            if model is None:
                return False
            if model.revision != expected_revision:
                raise ValueError('正文已更新，请刷新后重试')
            if body is None:
                session.delete(model)
            else:
                model.body = body
                model.revision += 1
                model.updated_at = datetime.now(timezone.utc).isoformat()
            return True
