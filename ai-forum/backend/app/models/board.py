"""版块模型。

定义版块表结构，区分入门级与深度级，承载版块元信息与计数。
"""
from datetime import datetime

from sqlalchemy import DateTime, Integer, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.models import Base


class Board(Base):
    """版块表，帖子按版块聚合展示。"""

    __tablename__ = "boards"
    __table_args__ = (
        # 名称+层级联合唯一，保证同层级内版块名不重复，供种子脚本幂等写入
        UniqueConstraint("name", "tier", name="uq_boards_name_tier"),
    )

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid()
    )
    # 版块名称
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    # 层级：entry（入门）/ deep（深度），用于首页分组展示
    tier: Mapped[str] = mapped_column(String(10), nullable=False)
    # 版块描述
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    # 排序权重：值小靠前
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    # 帖子数：冗余计数，避免每次聚合查询
    post_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    # 关注数：预留字段
    follower_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    # 创建时间
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
