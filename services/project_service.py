# -*-coding  : utf-8 -*-
# @Author    : zhangtao
# @File      : project_service.py
# @Desc      : 服务入口文件
# @Time      : 2026/11/3 17:19
# @Software  : PyCharm

from uuid import uuid4
from datetime import datetime, timezone
from rag.query_builder import build_retrieval_query

from services.outline_service import flatten
from services.task_service import TaskService


def create_project(request, config):
    tree = [node.model_dump() for node in request.directory_template]
    result = dict(
        task_id=request.taskid or str(uuid4()),
        status='queued',
        created_at=datetime.now(timezone.utc).isoformat(),
        parameters=request.model_dump(),
        group_snapshot=request.group_snapshot,
        outline_snapshot={
            **request.outline_snapshot,
            'tree': tree,
            'nodes': flatten(tree)
        },
        retrieval_query=build_retrieval_query(
            title=request.title,
            type=request.type,
            description=request.description,
            time_range=request.time_range
        )
    )

    re_data = dict(
        task_id=request.taskid or str(uuid4()),
        status='queued',
        created_at=datetime.now(timezone.utc).isoformat()
    )

    saved = TaskService(config.application_db_path).create(result)
    result['updated_at'] = saved['updated_at']
    result['task_info'] = saved
    return re_data
