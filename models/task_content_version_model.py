# -*-coding  : utf-8 -*-
# @Author    : zhangtao
# @File      : task_content_version_model.py
# @Desc      :
# @Time      : 2026/11/6 10:50
# @Software  : PyCharm

from sqlalchemy import Column, Text, Integer, ForeignKey, UniqueConstraint, CheckConstraint
from models.task_model import Base
from models.task_content_model import TaskContentModel
from models.task_revision_proposal_model import TaskRevisionProposalModel


class TaskContentVersionModel(Base):
    __tablename__ = 'task_content_versions'

    version_id = Column(Text, primary_key=True)
    content_id = Column(Text, ForeignKey('task_content.content_id', ondelete='RESTRICT'), nullable=False)
    revision = Column(Integer, nullable=False)
    title = Column(Text, nullable=False)
    body = Column(Text, nullable=False)
    citations = Column(Text, nullable=False, default='[]')
    change_type = Column(Text, nullable=False, comment='生成、人工修改、AI修改或恢复')
    changed_by = Column(Text, nullable=True, comment='系统生成可为空')
    model_name = Column(Text, nullable=True)
    proposal_id = Column(Text, ForeignKey('task_revision_proposals.proposal_id', ondelete='RESTRICT'), nullable=True)
    created_at = Column(Text, nullable=False)

    __table_args__ = (
        UniqueConstraint('content_id', 'revision', name='uq_content_version_revision'),
        CheckConstraint('revision >= 1', name='ck_content_version_revision'),
        CheckConstraint("change_type IN ('generated', 'manual', 'ai_edit', 'restore')", name='ck_content_version_type'),
    )
