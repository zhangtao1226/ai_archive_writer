from typing import Literal
from pydantic import BaseModel, ConfigDict, Field


class ChatRequest(BaseModel):
    model_config = ConfigDict(strict=True, extra='forbid', str_strip_whitespace=True)
    task_id: str = Field(min_length=1)
    section_id: str = Field(min_length=1)
    conversation_id: str = Field(min_length=1)
    request_id: str = Field(min_length=1, max_length=100)
    message: str = Field(min_length=1, max_length=10000)
    base_revision: int = Field(ge=1)
    mode: Literal['ask', 'edit'] = 'ask'
    retrieve: bool = False
