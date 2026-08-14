"""用户模型。

定义用户表结构，包含账号、角色、技术栈、个人资料及软删除字段。
"""
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Index, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.models import Base


class User(Base):
    """用户表，承载账号与个人资料信息。"""

    __tablename__ = "users"

    # 主键：UUID，应用层生成
    id: Mapped[str] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid()
    )
    # 邮箱：唯一且建索引，登录与查重使用
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    # 用户名：唯一且建索引，对外展示与个性化主页使用
    username: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)
    # 密码哈希：仅存 bcrypt 哈希，不存明文
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    # 头像 URL，可为空（使用默认头像）
    avatar: Mapped[str | None] = mapped_column(String(500), nullable=True)
    # 角色：developer（开发者）/ beginner（初学者），默认初学者
    role: Mapped[str] = mapped_column(String(20), nullable=False, default="beginner")
    # 技术栈标签数组，如 ["Python", "FastAPI"]
    tech_stack: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    # 个人简介
    bio: Mapped[str | None] = mapped_column(Text, nullable=True)
    reputation: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    level: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    points_balance: Mapped[int] = mapped_column(Integer, nullable=False, default=100)
    is_admin: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    is_system: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    personalization_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    # 创建时间：带时区
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    # 最近活跃时间：登录或发帖时更新
    last_active_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    # 软删除时间：非空表示已删除，查询需过滤
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # 复合索引：加速按邮箱+删除状态的查询
    __table_args__ = (
        Index("ix_users_email_active", "email", "deleted_at"),
    )
