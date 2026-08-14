"""帖子模型。

定义帖子表结构，承载主题内容、统计计数与状态字段。
"""
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.models import Base


class Post(Base):
    """帖子表，论坛核心内容载体。"""

    __tablename__ = "posts"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid()
    )
    # 作者 ID：关联 users 表
    author_id: Mapped[str] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True
    )
    # 所属版块 ID：关联 boards 表
    board_id: Mapped[str] = mapped_column(
        UUID(as_uuid=True), ForeignKey("boards.id"), nullable=False, index=True
    )
    # 标题
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    # 正文（Markdown）
    content: Mapped[str] = mapped_column(Text, nullable=False)
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    # 类型：question（提问）/ share（分享）
    type: Mapped[str] = mapped_column(String(10), nullable=False)
    # 标签数组
    tags: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    # 状态：draft（草稿）/ published（已发布）/ archived（已归档）
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="published")
    # AI 回答 ID：Phase 1 预留
    ai_answer_id: Mapped[str | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    # 投票数（赞 - 踩 的净值）
    vote_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    # 浏览数
    view_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    # 回复数：冗余计数
    reply_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    # 已采纳回复 ID：Phase 2 预留
    accepted_reply_id: Mapped[str | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    origin_type: Mapped[str] = mapped_column(String(20), nullable=False, default="user")
    source_url: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    source_title: Mapped[str | None] = mapped_column(String(500), nullable=True)
    source_published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    crawl_item_id: Mapped[str | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    # 是否折叠（达到举报阈值后自动折叠）
    is_folded: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    # 创建时间
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    # 更新时间：编辑时自动刷新
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )
    # 软删除时间
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # 复合索引：加速版块内按时间/热度排序的列表查询
    __table_args__ = (
        Index("ix_posts_board_created", "board_id", "created_at"),
        Index("ix_posts_vote_created", "vote_count", "created_at"),
    )
