"""认证相关 Pydantic 模型。

定义注册、登录、Token 响应、刷新请求与用户公开信息的数据结构。
"""
import re
from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

from app.models.user import User


class UserPublic(BaseModel):
    """用户公开信息（不含密码哈希），用于 Token 响应与 /me 接口。"""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    username: str
    email: str
    avatar: str | None = None
    role: str
    tech_stack: list[str] = Field(default_factory=list)
    bio: str | None = None
    created_at: datetime
    last_active_at: datetime

    @classmethod
    def from_orm_user(cls, user: User) -> "UserPublic":
        """从 User ORM 实例构造 UserPublic。"""
        return cls(
            id=user.id,
            username=user.username,
            email=user.email,
            avatar=user.avatar,
            role=user.role,
            tech_stack=user.tech_stack or [],
            bio=user.bio,
            created_at=user.created_at,
            last_active_at=user.last_active_at,
        )


class UserRegister(BaseModel):
    """注册请求体。"""

    email: EmailStr
    username: str = Field(min_length=2, max_length=50)
    password: str = Field(min_length=8, max_length=128)
    role: Literal["developer", "beginner"] = "beginner"
    tech_stack: list[str] = Field(default_factory=list)

    @field_validator("password")
    @classmethod
    def validate_password_strength(cls, v: str) -> str:
        """密码强度校验：至少 8 位且同时包含字母与数字。"""
        if not re.search(r"[a-zA-Z]", v) or not re.search(r"\d", v):
            raise ValueError("密码必须同时包含字母与数字")
        return v


class UserLogin(BaseModel):
    """登录请求体。"""

    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    """登录/注册成功后返回的 Token 响应。"""

    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    user: UserPublic


class RefreshRequest(BaseModel):
    """刷新 Access Token 的请求体。"""

    refresh_token: str
