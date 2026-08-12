"""举报模型。

记录用户对帖子/回复的举报，达到阈值后触发折叠。
"""
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.models import Base


class Report(Base):
    """举报表，记录用户对违规内容的举报。"""

    __tablename__ = "reports"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid()
    )
    # 举报人 ID
    reporter_id: Mapped[str] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False
    )
    # 目标类型：post / reply
    target_type: Mapped[str] = mapped_column(String(10), nullable=False)
    # 目标 ID
    target_id: Mapped[str] = mapped_column(UUID(as_uuid=True), nullable=False)
    # 举报理由
    reason: Mapped[str] = mapped_column(String(500), nullable=False)
    # 举报时间
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    # 唯一约束：同一用户对同一目标只能举报一次
    __table_args__ = (
        UniqueConstraint(
            "reporter_id", "target_type", "target_id", name="uq_reports_reporter_target"
        ),
    )
