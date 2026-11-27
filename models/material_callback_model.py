# -*-coding : utf-8 -*-
# @Author   : zhangtao
# @FileName : material_callback_model.py
# @Desc     : 
# @Time     : 2026/11/27 10:37
# @Software : PyCharm

from sqlalchemy import Column, Text, Integer
from models.task_model import Base

class MaterialCallbackModel(Base):
    __tablename__ = "material_callback"

    category_id = Column(Text, primary_key=True)
    material_id = Column(Text, primary_key=True)
    version = Column(Text, nullable=False)
    success = Column(Text, nullable=False)
    status = Column(Text, nullable=False, default='pending')
    attempts = Column(Integer, nullable=False, default=0)
    next_attempt = Column(Integer, nullable=False, default=0)
    error = Column(Text, nullable=False, default='')