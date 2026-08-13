"""FastAPI 应用入口。

负责创建应用实例、配置 CORS 中间件、挂载路由与提供健康检查接口。
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings

app = FastAPI(
    title="AI开发者论坛 API",
    description="面向 AI 开发者的技术交流与互助社区后端服务",
    version="0.1.0",
)

# CORS 中间件：允许前端开发环境跨域访问
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 挂载业务路由
from app.routers import auth, users, boards, posts, replies, votes, reports, ai, ws  # noqa: E402

app.include_router(auth.router, prefix="/api/auth", tags=["认证"])
app.include_router(users.router, prefix="/api/users", tags=["用户"])
app.include_router(boards.router, prefix="/api/boards", tags=["版块"])
app.include_router(posts.router, prefix="/api/posts", tags=["帖子"])
# replies 路由含 /posts/{id}/replies 和 /replies/{id}，使用 /api 前缀
app.include_router(replies.router, prefix="/api", tags=["回复"])
app.include_router(votes.router, prefix="/api", tags=["投票"])
app.include_router(reports.router, prefix="/api", tags=["举报"])
# AI 答案 REST 端点（/api/posts/{id}/ai-answer/regenerate）
app.include_router(ai.router, prefix="/api", tags=["AI 答案"])
# WebSocket 流式推送端点（/api/ws/ai-answer/{post_id}）
app.include_router(ws.router, prefix="/api", tags=["WebSocket"])


@app.get("/api/health")
async def health_check() -> dict:
    """健康检查接口，用于容器探针与负载均衡。"""
    return {"status": "ok"}


@app.get("/")
async def root() -> dict:
    """根路径提示，方便快速确认服务是否启动。"""
    return {"name": "AI开发者论坛 API", "docs": "/docs"}
