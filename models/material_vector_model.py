# -*-coding  : utf-8 -*-
# @Author    : zhangtao
# @File      : material_vector_model.py
# @Desc      : 
# @Time      : 2026/11/11 14:03
# @Software  : PyCharm

from uuid import uuid4
from datetime import datetime, timezone

from sqlalchemy import Column, Text, Integer, Index, CheckConstraint, UniqueConstraint
from models.task_model import Base


def utc_now():
    return datetime.now(timezone.utc).isoformat()


class MaterialVectorModel(Base):
    __tablename__ = 'material_vector_info'

    id = Column(Text, primary_key=True, nullable=False, default=lambda: str(uuid4()), comment='入库记录ID，数据库ID')
    category_id = Column(Text, nullable=False, comment='上游分类/素材ID')
    source_path = Column(Text, nullable=False, comment='素材文件路径')
    content_hash = Column(Text, nullable=False, comment='文件内容SHA256指纹')
    index_signature = Column(Text, nullable=False, comment='模型版本、分块和解析配置指纹')
    enabled = Column(Integer, nullable=False, default=1, server_default='1', comment='是否开启入库：0关闭，1开启')
    is_deleted = Column(Integer, nullable=False, default=0, server_default='0', comment='是否删除：0未删除，1已删除')
    status = Column(Text, nullable=False, default='pending', server_default='pending', comment='入库状态，completed表示完成')
    collection_name = Column(Text, nullable=False, default='archive_knowledge', server_default='archive_knowledge', comment='Chroma集合')
    vector_info = Column(Text, nullable=False, default='{}', server_default='{}', comment='向量化结果JSON：分块ID、数量、模型、维度等，不存实际向量')
    error_message = Column(Text, nullable=False, default='', server_default='', comment='最近一次错误原因')
    retry_count = Column(Integer, nullable=False, default=0, server_default='0', comment='重试次数')
    created_at = Column(Text, nullable=False, default=utc_now, comment='记录创建时间，UTC ISO8601')
    started_at = Column(Text, nullable=True, comment='本次执行开始时间')
    completed_at = Column(Text, nullable=True, comment='成功完成时间')
    updated_at = Column(Text, nullable=False, default=utc_now, onupdate=utc_now, comment='最近更新时间')

    __table_args__ = (
        CheckConstraint('enabled IN (0, 1)', name='ck_material_vector_enabled'),
        CheckConstraint('is_deleted IN (0, 1)', name='ck_material_vector_deleted'),
        CheckConstraint('retry_count >= 0', name='ck_material_vector_retries'),
        CheckConstraint("status IN ('pending', 'running', 'completed', 'failed', 'interrupted')", name='ck_material_vector_status'),
        # 同一分类可以包含多个文件，路径参与去重，防止相同内容文件互相冲突。
        UniqueConstraint('category_id', 'source_path', 'content_hash', 'index_signature', name='uq_material_vector_version'),
        Index('idx_material_vector_schedule', 'is_deleted', 'enabled', 'status'),
        Index('idx_material_vector_category', 'category_id'),
    )

    def __repr__(self):
        return f'<MaterialVectorModel(id={self.id}, category_id={self.category_id}, status={self.status}, is_deleted={self.is_deleted})>'