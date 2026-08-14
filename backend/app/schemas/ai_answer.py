"""AI 答案相关 Pydantic 模型。

定义 AI 答案的来源标注、详情与简要信息数据结构。
详情态用于已发布的 AI 答案展示，简要态用于生成中通过 WebSocket 推送状态。
"""
from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class AnswerSource(BaseModel):
    """检索来源标注，记录 AI 答案引用的具体出处。"""

    type: Literal["forum", "docs", "blog", "issue"]
    title: str
    snippet: str
    url: str
    # forum 类型时关联的帖子 ID，其他类型为 None
    post_id: str | None = None


class AIAnswerDetail(BaseModel):
    """AI 答案详情，用于 published 态完整展示。"""

    model_config = ConfigDict(from_attributes=True, protected_namespaces=())

    id: UUID
    content: str
    sources: list[AnswerSource]
    confidence: Literal["high", "medium", "low"]
    retrieval_path: Literal["forum", "web", "hybrid"]
    status: Literal["generating", "published", "verified", "corrected", "folded"]
    model_name: str
    token_usage: dict
    corrected_by_reply_id: UUID | None = None
    prompt_version: str = "answer-v1"
    my_feedback: str | None = None
    helpful_count: int = 0
    not_helpful_count: int = 0
    created_at: datetime
    updated_at: datetime


class AIAnswerBrief(BaseModel):
    """AI 答案简要信息，用于 generating 态。

    前端通过 WebSocket 接收流式内容，仅返回 id、状态与当前已生成内容。
    """

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    status: Literal["generating", "published", "verified", "corrected", "folded"]
    content: str = ""
