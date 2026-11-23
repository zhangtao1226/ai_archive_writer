# -*-coding  : utf-8 -*-
# @Author    : zhangtao
# @File      : main.py
# @Desc      : 服务入口文件
# @Time      : 2026/11/3 17:19
# @Software  : PyCharm

import asyncio
from queue import Queue, Empty
from threading import Event, Thread
from contextlib import asynccontextmanager
from fastapi.responses import StreamingResponse
from fastapi import FastAPI, Request, Depends, HTTPException
from pydantic import ValidationError
from sqlite3 import Error as SQLiteError
from sqlalchemy.exc import SQLAlchemyError


from core.config import configs
from core.db import close_database_pools
from core.LoggerDetector import logger
from core.ResponseUtil import ResponseUtil
from rag.scheduler import IngestionScheduler
from schemas.EditingResearchRequest import EditingResearchRequest
from schemas.ChatRequest import ChatRequest, TextChatRequest
from services.chat_stream import sse
from services.project_service import create_project
from services.research_parameter_adapter import normalize_research_request
from services.task_service import TaskService, DuplicateTaskError
from services.task_content_service import TaskContentService
from services.chat_service import ChatService
from services.generation_service import GenerationWorker

@asynccontextmanager
async def lifespan(app):
    """初始化数据库和后台任务，退出时等待任务结束并关闭连接池。"""
    await asyncio.to_thread(TaskService().initialize)
    await asyncio.to_thread(TaskContentService().initialize)
    app.state.chat_service = ChatService(configs)
    await asyncio.to_thread(app.state.chat_service.initialize)
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
    """返回服务存活状态。"""
    message = "服务正在运行中·······"
    logger.info(f"检查服务运行状态: {message}")
    return ResponseUtil.success(message=message)

@app.post("/v1/editing_research")
async def editing_research(request: Request):
    """校验并保存立项请求，将任务加入持久化生成队列。"""
    try:
        json_data = await request.json()
    except ValueError:
        return ResponseUtil.error(code=422, message="请求体必须是合法 JSON")
    if not isinstance(json_data, dict):
        return ResponseUtil.error(code=422, message="请求体必须是 JSON 对象")

    is_new_format = 'direction_model' in json_data
    try:
        context = {key: getattr(request.state, key, None) for key in ('user_id', 'person', 'group')}
        json_data = normalize_research_request(json_data, context)
    except ValidationError as exc:
        return ResponseUtil.error(code=422, message="立项参数校验失败",
            details={"errors": exc.errors(include_context=False, include_input=False)})
    except ValueError as exc:
        return ResponseUtil.error(code=422, message=str(exc))

    required = ("taskid", "title", "type", "directory_template") if is_new_format else (
        "user_id", "title", "type", "person", "group", "directory_template")
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
    except DuplicateTaskError as exc:
        return ResponseUtil.error(code=409, message=str(exc))
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
    """根据任务ID返回状态以及完成后的正文和引用。"""
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


def chat_user(user_id: str):
    """接收 Java 传入的用户标识用于会话隔离，不执行登录或分配权限校验。"""
    if not user_id.strip():
        raise HTTPException(status_code=422, detail="user_id 不能为空")
    return user_id


async def call_chat_service(request, method, *args):
    """在线程中调用同步服务并统一转换业务异常。"""
    try:
        result = await asyncio.to_thread(getattr(request.app.state.chat_service, method), *args)
        return ResponseUtil.success(data=result)
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc))
    except ValueError as exc:
        return ResponseUtil.error(code=409, message=str(exc))
    except Exception:
        logger.exception("章节对话处理失败")
        return ResponseUtil.error(code=503, message="对话服务暂不可用，请稍后重试")


@app.post("/v1/chat")
async def chat(payload: TextChatRequest, request: Request):
    """按用户、任务和节点恢复会话，以当前编辑文本执行流式修改。"""
    user_id = payload.user_id
    try:
        chat_request = await asyncio.to_thread(request.app.state.chat_service.prepare_text_request, payload)
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc))
    except ValueError as exc:
        return ResponseUtil.error(code=422, message=str(exc))

    queue = Queue(maxsize=128)
    cancelled = Event()

    def emit(event, data):
        from queue import Full
        while not cancelled.is_set():
            try:
                queue.put((event, data), timeout=0.2)
                return
            except Full:
                continue
        raise InterruptedError('客户端已断开')

    def generate():
        """在线程中运行同步检索及推理，异常转为 SSE error。"""
        try:
            result = request.app.state.chat_service.chat(chat_request, user_id, emit, cancelled)
            emit('done' if result['status'] == 'completed' else 'status', result)
        except Exception:
            logger.exception('流式对话失败')
            if not cancelled.is_set():
                emit('error', {'message':'生成失败，请查询历史记录或稍后重试'})

    async def events():
        """发送开始事件、正文片段和心跳；退出时通知生成线程取消。"""
        thread = Thread(target=generate, name='chat-stream')
        thread.start()
        try:
            yield sse(
                'start',
                {
                    'task_id':payload.task_id,
                    'node_id':payload.node_id,
                    'user_id':user_id,
                    'conversation_id':chat_request.conversation_id,
                    'request_id':chat_request.request_id
                }
            )
            while True:
                if await request.is_disconnected():
                    break
                try:
                    event, data = await asyncio.to_thread(queue.get, True, 10)
                except Empty:
                    yield ': heartbeat\n\n'
                    continue
                yield sse(event, data)
                if event in ('done', 'error', 'status'):
                    break
        finally:
            cancelled.set()
            await asyncio.to_thread(thread.join)

    return StreamingResponse(
        events(),
        media_type='text/event-stream',
        headers={'Cache-Control':'no-cache', 'X-Accel-Buffering':'no'}
    )


@app.post("/v1/tasks/{task_id}/sections/{section_id}/conversations")
async def create_conversation(task_id: str, section_id: str, request: Request, user_id: str = Depends(chat_user)):
    """创建或恢复指定用户的章节会话，user_id 通过查询参数传入。"""
    return await call_chat_service(request, 'create_conversation', task_id, section_id, user_id)


@app.get("/v1/conversations/{conversation_id}/messages")
async def chat_history(conversation_id: str, request: Request, after: int = 0, limit: int = 50, user_id: str = Depends(chat_user)):
    """分页返回指定会话的历史消息。"""
    return await call_chat_service(request, 'history', conversation_id, user_id, after, limit)


@app.post("/v1/chat/proposals/{proposal_id}/apply")
async def apply_proposal(proposal_id: str, request: Request, user_id: str = Depends(chat_user)):
    """应用 AI 建议，检查会话归属及正文版本；权限由 Java 校验。"""
    return await call_chat_service(request, 'apply', proposal_id, user_id)


if __name__ == '__main__':
    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)