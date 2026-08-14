"""回复模型。

定义回复表结构，支持二级回复（回复一级回复）与软删除。
"""
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.models import Base


class Reply(Base):
    """回复表，帖子下的讨论内容。"""

    __tablename__ = "replies"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid()
    )
    # 所属帖子 ID：关联 posts 表
    post_id: Mapped[str] = mapped_column(
        UUID(as_uuid=True), ForeignKey("posts.id"), nullable=False, index=True
    )
    # 父回复 ID：为空表示一级回复，非空表示二级回复
    parent_id: Mapped[str | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("replies.id"), nullable=True
    )
    target_ai_answer_id: Mapped[str | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("ai_answers.id", ondelete="SET NULL"), nullable=True
    )
    # 作者 ID：关联 users 表
    author_id: Mapped[str] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False
    )
    # 回复正文
    content: Mapped[str] = mapped_column(Text, nullable=False)
    # 类型：supplement（补充）/ correction（纠正）/ discussion（讨论）
    kind: Mapped[str] = mapped_column(String(20), nullable=False, default="discussion")
    # 投票数
    vote_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    # 是否被采纳
    is_accepted: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    # 是否折叠（达到举报阈值后自动折叠）
    is_folded: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    # 创建时间
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    # 更新时间
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )
    # 软删除时间
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
