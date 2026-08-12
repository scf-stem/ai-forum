"""投票模型。

记录用户对帖子/回复的投票，唯一约束防止重复投票。
"""
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.models import Base


class Vote(Base):
    """投票表，记录用户对内容的赞/踩。"""

    __tablename__ = "votes"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid()
    )
    # 投票用户 ID
    user_id: Mapped[str] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False
    )
    # 目标类型：post（帖子）/ reply（回复）
    target_type: Mapped[str] = mapped_column(String(10), nullable=False)
    # 目标 ID：根据 target_type 指向 posts 或 replies
    target_id: Mapped[str] = mapped_column(UUID(as_uuid=True), nullable=False)
    # 方向：up（赞）/ down（踩）
    direction: Mapped[str] = mapped_column(String(5), nullable=False)
    # 创建时间
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    # 唯一约束：同一用户对同一目标只能投一票
    __table_args__ = (
        UniqueConstraint(
            "user_id", "target_type", "target_id", name="uq_votes_user_target"
        ),
    )
