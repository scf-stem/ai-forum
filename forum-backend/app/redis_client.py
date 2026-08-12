"""Redis 异步连接模块。

提供全局 Redis 客户端与 FastAPI 依赖注入用的 get_redis。
"""
from collections.abc import AsyncGenerator

import redis.asyncio as redis

from app.config import settings

# 全局 Redis 异步客户端：decode_responses 让返回值直接为字符串
redis_client = redis.from_url(
    settings.REDIS_URL,
    decode_responses=True,
    encoding="utf-8",
)


async def get_redis() -> AsyncGenerator[redis.Redis, None]:
    """FastAPI 依赖：提供 Redis 客户端实例。"""
    yield redis_client
