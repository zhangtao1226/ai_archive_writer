# -*-coding : utf-8 -*-
# @Author   : zhangtao
# @FileName : ResponseModel.py
# @Desc     : 
# @Time     : 2026/11/10 09:31
# @Software : PyCharm

from fastapi import status
from pydantic import BaseModel
from typing import Any, Optional, Dict, TypeVar, Generic

T = TypeVar('T')

class BaseResponse(BaseModel, Generic[T]):
    code: int = 200
    message: str = "Success"
    data: Optional[T] = None

class ErrorResponse(BaseModel):
    code: int = 400
    message: str = "Error"
    detail: Optional[Dict[str, Any]] = None