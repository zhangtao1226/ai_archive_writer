# -*-coding  : utf-8 -*-
# @Author    : zhangtao
# @File      : task_service.py
# @Desc      : 编研任务立项
# @Time      : 2026/11/6 10:50
# @Software  : PyCharm

import json
from datetime import datetime, timezone
from sqlalchemy import select, inspect, Table, MetaData, values
from sqlalchemy.dialects.mssql.information_schema import columns

from core.db import get_database_pool, orm_session
from models.task_model import TaskModel
from services.citation_codec import decode_citations
from services.research_mode import resolve_research_mode

class DuplicateTaskError(ValueError):
    pass

class TaskService:
    def __init__(self, db_path=None):
        if db_path is None:
            from core.config import configs
            db_path = configs.application_db_path
        self.pool = get_database_pool(db_path)

    def initialize(self):
        with orm_session(self.pool, immediate=True) as session:
            TaskModel.metadata.create_all(session.connection())

    @staticmethod
    def _model(record):
        p = record['parameters']
        return TaskModel(
            task_id=record.get('task_id') or record['project_id'],
            user_id=p['user_id'] or '',
            title=p['title'],
            research_type=p['type'],
            responsible_user_id=p['person'] or '',
            group=p['group'] or '',
            directory_template=json.dumps(p['directory_template'], ensure_ascii=False),
            time_range=p.get('time_range', ''),
            description=p.get('description', ''),
            status=record['status'],
            retrieval_query=record.get('retrieval_query', ''),
            group_snapshot=json.dumps(record['group_snapshot'], ensure_ascii=False),
            outline_snapshot=json.dumps(record['outline_snapshot'], ensure_ascii=False),
            created_at=record['created_at'],
            updated_at=record.get('updated_at', record['created_at'])
        )

    def create(self, record):
        self.initialize()
        with orm_session(self.pool, immediate=True) as session:
            model = self._model(record)
            print(model)
            if session.get(TaskModel, model.task_id) is not None:
                raise DuplicateTaskError(f"taskid 已经存在: {model.task_id}, 请查询已有任务; 新立项请使用新的 taskid")
            session.add(model)
            session.flush()
            saved = self._decode(model)
        return saved

    @staticmethod
    def _owned(task_id, user_id):
        return select(TaskModel).where(TaskModel.task_id == task_id, TaskModel.user_id == user_id)

    @staticmethod
    def _decode(model):
        result = {column.name: getattr(model, column.name) for column in TaskModel.__table__.columns}
        for key in ('group_snapshot', 'outline_snapshot'):
            result[key] = json.loads(result[key])
        return result

    def get(self, task_id, user_id):
        with orm_session(self.pool) as session:
            model = session.scalar(self._owned(task_id, user_id))
            return self._decode(model) if model else None

    def list(self, user_id, limit=20, offset=0):
        if type(limit) is not int or type(offset) is not int or not 1 <= limit <= 100 or offset < 0:
            raise ValueError('分页参数无效')
        with orm_session(self.pool) as session:
            query = select(TaskModel).where(TaskModel.user_id == user_id).order_by(
                TaskModel.created_at.desc(), TaskModel.task_id).limit(limit).offset(offset)

            return [self._decode(model) for model in session.scalars(query)]

    def update(self, task_id, user_id, **changes):
        # 模板、成员和身份变更必须通过业务校验，不允许通用更新绕过。
        allowed = {'title', 'description', 'time_range', 'retrieval_query', 'status'}
        if not changes or changes.keys() - allowed:
            raise ValueError('包含不允许修改的字段或没有修改内容')
        if any(not isinstance(value, str) for value in changes.values()):
            raise ValueError('字段值必须是字符串')
        if 'title' in changes and not changes['title'].strip():
            raise ValueError('标题不能为空')
        if 'status' in changes and changes['status'] not in {'created', 'queued', 'running', 'completed', 'failed', 'cancelled'}:
            raise ValueError('任务状态无效')
        changes['updated_at'] = datetime.now(timezone.utc).isoformat()
        with orm_session(self.pool, immediate=True) as session:
            model = session.scalar(self._owned(task_id, user_id))
            if model is None:
                return False
            for key, value in changes.items():
                setattr(model, key, value)
            return True

    def delete(self, task_id, user_id):
        with orm_session(self.pool, immediate=True) as session:
            model = session.scalar(self._owned(task_id, user_id))
            if model is None:
                return False
            session.delete(model)
            return True

    def get_task_result(self, task_id):
        """在同一读事务中查询任务及完成后的全部章节正文。"""
        from models.task_content_model import TaskContentModel
        with orm_session(self.pool) as session:
            task = session.get(TaskModel, task_id)
            if task is None:
                return None
            labels = {
                'created': '任务进行中',
                'queued': '任务进行中',
                'running': '任务进行中',
                'completed': '任务已完成',
                'failed': '任务失败',
                'cancelled': '任务已取消'
            }

            result = {
                'task_id': task.task_id,
                'status': labels.get(task.status, '任务状态未知'),
                'status_code': task.status
            }

            if task.status == 'completed':
                task_info = self._decode(task)
                mode, columns = resolve_research_mode(task_info['outline_snapshot'], task.research_type)
                rows = session.scalars(
                    select(TaskContentModel)
                    .where(
                        TaskContentModel.task_id == task_id
                    )
                    .order_by(
                        TaskContentModel.created_at, TaskContentModel.content_id
                    )
                ).all()

                contents = [{c.name: getattr(row, c.name)
                                       for c in TaskContentModel.__table__.columns} for row in rows]
                for content in contents:
                    content['citations'] = decode_citations(content['citations'])
                    if mode == 'single_node':
                        content['table'] = json.loads(content['body'])
                        if not isinstance(content['table'], dict) and all(isinstance(v, list) for v in content['table'].values()):
                            from schemas.excel_content import parse_excel_content
                            table = parse_excel_content(content['body'])
                            content['table'] = {
                                'format': 'chronology_columns',
                                'columns': list(table),
                                'nodes': [
                                    {
                                        'title': key,
                                        'level': 1,
                                        'content': values,
                                        'source': [[] for _ in values],
                                    } for key, values in table.items()
                                ]
                            }

                        if not isinstance(content['table'], dict) or content['table'].get('columns') != columns:
                            raise ValueError('已保存的大事记内容不是匹配表头数据， 需要重新生成')

                order = self._outline_order(task_info['outline_snapshot'])
                contents.sort(key=lambda row: order.get(row['section_id'], len(order)))

                for content in contents:
                    content['citations'] = decode_citations(content['citations'])
                    if task_info['outline_snapshot'].get('direction_model') == 'single_node':
                        content['table'] = json.loads(content['body'])

                from services.outline_service import fill
                tree = task_info['outline_snapshot'].get('tree', [])
                result['directory_template'] = fill(tree, contents)

                if mode == 'single_node':
                    from services.table_result import table_to_nodes
                    if len(contents) != 1:
                        raise ValueError('大事记应包含一个完整表格')
                    result['directory_template'] = table_to_nodes(contents[0]['table'])
                    contents[0]['nodes'] = result['directory_template']
                result['content_count'] = len(contents)
                result['has_content'] = bool(contents)
            return result

    @staticmethod
    def _outline_order(snapshot):
        nodes = snapshot.get('nodes', []) if isinstance(snapshot, dict) else []
        if not isinstance(nodes, list):
            return {}
        children = {}
        for node in nodes:
            if not isinstance(node, dict) or not isinstance(node.get('id'), str):
                continue
            parent = node.get('parent_id')
            if parent is not None and not isinstance(parent, str):
                continue
            children.setdefault(parent, []).append(node)
        for siblings in children.values():
            siblings.sort(key=lambda n: n['order'] if type(n.get('order')) is int else 0)
        order = {}
        stack = list(reversed(children.get(None, [])))
        while stack:
            node = stack.pop()
            if node['id'] in order:
                continue
            order[node['id']] = len(order)
            stack.extend(reversed(children.get(node['id'], [])))
        return order
