"""AI 答案模型。

定义 AI 答案表结构，承载 LLM 生成内容、检索来源与状态流转。
每个帖子对应一条 AI 答案（一对一），帖子删除时级联删除。
"""
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.models import Base


class AIAnswer(Base):
    """AI 答案表，帖子的 AI 生成回答。"""

    __tablename__ = "ai_answers"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid()
    )
    # 所属帖子 ID：一对一关联 posts 表，帖子删除时级联删除
    post_id: Mapped[str] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("posts.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
    )
    # 答案正文（Markdown）
    content: Mapped[str] = mapped_column(Text, nullable=False, default="")
    # 检索来源列表
    sources: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    # 置信度：high / medium / low
    confidence: Mapped[str] = mapped_column(String(20), nullable=False, default="medium")
    # 检索路径：forum / web / hybrid
    retrieval_path: Mapped[str] = mapped_column(String(20), nullable=False, default="hybrid")
    # 状态：generating / published / verified / corrected / folded
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="generating")
    # 生成答案所用模型名称
    model_name: Mapped[str] = mapped_column(String(100), nullable=False, default="")
    # Token 用量统计
    token_usage: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    corrected_by_reply_id: Mapped[str | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    prompt_version: Mapped[str] = mapped_column(String(50), nullable=False, default="answer-v1")
    # 创建时间
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    # 更新时间：状态流转时自动刷新
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )
