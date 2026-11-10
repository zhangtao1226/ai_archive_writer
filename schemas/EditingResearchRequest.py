# -*-coding  : utf-8 -*-
# @Author    : zhangtao
# @File      : EditingResearchRequest.py
# @Desc      :
# @Time      : 2025/8/15 16:42
# @Software  : PyCharm

from typing import Annotated
from pydantic import BaseModel, ConfigDict, Field, StringConstraints, model_validator

Text = Annotated[str, StringConstraints(strict=True, strip_whitespace=True, min_length=1, max_length=500)]


class OutlineNode(BaseModel):
    model_config = ConfigDict(strict=True, extra='forbid')
    id: Text
    parent_id: Text | None = None
    title: Text
    order: int = Field(ge=0)
    generate_body: bool = False
    writing_requirements: str = ''


class Template(BaseModel):
    model_config = ConfigDict(strict=True, extra='forbid')
    id: Text
    name: Text
    type: Text
    version: Text
    nodes: list[OutlineNode] = Field(min_length=1)

    @model_validator(mode='after')
    def validate_tree(self):
        nodes = {node.id: node for node in self.nodes}
        if len(nodes) != len(self.nodes):
            raise ValueError('大纲节点 ID 重复')
        positions = set()
        for node in self.nodes:
            position = (node.parent_id, node.order)
            if position in positions:
                raise ValueError('同级节点顺序重复')
            positions.add(position)
            seen = {node.id}
            parent = node.parent_id
            while parent is not None:
                if parent not in nodes or parent in seen:
                    raise ValueError('大纲存在无效父节点或循环')
                seen.add(parent)
                parent = nodes[parent].parent_id
        if not any(n.generate_body for n in self.nodes):
            raise ValueError('模板至少需要一个正文节点')
        return self


class Group(BaseModel):
    model_config = ConfigDict(strict=True, extra='forbid')
    id: Text
    name: Text
    type: Text
    member_ids: list[Text]


class Catalog(BaseModel):
    model_config = ConfigDict(strict=True, extra='forbid')
    templates: list[Template]
    groups: list[Group]

    @model_validator(mode='after')
    def unique_ids(self):
        for items in (self.templates, self.groups):
            if len({item.id for item in items}) != len(items):
                raise ValueError('目录 ID 重复')
        return self


class EditingResearchRequest(BaseModel):
    model_config = ConfigDict(strict=True, str_strip_whitespace=True, extra='forbid')
    user_id: Text
    title: Text
    type: Text
    person: Text = Field(description='责任人用户 ID，不参与语义检索')
    group: Text
    directory_template: Text
    time_range: str = Field(default='', max_length=200)
    description: str = Field(default='', max_length=10000)

    # 可选请求快照：原样保存，不查询服务端目录或校验业务关系。
    group_snapshot: dict = Field(default_factory=dict)
    outline_snapshot: dict = Field(default_factory=dict)
