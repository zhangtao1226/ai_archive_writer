# -*-coding  : utf-8 -*-
# @Author    : zhangtao
# @File      : project_service.py
# @Desc      : 服务入口文件
# @Time      : 2026/11/3 17:19
# @Software  : PyCharm

from services.task_service import TaskService
from uuid import uuid4
from datetime import datetime, timezone
from rag.query_builder import build_retrieval_query


def create_project(request, config):
    result = dict(
        task_id=str(uuid4()),
        status='queued',
        created_at=datetime.now(timezone.utc).isoformat(),
        parameters=request.model_dump(),
        group_snapshot=request.group_snapshot,
        outline_snapshot=request.outline_snapshot,
        retrieval_query=build_retrieval_query(
            title=request.title,
            type=request.type,
            description=request.description,
            time_range=request.time_range
        )
    )

    saved = TaskService(config.application_db_patth).create(result)
    result['updated_at'] = saved['updated_at']
    result['task_info'] = saved

    # 检索向量知识库 -> 再重排序, 将得到的结果丢给 LLM 进行推理, 推理完成后将生成的文本保存到 task_content表中

    return result
