"""投票路由。

提供投票（赞/踩/取消）与批量查询投票状态接口。
"""
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.middleware.auth import get_current_user
from app.models.post import Post
from app.models.reply import Reply
from app.models.user import User
from app.models.vote import Vote
from app.schemas.vote import VoteCreate, VoteStatusResponse

router = APIRouter()


async def _get_target(
    target_type: str, target_id: str, db: AsyncSession
) -> Post | Reply:
    """根据目标类型查询目标实体（Post 或 Reply），并校验未删除。"""
    if target_type == "post":
        result = await db.execute(
            select(Post).where(Post.id == target_id, Post.deleted_at.is_(None))
        )
        target = result.scalar_one_or_none()
    else:
        result = await db.execute(
            select(Reply).where(Reply.id == target_id, Reply.deleted_at.is_(None))
        )
        target = result.scalar_one_or_none()

    if target is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="投票目标不存在")
    return target


@router.post("/vote")
async def vote(
    payload: VoteCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """投票：支持赞、踩、取消与切换方向，原子操作保证一致性。"""
    # 校验目标存在
    target = await _get_target(payload.target_type, payload.target_id, db)

    # 查询是否已有投票记录
    existing_result = await db.execute(
        select(Vote).where(
            Vote.user_id == user.id,
            Vote.target_type == payload.target_type,
            Vote.target_id == payload.target_id,
        )
    )
    existing_vote = existing_result.scalar_one_or_none()

    # 投票方向对应的计数增量：up=+1, down=-1
    delta = 1 if payload.direction == "up" else -1

    if existing_vote is None:
        # 无记录：创建新投票
        new_vote = Vote(
            user_id=user.id,
            target_type=payload.target_type,
            target_id=payload.target_id,
            direction=payload.direction,
        )
        db.add(new_vote)
        target.vote_count = (target.vote_count or 0) + delta
        message = "投票成功"
    elif existing_vote.direction == payload.direction:
        # 方向相同：取消投票
        await db.delete(existing_vote)
        target.vote_count = (target.vote_count or 0) - delta
        message = "已取消投票"
    else:
        # 方向不同：切换方向（净变化为新方向的 2 倍）
        existing_vote.direction = payload.direction
        target.vote_count = (target.vote_count or 0) + 2 * delta
        message = "已切换投票方向"

    await db.commit()
    return {
        "detail": message,
        "vote_count": target.vote_count,
    }


@router.get("/vote/status", response_model=VoteStatusResponse)
async def get_vote_status(
    target_type: str = Query(..., pattern="^(post|reply)$"),
    target_ids: str = Query(..., description="逗号分隔的目标 ID 列表"),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> VoteStatusResponse:
    """批量查询当前用户对多个目标的投票状态。"""
    # 解析目标 ID 列表
    ids = [tid.strip() for tid in target_ids.split(",") if tid.strip()]
    if not ids:
        return VoteStatusResponse(statuses={})

    result = await db.execute(
        select(Vote).where(
            Vote.user_id == user.id,
            Vote.target_type == target_type,
            Vote.target_id.in_(ids),
        )
    )
    votes = result.scalars().all()
    statuses = {str(vote.target_id): vote.direction for vote in votes}

    return VoteStatusResponse(statuses=statuses)
