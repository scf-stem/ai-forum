"""回复相关 Pydantic 模型。

定义回复创建、回复项与分页响应的数据结构。
"""
from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.post import AuthorBrief


class ReplyCreate(BaseModel):
    """创建回复请求体。"""

    content: str = Field(min_length=1)
    parent_id: str | None = None
    kind: Literal["supplement", "correction", "discussion"] = "discussion"


class ReplyItem(BaseModel):
    """回复项，含作者信息与二级回复列表。"""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    post_id: UUID
    parent_id: UUID | None = None
    content: str
    kind: str
    vote_count: int
    is_accepted: bool
    is_folded: bool
    created_at: datetime
    updated_at: datetime
    author: AuthorBrief
    # 二级回复列表（仅一级回复填充）
    children: list["ReplyItem"] = Field(default_factory=list)
    # 当前用户对该回复的投票方向
    my_vote: str | None = None


class ReplyListResponse(BaseModel):
    """回复列表分页响应。"""

    items: list[ReplyItem]
    total: int
    page: int
    page_size: int
    has_more: bool


# 解析 ReplyItem.children 的前向引用
ReplyItem.model_rebuild()
