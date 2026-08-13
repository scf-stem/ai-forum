"""AI 答案生成编排服务。

编排完整的 AI 答案生成流程：双路检索 → DeepSeek 流式生成 → WebSocket 逐 token 推送 → 持久化。
作为后台任务运行，不阻塞帖子发布接口。
"""
import asyncio
import logging

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import AsyncSessionLocal
from app.models.ai_answer import AIAnswer
from app.models.post import Post
from app.routers.ws import manager as ws_manager
from app.services.ai_service import DEGRADED_ANSWER, generate_answer_stream
from app.services.retrieval_service import RetrievalService

logger = logging.getLogger(__name__)

# 后台任务引用集合，防止任务被 GC 回收导致中途取消
_background_tasks: set[asyncio.Task] = set()


async def generate_ai_answer_background(post_id: str, ai_answer_id: str):
    """AI 答案生成的异步编排函数。

    流程：
    1. 从数据库获取帖子标题与正文
    2. 双路检索获取上下文来源与检索路径
    3. 评估置信度
    4. 调用 DeepSeek 流式生成，逐 token 通过 WebSocket 推送
    5. 拼接完整答案并持久化
    6. 推送完成事件

    任何步骤异常时降级为 DEGRADED_ANSWER 并推送 error 事件。
    """
    try:
        # 1. 获取帖子内容
        async with AsyncSessionLocal() as session:
            result = await session.execute(
                select(Post).where(Post.id == post_id, Post.deleted_at.is_(None))
            )
            post = result.scalar_one_or_none()
            if post is None:
                logger.error("AI 答案生成中止：帖子不存在 post_id=%s", post_id)
                return
            title, content = post.title, post.content

        # 2. 双路检索获取上下文来源与检索路径
        sources, retrieval_path = await RetrievalService.retrieve(f"{title} {content}")

        # 3. 评估置信度
        confidence = RetrievalService.assess_confidence(sources)

        # 4. 流式生成并逐 token 推送
        full_content = ""
        async for token in generate_answer_stream(title, content, sources):
            full_content += token
            await ws_manager.send_to_post(
                post_id, {"type": "token", "content": token}
            )

        # 5. 持久化完整答案（流式模式下 usage 不可用，置空 dict）
        async with AsyncSessionLocal() as session:
            await session.execute(
                update(AIAnswer)
                .where(AIAnswer.id == ai_answer_id)
                .values(
                    status="published",
                    content=full_content,
                    sources=sources,
                    confidence=confidence,
                    retrieval_path=retrieval_path,
                    model_name=settings.DEEPSEEK_MODEL,
                    token_usage={},
                )
            )
            await session.commit()

        # 6. 推送完成事件
        await ws_manager.send_to_post(
            post_id,
            {
                "type": "done",
                "content": full_content,
                "sources": sources,
                "confidence": confidence,
                "retrievalPath": retrieval_path,
            },
        )
        logger.info(
            "AI 答案生成完成 post_id=%s ai_answer_id=%s", post_id, ai_answer_id
        )

    except Exception:
        logger.exception("AI 答案生成编排失败 post_id=%s", post_id)
        # 降级：更新记录为降级文案
        try:
            async with AsyncSessionLocal() as session:
                await session.execute(
                    update(AIAnswer)
                    .where(AIAnswer.id == ai_answer_id)
                    .values(
                        status="published",
                        content=DEGRADED_ANSWER,
                        confidence="low",
                        model_name=settings.DEEPSEEK_MODEL,
                    )
                )
                await session.commit()
        except Exception:
            logger.exception("降级写入失败 ai_answer_id=%s", ai_answer_id)

        # 推送 error 事件
        await ws_manager.send_to_post(
            post_id, {"type": "error", "content": DEGRADED_ANSWER}
        )


def schedule_ai_answer_generation(post_id: str, ai_answer_id: str) -> None:
    """调度 AI 答案生成后台任务，持有引用以防被 GC 回收。"""
    task = asyncio.create_task(
        generate_ai_answer_background(post_id, ai_answer_id)
    )
    _background_tasks.add(task)
    task.add_done_callback(_background_tasks.discard)
