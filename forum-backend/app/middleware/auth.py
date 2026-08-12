"""认证依赖中间件。

提供 FastAPI 依赖注入用的当前用户获取函数，支持强制认证与可选认证两种模式。
"""
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.user import User
from app.services.auth_service import decode_token, is_token_blacklisted

# OAuth2 Bearer Token 提取器，tokenUrl 指向登录接口用于 OpenAPI 文档
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login", auto_error=False)


async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db),
) -> User:
    """强制认证依赖：解析 Token 并返回当前用户。

    无 Token、Token 无效、已加入黑名单或用户不存在均抛出 401。
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="无效的认证凭证",
        headers={"WWW-Authenticate": "Bearer"},
    )

    if not token:
        raise credentials_exception

    # 解析 Token，失败则拒绝
    try:
        payload = decode_token(token)
    except Exception:
        raise credentials_exception

    user_id = payload.get("sub")
    jti = payload.get("jti")
    token_type = payload.get("type")
    if not user_id or not jti or token_type != "access":
        raise credentials_exception

    # 校验黑名单（登出后的 Access Token 立即失效）
    if await is_token_blacklisted(jti):
        raise credentials_exception

    # 查询用户，过滤软删除
    result = await db.execute(
        select(User).where(User.id == user_id, User.deleted_at.is_(None))
    )
    user = result.scalar_one_or_none()
    if user is None:
        raise credentials_exception

    return user


async def get_current_user_optional(
    token: str | None = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db),
) -> User | None:
    """可选认证依赖：无 Token 或校验失败时返回 None，不抛异常。

    适用于游客可访问但登录后享有附加信息的接口（如帖子详情的 my_vote）。
    """
    if not token:
        return None

    try:
        payload = decode_token(token)
    except Exception:
        return None

    user_id = payload.get("sub")
    jti = payload.get("jti")
    token_type = payload.get("type")
    if not user_id or not jti or token_type != "access":
        return None

    # 校验黑名单
    if await is_token_blacklisted(jti):
        return None

    result = await db.execute(
        select(User).where(User.id == user_id, User.deleted_at.is_(None))
    )
    return result.scalar_one_or_none()
