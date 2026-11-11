# -*-coding  : utf-8 -*-
# @Author    : zhangtao
# @File      : task_content_model.py
# @Desc      :
# @Time      : 2026/11/6 10:50
# @Software  : PyCharm

from sqlalchemy import Column, Text, Integer, ForeignKey, UniqueConstraint, CheckConstraint
from models.task_model import Base


class TaskContentModel(Base):
    __tablename__ = 'task_content'

    content_id = Column(Text, primary_key=True, comment='正文ID')
    task_id = Column(Text, ForeignKey('task_info.task_id', ondelete='RESTRICT'), nullable=False, comment='立项ID')
    section_id = Column(Text, nullable=False, comment='大纲节点ID')
    title = Column(Text, nullable=False, comment='章节标题快照')
    body = Column(Text, nullable=False, comment='当前正文')
    citations = Column(Text, nullable=False, default='[]', server_default='[]', comment='实际引用资料JSON')
    model_name = Column(Text, nullable=False, default='', comment='生成模型名称')
    revision = Column(Integer, nullable=False, default=1, comment='正文修订号')
    created_at = Column(Text, nullable=False, comment='创建时间')
    updated_at = Column(Text, nullable=False, comment='更新时间')

    __table_args__ = (
        UniqueConstraint('task_id', 'section_id', name='uq_task_content_section'),
        CheckConstraint('revision >= 1', name='ck_task_content_revision'),
    )

    def __repr__(self):
        return (f"<TaskContentModel(content_id={self.content_id}, task_id={self.task_id}, title={self.title}, "
                f"body={self.body}, model_name={self.model_name}, revision={self.revision}, created_at={self.created_at}, "
                f"updated_at={self.updated_at})>")
