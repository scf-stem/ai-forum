"""举报相关 Pydantic 模型。"""
from typing import Literal

from pydantic import BaseModel, Field


class ReportCreate(BaseModel):
    """创建举报请求体。"""

    target_type: Literal["post", "reply"]
    target_id: str
    reason: str = Field(min_length=1, max_length=500)
