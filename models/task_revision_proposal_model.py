# -*-coding  : utf-8 -*-
# @Author    : zhangtao
# @File      : task_revision_proposal_model.py
# @Desc      :
# @Time      : 2026/11/6 10:50
# @Software  : PyCharm
"""AI 修改建议，仅在用户应用后更新正文。章节由关联会话确定。"""

from sqlalchemy import Column, Text, Integer, ForeignKey, CheckConstraint, Index
from models.task_model import Base
from models.task_message_model import TaskMessageModel


class TaskRevisionProposalModel(Base):
    __tablename__ = 'task_revision_proposals'

    proposal_id = Column(Text, primary_key=True)
    message_id = Column(Text, ForeignKey('task_messages.message_id', ondelete='RESTRICT'), nullable=False, unique=True, comment='产生建议的助手消息')
    base_revision = Column(Integer, nullable=False)
    proposed_body = Column(Text, nullable=False, comment='建议的完整章节正文，首版避免不可靠文本补丁')
    citations = Column(Text, nullable=False, default='[]', comment='建议正文对应引用快照JSON')
    change_summary = Column(Text, nullable=False, default='')
    status = Column(Text, nullable=False, default='pending')
    applied_revision = Column(Integer, nullable=True)
    applied_by = Column(Text, nullable=True)
    applied_at = Column(Text, nullable=True)
    created_at = Column(Text, nullable=False)
    updated_at = Column(Text, nullable=False)

    __table_args__ = (
        CheckConstraint('base_revision >= 1', name='ck_proposal_revision'),
        CheckConstraint("status IN ('pending', 'applied', 'rejected', 'conflict')", name='ck_proposal_status'),
        Index('idx_proposal_status', 'status', 'created_at'),
    )
