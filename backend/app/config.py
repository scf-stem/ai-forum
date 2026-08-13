"""应用配置管理模块。

使用 pydantic-settings 从环境变量读取配置，集中管理数据库、Redis、JWT、CORS 等参数。
"""
from functools import lru_cache
from typing import List

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """全局配置项。

    所有配置均可通过环境变量覆盖，默认值适配本地开发环境。
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    # 数据库连接
    DATABASE_URL: str = "postgresql+asyncpg://forum:forum@localhost:5432/forum"

    # Redis 连接
    REDIS_URL: str = "redis://localhost:6379/0"

    # JWT 鉴权配置
    JWT_SECRET: str = "dev-secret-change-in-production"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # 内容举报阈值：达到该阈值后内容进入待审队列
    REPORT_THRESHOLD: int = 5

    # 跨域允许来源
    CORS_ORIGINS: List[str] = ["http://localhost:3000"]

    # DeepSeek API 配置
    DEEPSEEK_API_KEY: str = ""
    DEEPSEEK_BASE_URL: str = "https://api.deepseek.com"
    DEEPSEEK_MODEL: str = "deepseek-v4-flash"

    # Web Search API 配置（可选，不配置则跳过联网检索）
    WEB_SEARCH_API_URL: str = ""
    WEB_SEARCH_API_KEY: str = ""

    # AI 答案生成参数
    AI_ANSWER_MAX_TOKENS: int = 2048
    AI_ANSWER_TEMPERATURE: float = 0.3

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def _parse_cors_origins(cls, value):
        """支持以逗号分隔字符串的形式配置 CORS 来源。"""
        if isinstance(value, str):
            # 去除空格后按逗号拆分，过滤掉空字符串
            return [origin.strip() for origin in value.split(",") if origin.strip()]
        return value


@lru_cache
def get_settings() -> Settings:
    """获取全局配置单例。

    使用 lru_cache 缓存，避免重复读取环境变量造成的性能开销。
    """
    return Settings()


settings = get_settings()
