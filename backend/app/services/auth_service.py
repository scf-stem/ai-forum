"""认证服务。

封装密码哈希、JWT 签发/校验与 Redis 会话管理（Refresh Token 存储、Access Token 黑名单）。
"""
from datetime import datetime, timedelta, timezone
from uuid import uuid4

import bcrypt
from jose import jwt

from app.config import settings
from app.redis_client import redis_client

# Refresh Token 在 Redis 中的 key 前缀
REFRESH_KEY_PREFIX = "refresh"
# Access Token 黑名单在 Redis 中的 key 前缀
BLACKLIST_KEY_PREFIX = "blacklist"


def hash_password(password: str) -> str:
    """对明文密码进行 bcrypt 哈希。

    bcrypt 限制密码最大 72 字节，超长时截断以避免 ValueError。
    """
    # bcrypt 限制密码最大 72 字节，截断后编码
    password_bytes = password.encode("utf-8")[:72]
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(password_bytes, salt).decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    """校验明文密码与哈希是否匹配。"""
    plain_bytes = plain.encode("utf-8")[:72]
    hashed_bytes = hashed.encode("utf-8")
    return bcrypt.checkpw(plain_bytes, hashed_bytes)


def _create_token(user_id: str, token_type: str, expires_delta: timedelta) -> str:
    """构造 JWT 的通用方法。

    内部生成 jti（唯一标识），用于黑名单与 Refresh Token 管理。
    """
    now = datetime.now(timezone.utc)
    to_encode = {
        "sub": str(user_id),
        "exp": now + expires_delta,
        "iat": now,
        "jti": str(uuid4()),
        "type": token_type,
    }
    return jwt.encode(to_encode, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)


def create_access_token(user_id: str) -> str:
    """签发 Access Token，有效期由 ACCESS_TOKEN_EXPIRE_MINUTES 控制。"""
    return _create_token(
        user_id,
        "access",
        timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES),
    )


def create_refresh_token(user_id: str) -> str:
    """签发 Refresh Token，有效期由 REFRESH_TOKEN_EXPIRE_DAYS 控制。"""
    return _create_token(
        user_id,
        "refresh",
        timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS),
    )


def decode_token(token: str) -> dict:
    """解析并校验 Token。

    校验失败抛出 JWTError，由调用方处理。
    """
    return jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM])


# ---------- Redis 会话管理 ----------

async def store_refresh_token(user_id: str, jti: str) -> None:
    """将 Refresh Token 的 jti 存入 Redis，TTL 与 Refresh Token 有效期一致。"""
    key = f"{REFRESH_KEY_PREFIX}:{user_id}:{jti}"
    await redis_client.set(key, "1", ex=settings.REFRESH_TOKEN_EXPIRE_DAYS * 24 * 3600)


async def revoke_access_token(jti: str, exp: int) -> None:
    """将 Access Token 加入黑名单，TTL 为其剩余有效期。"""
    now = int(datetime.now(timezone.utc).timestamp())
    ttl = exp - now
    if ttl <= 0:
        # 已过期的 Token 无需加入黑名单
        return
    key = f"{BLACKLIST_KEY_PREFIX}:{jti}"
    await redis_client.set(key, "1", ex=ttl)


async def is_token_blacklisted(jti: str) -> bool:
    """判断 Access Token 是否已被加入黑名单。"""
    key = f"{BLACKLIST_KEY_PREFIX}:{jti}"
    return await redis_client.exists(key) > 0


async def validate_refresh_token(user_id: str, jti: str) -> bool:
    """校验 Refresh Token 是否仍在有效期内（存在于 Redis 中）。"""
    key = f"{REFRESH_KEY_PREFIX}:{user_id}:{jti}"
    return await redis_client.exists(key) > 0


async def delete_refresh_token(user_id: str, jti: str) -> None:
    """删除指定的 Refresh Token（登出时调用）。"""
    key = f"{REFRESH_KEY_PREFIX}:{user_id}:{jti}"
    await redis_client.delete(key)
