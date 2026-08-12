"""版块相关 Pydantic 模型。"""
from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class BoardItem(BaseModel):
    """版块列表项。"""

    model_config = ConfigDict(from_attributes=True)

    # 使用 UUID 类型以便直接从 ORM 对象转换；序列化时自动输出为标准格式字符串
    id: UUID
    name: str
    tier: str
    description: str | None = None
    sort_order: int
    post_count: int
    follower_count: int
    created_at: datetime


class BoardListResponse(BaseModel):
    """版块列表响应，按层级分组。"""

    entry: list[BoardItem]
    deep: list[BoardItem]
