"""外部立项格式；空 content 数组表示待生成正文。"""
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field
from schemas.EditingResearchRequest import Text

class ResearchNode(BaseModel):
    model_config = ConfigDict(strict=True, extra='forbid')
    title: Text
    level: int = Field(ge=1, le=20)
    content: list[str] = Field(default_factory=list)
    source: list = Field(default_factory=list)
    children: list['ResearchNode'] = Field(default_factory=list)

class ResearchRequest(BaseModel):
    model_config = ConfigDict(strict=True, extra='forbid')
    taskid: Text
    task_name: Text
    direction_model: Literal['multi_level', 'single_node']
    time_range: str = Field(default='', max_length=200)
    description: str = Field(default='', max_length=10000)
    nodes: list[ResearchNode] = Field(min_length=1, max_length=500)
    user_id: Text | None = None
    person: Text | None = None
    group: Text | None = None
