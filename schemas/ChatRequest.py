from typing import Literal
from pydantic import BaseModel, ConfigDict, Field, model_validator


class ChatRequest(BaseModel):
    model_config = ConfigDict(strict=True, extra='forbid', str_strip_whitespace=True)
    task_id: str = Field(min_length=1)
    section_id: str = Field(min_length=1)
    conversation_id: str = Field(min_length=1)
    request_id: str = Field(min_length=1, max_length=100)
    message: str = Field(min_length=1, max_length=10000)
    base_revision: int = Field(ge=1)
    type: Literal['world', 'excel'] = 'world'
    mode: Literal['ask', 'edit'] = 'ask'
    retrieve: bool = False
    current_content: str | None = None
    use_reference: bool = False
    references: list[dict] = Field(default_factory=list)


class ReferenceRequest(BaseModel):
    """上游素材唯一标识。"""
    model_config = ConfigDict(strict=True, extra='forbid', str_strip_whitespace=True)
    category_id: str = Field(min_length=1)
    material_id: str = Field(min_length=1)


class TextChatRequest(BaseModel):
    """文本对话请求，content 是用户当前编辑稿，不是数据库旧稿。"""
    model_config = ConfigDict(strict=True, extra='forbid', str_strip_whitespace=False)
    user_id: str = Field(min_length=1)
    task_id: str = Field(min_length=1)
    type: Literal['world', 'excel']
    node_id: str | None = None
    content: str = Field(min_length=1)
    questions: str = Field(min_length=1, max_length=10000)
    use_reference: bool = False
    references: list[ReferenceRequest] = Field(default_factory=list, max_length=20)
    request_id: str | None = Field(default=None, min_length=1)

    @model_validator(mode='after')
    def validate_node_id(self):
        """文本对话必须指定章节；Excel 允许省略、null 或空节点。"""
        if self.type == 'world' and (self.node_id is None or not self.node_id.strip()):
            raise ValueError('type=world 时缺少必要参数: node_id')
        if self.node_id is not None:
            self.node_id = self.node_id.strip() or None
        if self.type == 'excel':
            from schemas.excel_content import parse_excel_content
            parse_excel_content(self.content)
        return self
