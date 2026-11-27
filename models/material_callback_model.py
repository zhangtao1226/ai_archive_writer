"""素材回调持久化状态，与向量分块记录独立。"""
from sqlalchemy import Column, Text, Integer
from models.task_model import Base

class MaterialCallbackModel(Base):
    __tablename__ = 'material_callback'
    category_id = Column(Text, primary_key=True)
    material_id = Column(Text, primary_key=True)
    version = Column(Text, nullable=False)
    success = Column(Integer, nullable=False)
    status = Column(Text, nullable=False, default='pending')
    attempts = Column(Integer, nullable=False, default=0)
    next_attempt = Column(Text, nullable=False, default='')
    error = Column(Text, nullable=False, default='')
