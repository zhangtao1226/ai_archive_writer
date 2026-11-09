# -*-coding  : utf-8 -*-
# @Author    : zhangtao
# @File      : main.py
# @Desc      : 服务入口文件
# @Time      : 2026/11/3 17:19
# @Software  : PyCharm

from contextlib import asynccontextmanager
import asyncio
from fastapi import FastAPI, Request
from core.config import configs
from core.db import close_database_pools
from rag.scheduler import IngestionScheduler


from core.LoggerDetector import logger
from core.ResponseUtil import ResponseUtil
from pydantic import ValidationError
from sqlalchemy.exc import SQLAlchemyError
from sqlite3 import Error as SQLiteError
from schemas.EditingResearchRequest import EditingResearchRequest
from services.project_service import create_project
from services.task_service import TaskService
from services.task_content_service import TaskContentService
from services.generation_service import GenerationWorker

@asynccontextmanager
async def lifespan(app):
    await asyncio.to_thread(TaskService().initialize)
    await asyncio.to_thread(TaskContentService().initialize)
    worker = GenerationWorker(configs)
    worker.start()
    scheduler = IngestionScheduler(configs) if configs.rag_scheduler_enabled else None
    if scheduler:
        scheduler.start()
        logger.info(f"启动素材库定时写入向量知识库中")
    try:
        yield
    finally:
        try:
            await asyncio.to_thread(worker.stop)
            if scheduler:
                await asyncio.to_thread(scheduler.stop)
        finally:
            await asyncio.to_thread(close_database_pools)



app = FastAPI(lifespan=lifespan, title="AI 档案编研系统",
              description="档案编研任务、资料管理、正文生成与成果导出服务。",
              version="1.0.0",)


@app.get("/")
async def health_check():
    message = "服务正在运行中·······"
    logger.info(f"检查服务运行状态: {message}")
    return ResponseUtil.success(message=message)

@app.post("/v1/editing_research")
async def editing_research(request: Request):
    try:
        json_data = await request.json()
    except ValueError:
        return ResponseUtil.error(code=422, message="请求体必须是合法 JSON")
    if not isinstance(json_data, dict):
        return ResponseUtil.error(code=422, message="请求体必须是 JSON 对象")

    required = ("user_id", "title", "type", "person", "group", "directory_template")
    missing = [key for key in required if key not in json_data or json_data[key] is None
               or (isinstance(json_data[key], str) and not json_data[key].strip())]
    if missing:
        return ResponseUtil.error(message=f"缺少必要参数: {', '.join(missing)}")
    try:
        parameters = EditingResearchRequest.model_validate(json_data)
    except ValidationError as exc:
        return ResponseUtil.error(
            code=422,
            message="立项参数校验失败",
            details={"errors": exc.errors(include_context=False, include_input=False)}
        )
    try:
        project = await asyncio.to_thread(create_project, parameters, configs)
    except (SQLAlchemyError, SQLiteError, TimeoutError):
        logger.exception("编研立项保存失败")
        return ResponseUtil.error(code=503, message="立项保存失败，请稍后重试")
    except (OSError, ValidationError):
        logger.exception("立项保存参数或存储不可用")
        return ResponseUtil.error(code=503, message="立项保存失败，参数或存储不可用")
    except ValueError as exc:
        return ResponseUtil.error(message=str(exc))
    return ResponseUtil.success(data=project, message="立项已保存，任务已排队")

@app.get("/v1/tasks_info/{task_id}")
async def get_tasks_info(task_id: str):
    if not task_id.strip():
        return ResponseUtil.error(code=422, message="task_id 不能为空")
    try:
        result = await asyncio.to_thread(TaskService().get_task_result, task_id.strip())
    except (SQLAlchemyError, SQLiteError, TimeoutError):
        logger.exception("任务信息查询失败")
        return ResponseUtil.error(code=503, message="任务信息查询失败，请稍后重试")
    except (ValueError, TypeError):
        logger.exception("任务数据格式异常")
        return ResponseUtil.error(code=500, message="任务数据格式异常，请联系管理员")
    if result is None:
        return ResponseUtil.error(code=404, message="任务不存在")
    return ResponseUtil.success(data=result, message=result['status'])

# 对话接口



if __name__ == '__main__':
    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)