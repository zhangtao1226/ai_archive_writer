# -*-coding  : utf-8 -*-
# @Author    : zhangtao
# @File      : ChatRequest.py
# @Desc      :
# @Time      : 2026/11/6 10:50
# @Software  : PyCharm

from typing import Literal

from aiohttp import payload
from pydantic import BaseModel, ConfigDict, Field, model_validator


class ChatRequest(BaseModel):
    model_config = ConfigDict(strict=True, extra='forbid', str_strip_whitespace=True)
    task_id: str = Field(min_length=1)
    section_id: str = Field(min_length=1)
    conversation_id: str = Field(min_length=1)
    request_id: str = Field(min_length=1, max_length=100)
    message: str = Field(min_length=1, max_length=10000)
    base_revision: int = Field(ge=1)
    mode: Literal['ask', 'edit'] = 'ask'
    type: Literal['word', 'excel'] = 'word'
    retrieve: bool = False
    current_content: str | None = None
    use_reference: bool = False
    references: list[dict] = Field(default_factory=list)

class ReferenceRequest(BaseModel):
    model_config = ConfigDict(strict=True, extra='forbid', str_strip_whitespace=True)
    category_id: str = Field(min_length=1)
    material_id: str = Field(min_length=1)

class TextChatRequest(BaseModel):
    model_config = ConfigDict(strict=True, extra='forbid', str_strip_whitespace=True)
    user_id: str = Field(min_length=1)
    task_id: str = Field(min_length=1)
    type: Literal['word', 'excel']
    node_id: str | None = None
    content: str = Field(min_length=1)
    questions: str = Field(min_length=1, max_length=10000)
    use_reference: bool = False
    references: list[ReferenceRequest] = Field(default_factory=list, max_length=20)
    request_id: str | None = Field(default=None, min_length=1)

    @model_validator(mode='after')
    def validate_node_id(self):
        if self.type == 'word' and (self.node_id is None or not self.node_id.strip()):
            raise ValueError("type=word 时缺少必要参数： node_id")

        if self.node_id is None:
            self.node_id = self.node_id.strip() or None
        return self


