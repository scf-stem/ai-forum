"""用户相关 Pydantic 模型。

定义用户资料、资料更新与用户帖子列表项的数据结构。
"""
from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class UserProfile(BaseModel):
    """用户公开资料（不含邮箱），用于用户主页展示。"""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    username: str
    avatar: str | None = None
    role: str
    tech_stack: list[str] = Field(default_factory=list)
    bio: str | None = None
    created_at: datetime
    last_active_at: datetime


class UserUpdate(BaseModel):
    """用户资料更新请求体，所有字段可选。"""

    avatar: str | None = Field(default=None, max_length=500)
    bio: str | None = None
    tech_stack: list[str] | None = None


class UserPostItem(BaseModel):
    """用户帖子列表项（精简版），用于用户主页的帖子列表。"""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    title: str
    type: str
    tags: list[str] = Field(default_factory=list)
    vote_count: int
    reply_count: int
    created_at: datetime
    board_name: str | None = None


class UserReplyItem(BaseModel):
    """用户回复列表项，含所属帖子信息。"""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    content: str
    kind: str
    vote_count: int
    created_at: datetime
    post_id: UUID
    post_title: str | None = None
