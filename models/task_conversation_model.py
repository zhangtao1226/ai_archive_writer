# -*-coding  : utf-8 -*-
# @Author    : zhangtao
# @File      : task_conversation_model.py
# @Desc      :
# @Time      : 2026/11/6 10:50
# @Software  : PyCharm

from sqlalchemy import Column, Text, Integer, ForeignKeyConstraint, Index, CheckConstraint
from models.task_model import Base
from models.task_section_model import TaskSectionModel


class TaskConversationModel(Base):
    __tablename__ = 'task_conversations'

    conversation_id = Column(Text, primary_key=True)
    task_id = Column(Text, nullable=False)
    section_id = Column(Text, nullable=False)
    user_id = Column(Text, nullable=False, comment='会话所有者，转交章节不修改历史所有者')
    title = Column(Text, nullable=False, default='')
    status = Column(Text, nullable=False, default='active')
    summary = Column(Text, nullable=False, default='', comment='供模型使用的历史摘要，不替代原始消息')
    summary_through_sequence = Column(Integer, nullable=False, default=0, comment='摘要覆盖到的消息序号')
    summary_base_revision = Column(Integer, nullable=True, comment='摘要生成时正文版本')
    created_at = Column(Text, nullable=False)
    updated_at = Column(Text, nullable=False)

    __table_args__ = (
        ForeignKeyConstraint(['task_id', 'section_id'], ['task_sections.task_id', 'task_sections.section_id'], ondelete='RESTRICT'),
        CheckConstraint("status IN ('active', 'archived')", name='ck_conversation_status'),
        CheckConstraint('summary_through_sequence >= 0', name='ck_conversation_summary_sequence'),
        Index('idx_conversation_section_user', 'task_id', 'section_id', 'user_id', 'created_at'),
    )
