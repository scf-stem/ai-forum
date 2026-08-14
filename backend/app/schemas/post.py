"""帖子相关 Pydantic 模型。

定义帖子创建、更新、列表项、详情与分页响应的数据结构。
"""
from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.ai_answer import AIAnswerDetail


class AuthorBrief(BaseModel):
    """作者简要信息，用于帖子/回复列表中的嵌套展示。"""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    username: str
    avatar: str | None = None
    role: str


class BoardBrief(BaseModel):
    """版块简要信息，用于帖子列表中的嵌套展示。"""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    tier: str


class PostCreate(BaseModel):
    """创建帖子请求体。"""

    title: str = Field(min_length=5, max_length=200)
    content: str = Field(min_length=10)
    summary: str | None = Field(default=None, max_length=2000)
    board_id: str
    type: Literal["question", "share"]
    tags: list[str] = Field(default_factory=list)


class PostUpdate(BaseModel):
    """更新帖子请求体，所有字段可选。"""

    title: str | None = Field(default=None, min_length=5, max_length=200)
    content: str | None = Field(default=None, min_length=10)
    summary: str | None = Field(default=None, max_length=2000)
    tags: list[str] | None = None


class PostListItem(BaseModel):
    """帖子列表项。"""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    title: str
    type: str
    tags: list[str] = Field(default_factory=list)
    vote_count: int
    view_count: int
    reply_count: int
    is_folded: bool
    summary: str | None = None
    accepted_reply_id: UUID | None = None
    origin_type: str = "user"
    source_url: str | None = None
    source_title: str | None = None
    created_at: datetime
    updated_at: datetime
    author: AuthorBrief
    board: BoardBrief


class PostDetail(BaseModel):
    """帖子详情，含完整内容与当前用户投票方向。"""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    author_id: UUID
    board_id: UUID
    title: str
    content: str
    type: str
    tags: list[str] = Field(default_factory=list)
    status: str
    vote_count: int
    view_count: int
    reply_count: int
    is_folded: bool
    summary: str | None = None
    accepted_reply_id: UUID | None = None
    origin_type: str = "user"
    source_url: str | None = None
    source_title: str | None = None
    created_at: datetime
    updated_at: datetime
    author: AuthorBrief
    board: BoardBrief
    # 当前用户对该帖子的投票方向，未登录或未投票时为 None
    my_vote: str | None = None
    # AI 答案详情，未生成或未发布时为 None
    ai_answer: AIAnswerDetail | None = None


class PostListResponse(BaseModel):
    """帖子列表分页响应。"""

    items: list[PostListItem]
    total: int
    page: int
    page_size: int
    has_more: bool
