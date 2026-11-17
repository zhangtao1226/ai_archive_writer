# -*-coding  : utf-8 -*-
# @Author    : zhangtao
# @File      : task_message_model.py
# @Desc      :
# @Time      : 2026/11/6 10:50
# @Software  : PyCharm
"""持久化会话消息及推理状态；客户端请求ID支持重试去重。"""

from sqlalchemy import Column, Text, Integer, ForeignKey, UniqueConstraint, CheckConstraint
from models.task_model import Base
from models.task_conversation_model import TaskConversationModel


class TaskMessageModel(Base):
    __tablename__ = 'task_messages'

    message_id = Column(Text, primary_key=True)
    conversation_id = Column(Text, ForeignKey('task_conversations.conversation_id', ondelete='RESTRICT'), nullable=False)
    sequence = Column(Integer, nullable=False, comment='会话内递增序号，用于游标分页')
    request_id = Column(Text, nullable=False, comment='同一轮请求的幂等ID，用户和助手消息共用')
    role = Column(Text, nullable=False)
    sender_user_id = Column(Text, nullable=True, comment='用户消息必填；助手消息为空，由服务层校验')
    content = Column(Text, nullable=False, default='')
    citations = Column(Text, nullable=False, default='[]', comment='本条回复引用资料JSON')
    base_revision = Column(Integer, nullable=True, comment='发起请求时正文修订号')
    status = Column(Text, nullable=False, default='pending')
    model_name = Column(Text, nullable=True)
    prompt_tokens = Column(Integer, nullable=True)
    completion_tokens = Column(Integer, nullable=True)
    finish_reason = Column(Text, nullable=True)
    error_message = Column(Text, nullable=True, comment='脱敏错误信息')
    created_at = Column(Text, nullable=False)
    updated_at = Column(Text, nullable=False)

    __table_args__ = (
        UniqueConstraint('conversation_id', 'sequence', name='uq_message_sequence'),
        UniqueConstraint('conversation_id', 'request_id', 'role', name='uq_message_request_role'),
        CheckConstraint('sequence > 0', name='ck_message_sequence'),
        CheckConstraint("role IN ('user', 'assistant')", name='ck_message_role'),
        CheckConstraint("status IN ('pending', 'running', 'completed', 'failed', 'cancelled')", name='ck_message_status'),
        CheckConstraint('prompt_tokens IS NULL OR prompt_tokens >= 0', name='ck_message_prompt_tokens'),
        CheckConstraint('completion_tokens IS NULL OR completion_tokens >= 0', name='ck_message_completion_tokens'),
    )
