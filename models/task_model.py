# -*-coding  : utf-8 -*-
# @Author    : zhangtao
# @File      : task_model.py
# @Desc      :
# @Time      : 2026/11/6 10:50
# @Software  : PyCharm
from sqlalchemy import Column, Text, Index
from sqlalchemy.orm import declarative_base

Base = declarative_base()


class TaskModel(Base):
    __tablename__ = 'task_info'

    task_id = Column(Text, primary_key=True, nullable=False, comment="任务ID")
    user_id = Column(Text, nullable=False, comment="发起用户ID")
    title = Column(Text, nullable=False, comment="选题名称")
    research_type = Column(Text, nullable=False, comment="编研类型")
    responsible_user_id = Column(Text, nullable=False, comment="责任人ID")
    group = Column(Text, nullable=False, comment="编研小组")
    directory_template = Column(Text, nullable=False, comment="目录模板")
    time_range = Column(Text, nullable=False, comment="时间范围")
    description = Column(Text, nullable=False, comment="选题说明")
    status = Column(Text, nullable=False, comment="任务状态")
    retrieval_query = Column(Text, nullable=False, comment="检索问题")
    group_snapshot = Column(Text, nullable=False, comment="小组快照JSON")
    outline_snapshot = Column(Text, nullable=False, comment="大纲快照JSON")
    created_at = Column(Text, nullable=False, comment="创建时间")
    updated_at = Column(Text, nullable=False, comment="更新时间")

    __table_args__ = (
        Index('idx_task_info_user_created', 'user_id', 'created_at'),
        Index('idx_task_info_status', 'status'),
    )


    def __repr__(self):
        return (f"<TaskModel(task_id={self.task_id}, user_id={self.user_id}, title={self.title}, "
                f"research_type={self.research_type}, responsible_user_id={self.responsible_user_id}, "
                f"group={self.group}, directory_template={self.directory_template}, time_range={self.time_range}, "
                f"description={self.description}, status={self.status}, retrieval_query={self.retrieval_query}, group_snapshot={self.group_snapshot}, "
                f"outline_snapshot={self.outline_snapshot}), created_at={self.created_at}, updated_at={self.updated_at})>")