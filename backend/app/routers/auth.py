"""认证路由。

提供注册、登录、登出、刷新 Token 接口。
"""
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.middleware.auth import get_current_user
from app.models.user import User
from app.schemas.auth import (
    RefreshRequest,
    TokenResponse,
    UserLogin,
    UserPublic,
    UserRegister,
)
from app.services.auth_service import (
    create_access_token,
    create_refresh_token,
    decode_token,
    delete_refresh_token,
    hash_password,
    revoke_access_token,
    store_refresh_token,
    validate_refresh_token,
    verify_password,
)

router = APIRouter()

# 用于 logout 接口再次提取 Access Token（auto_error=False 避免与 get_current_user 重复报错）
_token_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login", auto_error=False)


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def register(payload: UserRegister, db: AsyncSession = Depends(get_db)) -> TokenResponse:
    """注册新用户并签发 Token。"""
    # 校验邮箱唯一性
    email_exists = await db.execute(
        select(User).where(User.email == payload.email, User.deleted_at.is_(None))
    )
    if email_exists.scalar_one_or_none() is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="该邮箱已被注册")

    # 校验用户名唯一性
    username_exists = await db.execute(
        select(User).where(User.username == payload.username, User.deleted_at.is_(None))
    )
    if username_exists.scalar_one_or_none() is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="该用户名已被占用")

    # 创建用户
    user = User(
        email=payload.email,
        username=payload.username,
        password_hash=hash_password(payload.password),
        role=payload.role,
        tech_stack=payload.tech_stack,
    )
    db.add(user)
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="用户名或邮箱已存在")
    await db.refresh(user)

    # 签发 Token 并存储 Refresh Token
    access_token = create_access_token(str(user.id))
    refresh_token = create_refresh_token(str(user.id))
    refresh_jti = decode_token(refresh_token)["jti"]
    await store_refresh_token(str(user.id), refresh_jti)

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        user=UserPublic.from_orm_user(user),
    )


@router.post("/login", response_model=TokenResponse)
async def login(payload: UserLogin, db: AsyncSession = Depends(get_db)) -> TokenResponse:
    """登录并签发 Token。"""
    # 统一错误信息，不区分邮箱或密码错误
    invalid_credentials = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="邮箱或密码错误",
    )

    result = await db.execute(
        select(User).where(User.email == payload.email, User.deleted_at.is_(None))
    )
    user = result.scalar_one_or_none()
    if user is None or not verify_password(payload.password, user.password_hash):
        raise invalid_credentials

    # 更新最近活跃时间
    user.last_active_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(user)

    # 签发 Token
    access_token = create_access_token(str(user.id))
    refresh_token = create_refresh_token(str(user.id))
    refresh_jti = decode_token(refresh_token)["jti"]
    await store_refresh_token(str(user.id), refresh_jti)

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        user=UserPublic.from_orm_user(user),
    )


@router.post("/logout", status_code=status.HTTP_200_OK)
async def logout(
    body: RefreshRequest,
    user: User = Depends(get_current_user),
    token: str = Depends(_token_scheme),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """登出：将 Access Token 加入黑名单并删除 Refresh Token。"""
    # 将 Access Token 加入黑名单
    access_payload = decode_token(token)
    await revoke_access_token(access_payload["jti"], access_payload["exp"])

    # 删除 Refresh Token（若提供且有效）
    try:
        refresh_payload = decode_token(body.refresh_token)
    except Exception:
        refresh_payload = None
    if refresh_payload and refresh_payload.get("type") == "refresh":
        await delete_refresh_token(refresh_payload["sub"], refresh_payload["jti"])

    return {"detail": "已退出登录"}


@router.post("/refresh", response_model=TokenResponse)
async def refresh(body: RefreshRequest, db: AsyncSession = Depends(get_db)) -> TokenResponse:
    """校验 Refresh Token 并签发新的 Access Token。"""
    invalid_token = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="无效的刷新凭证",
    )

    try:
        payload = decode_token(body.refresh_token)
    except Exception:
        raise invalid_token

    if payload.get("type") != "refresh":
        raise invalid_token

    user_id = payload.get("sub")
    jti = payload.get("jti")
    if not user_id or not jti:
        raise invalid_token

    # 校验 Refresh Token 是否仍在 Redis 中（未被登出）
    if not await validate_refresh_token(user_id, jti):
        raise invalid_token

    # 查询用户确保仍存在
    result = await db.execute(
        select(User).where(User.id == user_id, User.deleted_at.is_(None))
    )
    user = result.scalar_one_or_none()
    if user is None:
        raise invalid_token

    # 签发新 Access Token，Refresh Token 保持不变
    access_token = create_access_token(str(user.id))

    return TokenResponse(
        access_token=access_token,
        refresh_token=body.refresh_token,
        user=UserPublic.from_orm_user(user),
    )
