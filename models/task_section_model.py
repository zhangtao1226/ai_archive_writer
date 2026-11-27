# -*-coding  : utf-8 -*-
# @Author    : zhangtao
# @File      : task_section_model.py
# @Desc      :
# @Time      : 2026/11/6 10:50
# @Software  : PyCharm
"""任务章节树。每个节点至多一位编辑负责人，未分配时为空。"""
from sqlalchemy import Column, Text, Integer, Boolean, ForeignKey, ForeignKeyConstraint, Index, CheckConstraint
from models.task_model import Base


class TaskSectionModel(Base):
    __tablename__ = 'task_sections'

    task_id = Column(Text, ForeignKey('task_info.task_id', ondelete='RESTRICT'), primary_key=True)
    section_id = Column(Text, primary_key=True, comment='大纲稳定节点ID，任务内唯一')
    parent_id = Column(Text, nullable=True, comment='同任务父节点ID，根节点为空')
    title = Column(Text, nullable=False, comment='章节标题')
    sort_order = Column(Integer, nullable=False, default=0, comment='同级显示顺序')
    editable = Column(Boolean, nullable=False, default=False, comment='是否为正文编辑节点')
    assigned_user_id = Column(Text, nullable=True, comment='唯一编辑负责人ID')
    writing_requirements = Column(Text, nullable=False, default='')
    created_at = Column(Text, nullable=False, comment='UTC ISO8601')
    updated_at = Column(Text, nullable=False, comment='UTC ISO8601')

    __table_args__ = (
        ForeignKeyConstraint(['task_id', 'parent_id'], ['task_sections.task_id', 'task_sections.section_id'], ondelete='RESTRICT'),
        CheckConstraint('sort_order >= 0', name='ck_section_order'),
        CheckConstraint('parent_id IS NULL OR parent_id != section_id', name='ck_section_not_self'),
        Index('idx_section_assignee', 'assigned_user_id', 'task_id'),
    )
