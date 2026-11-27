# -*-coding : utf-8 -*-
# @Author   : zhangtao
# @FileName : ResponseUtil.py
# @Desc     : 
# @Time     : 2026/11/9 14:33
# @Software : PyCharm

from typing import Any, Optional, Dict, List, Generic, TypeVar
from schemas.ResponseModel import BaseResponse, ErrorResponse

class ResponseUtil:

    @staticmethod
    def success(data: Any = None, message: str = "Success") -> BaseResponse:
        return BaseResponse(code=200, message=message, data=data)

    @staticmethod
    def error(code: int = 400, message: str = "Error", details: Any = None) -> BaseResponse:
        return BaseResponse(code=code, message=message, data=details)

    @staticmethod
    def created(data: Any = None, message: str = "创建成功") -> BaseResponse:
        return BaseResponse(code=201, message=message, data=data)

    @staticmethod
    def updated(data: Any = None, message: str = "更新成功") -> BaseResponse:
        return BaseResponse(code=200, message=message, data=data)

    @staticmethod
    def deleted(message: str = "删除成功") -> BaseResponse:
        return BaseResponse(code=200, message=message)
