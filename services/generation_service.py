# -*-coding  : utf-8 -*-
# @Author    : zhangtao
# @File      : generation_service.py
# @Desc      : 持久化队列消费者：单进程内串行推理，多进程通过 SQLite 原子领取
# @Time      : 2026/11/6 10:50
# @Software  : PyCharm

import json
from threading import Event, Thread
from datetime import datetime, timezone
from uuid import uuid4
import httpx
from sqlalchemy import select
from core.db import get_database_pool, orm_session
from core.LoggerDetector import logger
from models.task_model import TaskModel
from models.task_content_model import TaskContentModel
from services.research_mode import resolve_research_mode
from services.table_generation import generate_table
from services.relevance_service import filter_relevant_hits
from services.generation_output import parse_output, parse_table_output
from prompts.prompt_template import build_messages, build_sources, PROMPT_VERSION, build_table_messages


class GenerationWorker:
    def __init__(self, config):
        self.config = config
        self.pool = get_database_pool(config.application_db_path)
        self.stop_event = Event()
        self.thread = Thread(target=self.run, name='research-generation')
        self.kb = None

    def start(self):
        self.thread.start()

    def stop(self):
        self.stop_event.set()
        self.thread.join()

    def claim(self):
        with orm_session(self.pool, immediate=True) as session:
            task = session.scalar(select(TaskModel).where(TaskModel.status == 'queued').order_by(TaskModel.created_at).limit(1))
            if task is None:
                return None
            task.status = 'running'
            task.updated_at = datetime.now(timezone.utc).isoformat()
            return {c.name: getattr(task, c.name) for c in TaskModel.__table__.columns}

    def run(self):
        while not self.stop_event.is_set():
            try:
                task = self.claim()
                if task:
                    self.process(task)
                    continue
            except Exception:
                logger.exception('后台编研任务调度失败')
            self.stop_event.wait(2)

    def process(self, task):
        try:
            outline = json.loads(task['outline_snapshot'])
            mode, columns = resolve_research_mode(outline, task['research_type'])
            is_table = mode == 'single_node'
            outline['columns'] = columns
            logger.info(f"编研生成路由 task_id={task['task_id']} direction_model={mode} columns={columns}")
            nodes = [n for n in outline.get('nodes', []) if n.get('generate_body') or n.get('content', '').strip()]
            if not nodes:
                nodes = [{'id': 'document', 'title': task['title'], 'writing_requirements': task['directory_template']}]

            with httpx.Client(timeout=self.config.vllm_timeout_seconds) as client:
                for node in nodes:
                    with orm_session(self.pool) as session:
                        existing = session.scalar(select(TaskContentModel).where(TaskContentModel.task_id == task['task_id'], TaskContentModel.section_id == node['id']))
                    if existing:
                        continue
                    if node.get('content', '').strip():
                        self.save_node(task, node, node['content'], [], '')
                        continue
                    if self.kb is None:
                        from rag.indexing import KnowledgeBase
                        self.kb = KnowledgeBase()
                    hits = self.kb.query(task['retrieval_query'] + '\n章节：' + node.get('path', node['title']),
                                         top_k=5, initial_k=max(5, self.config.rag_initial_k), rerank=True)
                    if not hits and not is_table:
                        raise ValueError('未检索到相关资料，停止生成以避免无依据正文')
                    selected = []
                    used = 0
                    for hit in hits:
                        part = json.dumps(build_sources(selected + [hit])[-1], ensure_ascii=False)
                        if used + len(part) > self.config.llm_context_max_chars:
                            continue
                        selected.append(hit)
                        used += len(part) + 2
                    if not selected and not is_table:
                        raise ValueError('资料预算不足以容纳一个完整片段')
                    messages = build_messages(
                        scene='generate',
                        project={'title': task['title'], 'description': task['description'],
                                 'research_type': task['research_type'], 'time_range': task['time_range']},
                        section={'node_id': node['id'], 'node_title': node['title'],
                                 'title_path': node.get('path', node['title']),
                                 'writing_requirements': node.get('writing_requirements', '')},
                        hits=selected,
                    )
                    if is_table:
                        messages = build_table_messages(
                            {
                                'title': task['title'],
                                'description': task['description'],
                                'time_range': task['time_range']
                            },
                            outline['columns'],
                            selected
                        )
                    logger.info(f"生成节点 task_id={task['task_id']} node_id={node['id']} prompt_version={PROMPT_VERSION}")
                    def request_choice(request_messages):
                        response = client.post(self.config.vllm_base_url.rstrip('/') + '/chat/completions',
                            headers={'Authorization': 'Bearer ' + self.config.vllm_api_key},
                            json={
                                'model': self.config.vllm_model_name,
                                'messages': request_messages,
                                'max_tokens': self.config.vllm_max_tokens,
                                'chat_template_kwargs': {'enable_thinking': False},
                                'response_format': {'type': 'json_object'}
                            }
                        )
                        response.raise_for_status()
                        return response.json()['choices'][0]
                    if is_table:
                        project = {
                            'title':task['title'],
                            'description':task['description'],
                            'time_range':task['time_range']
                        }
                        candidate_count = len(selected)
                        selected = filter_relevant_hits(request_choice, project, selected)
                        messages = build_table_messages(project, columns, selected)
                        logger.info(f"大事记资料筛选 task_id={task['task_id']} candidates={candidate_count} relevant={len(selected)}")
                        body, citations = generate_table(request_choice, messages, selected, columns, task['task_id'])
                    else:
                        choice = request_choice(messages)
                        if choice.get('finish_reason') != 'stop':
                            raise ValueError(f"生成未正常完成：{choice.get('finish_reason')}")
                        body, citations = parse_output(choice['message']['content'], selected)
                    self.save_node(task, node, body, citations, self.config.vllm_model_name)
            with orm_session(self.pool, immediate=True) as session:
                current = session.get(TaskModel, task['task_id'])
                if current is None or current.status != 'running':
                    return
                now = datetime.now(timezone.utc).isoformat()
                current.status = 'completed'
                current.updated_at = now
        except Exception:
            logger.exception(f"编研生成失败 task_id={task['task_id']}")
            with orm_session(self.pool, immediate=True) as session:
                current = session.get(TaskModel, task['task_id'])
                if current and current.status == 'running':
                    current.status = 'failed'
                    current.updated_at = datetime.now(timezone.utc).isoformat()

    def save_node(self, task, node, body, citations, model_name):
        with orm_session(self.pool, immediate=True) as session:
            current = session.get(TaskModel, task['task_id'])
            if current is None or current.status != 'running':
                raise ValueError('任务已停止，不能继续保存')
            existing = session.scalar(select(TaskContentModel).where(
                TaskContentModel.task_id == current.task_id, TaskContentModel.section_id == node['id']))
            if existing:
                return
            now = datetime.now(timezone.utc).isoformat()
            session.add(TaskContentModel(content_id=str(uuid4()),task_id=current.task_id,
                section_id=node['id'],title=node['title'],body=body,model_name=model_name,
                revision=1,created_at=now,updated_at=now,citations=json.dumps(citations,ensure_ascii=False)))
