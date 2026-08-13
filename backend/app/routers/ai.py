"""AI 答案相关 REST 端点。

提供 AI 答案重新生成接口，仅帖子作者可调用。
"""
import logging

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import get_db
from app.middleware.auth import get_current_user
from app.models.ai_answer import AIAnswer
from app.models.post import Post
from app.models.user import User
from app.services.ai_orchestrator import schedule_ai_answer_generation

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/posts/{post_id}/ai-answer/regenerate")
async def regenerate_ai_answer(
    post_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    """重新生成 AI 答案（仅帖子作者可调用）。

    流程：校验帖子存在且为提问类型 → 校验作者权限 → 删除旧 AI 答案 →
    创建新的 generating 态记录 → 回写 post.ai_answer_id → 异步启动生成。
    """
    # 1. 查询帖子，校验存在且未删除
    result = await db.execute(
        select(Post).where(Post.id == post_id, Post.deleted_at.is_(None))
    )
    post = result.scalar_one_or_none()
    if post is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="帖子不存在")

    # 校验帖子类型为提问
    if post.type != "question":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="仅提问帖可重新生成 AI 答案",
        )

    # 2. 校验当前用户是帖子作者
    if str(post.author_id) != str(current_user.id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="无权操作该帖子"
        )

    # 3. 删除旧 AI 答案记录
    await db.execute(delete(AIAnswer).where(AIAnswer.post_id == post.id))

    # 4. 创建新 AIAnswer 记录（generating 态）
    ai_answer = AIAnswer(
        post_id=post.id,
        status="generating",
        content="",
        sources=[],
        confidence="medium",
        retrieval_path="hybrid",
        model_name=settings.DEEPSEEK_MODEL,
    )
    db.add(ai_answer)
    await db.flush()  # 获取 server_default 生成的 id

    # 5. 回写 post.ai_answer_id
    post.ai_answer_id = ai_answer.id
    await db.commit()

    # 6. 异步启动生成，不阻塞响应
    schedule_ai_answer_generation(str(post.id), str(ai_answer.id))

    logger.info(
        "AI 答案重新生成已调度 post_id=%s ai_answer_id=%s",
        post_id,
        ai_answer.id,
    )

    # 7. 返回
    return {
        "message": "AI 答案正在重新生成",
        "ai_answer_id": str(ai_answer.id),
    }
