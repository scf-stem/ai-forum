"""投票相关 Pydantic 模型。"""
from typing import Literal

from pydantic import BaseModel


class VoteCreate(BaseModel):
    """创建投票请求体。"""

    target_type: Literal["post", "reply"]
    target_id: str
    direction: Literal["up", "down"]


class VoteStatusResponse(BaseModel):
    """批量投票状态响应，key 为目标 ID，value 为方向。"""

    statuses: dict[str, str] = {}
