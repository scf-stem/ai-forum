"""Acceptance, reputation leaderboard and AI feedback endpoints."""
from datetime import datetime, timedelta, timezone
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.middleware.auth import get_current_user
from app.models.ai_answer import AIAnswer
from app.models.board import Board
from app.models.community import AIAnswerFeedback, ReputationLog
from app.models.post import Post
from app.models.reply import Reply
from app.models.user import User
from app.schemas.platform import AIFeedbackRequest, AcceptReplyRequest
from app.services.community_service import (apply_reputation, create_notification,
    deactivate_index, index_content, reverse_active_reputation)
from app.services.community_service import restore_ai_answer_if_allowed
from app.services.growth_service import record_event
from app.routers.notifications import push_notification

router = APIRouter()


@router.put("/posts/{post_id}/accepted-reply")
async def set_accepted_reply(post_id: str, payload: AcceptReplyRequest,
                             user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)) -> dict:
    post = (await db.execute(select(Post).where(Post.id == post_id, Post.deleted_at.is_(None)).with_for_update())).scalar_one_or_none()
    if post is None:
        raise HTTPException(status_code=404, detail="帖子不存在")
    if str(post.author_id) != str(user.id):
        raise HTTPException(status_code=403, detail="只有提问者可以采纳回复")
    if post.type != "question":
        raise HTTPException(status_code=400, detail="只有提问帖支持采纳")

    old_reply = None
    if post.accepted_reply_id:
        old_reply = (await db.execute(select(Reply).where(Reply.id == post.accepted_reply_id).with_for_update())).scalar_one_or_none()
    new_reply = None
    if payload.reply_id:
        new_reply = (await db.execute(select(Reply).where(
            Reply.id == payload.reply_id, Reply.post_id == post.id,
            Reply.parent_id.is_(None), Reply.deleted_at.is_(None),
        ).with_for_update())).scalar_one_or_none()
        if new_reply is None or new_reply.kind not in ("supplement", "correction"):
            raise HTTPException(status_code=400, detail="只能采纳同帖的一级补充或纠错")
        if str(new_reply.author_id) == str(user.id):
            raise HTTPException(status_code=400, detail="不能采纳自己的回复")
    if old_reply and new_reply and str(old_reply.id) == str(new_reply.id):
        return {"accepted_reply_id": str(new_reply.id)}

    if old_reply and (new_reply is None or str(old_reply.id) != str(new_reply.id)):
        old_reply.is_accepted = False
        await deactivate_index(db, "accepted_reply", old_reply.id)
        for reason in ("answer_accepted", "correction_verified", "onboarding_help"):
            await reverse_active_reputation(db, user_id=old_reply.author_id, reason=reason,
                                            ref_type="reply", ref_id=old_reply.id)

    post.accepted_reply_id = new_reply.id if new_reply else None
    ai_answer = (await db.execute(select(AIAnswer).where(AIAnswer.post_id == post.id))).scalar_one_or_none()
    if (ai_answer and old_reply and ai_answer.corrected_by_reply_id and
            str(ai_answer.corrected_by_reply_id) == str(old_reply.id)):
        ai_answer.corrected_by_reply_id = None
        await restore_ai_answer_if_allowed(db, ai_answer)
    notification = None
    if new_reply:
        award_cycle = uuid4()
        new_reply.is_accepted = True
        await apply_reputation(db, user_id=new_reply.author_id, delta=15, reason="answer_accepted",
                               event_key=f"accept:{new_reply.id}:{award_cycle}:base", ref_type="reply", ref_id=new_reply.id)
        if new_reply.kind == "correction":
            await apply_reputation(db, user_id=new_reply.author_id, delta=10, reason="correction_verified",
                                   event_key=f"accept:{new_reply.id}:{award_cycle}:correction", ref_type="reply", ref_id=new_reply.id)
            if ai_answer:
                ai_answer.corrected_by_reply_id = new_reply.id
                ai_answer.status = "folded"
                await deactivate_index(db, "high_confidence_ai_answer", ai_answer.id)
        board = (await db.execute(select(Board).where(Board.id == post.board_id))).scalar_one()
        if board.tier == "entry":
            await apply_reputation(db, user_id=new_reply.author_id, delta=5, reason="onboarding_help",
                                   event_key=f"accept:{new_reply.id}:{award_cycle}:entry", ref_type="reply", ref_id=new_reply.id)
        await index_content(db, source_type="accepted_reply", source_id=new_reply.id,
                            post=post, content=new_reply.content, quality_score=100 + new_reply.vote_count)
        notification = await create_notification(db, user_id=new_reply.author_id, type="accepted", actor_id=user.id,
                                  post_id=post.id, reply_id=new_reply.id,
                                  title=f"{user.username} 采纳了你的回答", body=post.title)
        await record_event(db, event_name="reply_accepted", user_id=user.id, post_id=post.id,
                           board_id=post.board_id, properties={"kind": new_reply.kind})
    if (ai_answer and ai_answer.confidence == "high" and
            ai_answer.corrected_by_reply_id is None and ai_answer.status != "folded"):
        await index_content(db, source_type="high_confidence_ai_answer",
                            source_id=ai_answer.id, post=post,
                            content=ai_answer.content, quality_score=50)
    await db.commit()
    await push_notification(notification)
    return {"accepted_reply_id": str(new_reply.id) if new_reply else None}


@router.post("/ai-answers/{answer_id}/feedback")
async def feedback(answer_id: str, payload: AIFeedbackRequest,
                   user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)) -> dict:
    answer = (await db.execute(select(AIAnswer).where(AIAnswer.id == answer_id))).scalar_one_or_none()
    if answer is None:
        raise HTTPException(status_code=404, detail="AI 答案不存在")
    item = (await db.execute(select(AIAnswerFeedback).where(
        AIAnswerFeedback.ai_answer_id == answer.id, AIAnswerFeedback.user_id == user.id
    ))).scalar_one_or_none()
    if item:
        item.value, item.reason = payload.value, payload.reason
    else:
        db.add(AIAnswerFeedback(ai_answer_id=answer.id, user_id=user.id, value=payload.value, reason=payload.reason))
    if payload.value == "helpful" and answer.status == "published":
        answer.status = "verified"
    await db.commit()
    return {"detail": "反馈已记录", "value": payload.value}


@router.get("/reputation/leaderboard")
async def leaderboard(window: str = Query("week", pattern="^(week|month|all)$"), limit: int = Query(20, ge=1, le=100),
                      db: AsyncSession = Depends(get_db)) -> dict:
    query = select(User.id, User.username, User.avatar, User.reputation, User.level)
    if window != "all":
        cutoff = datetime.now(timezone.utc) - timedelta(days=7 if window == "week" else 30)
        points = select(ReputationLog.user_id, func.sum(ReputationLog.delta).label("window_score")).where(
            ReputationLog.created_at >= cutoff).group_by(ReputationLog.user_id).subquery()
        query = select(User.id, User.username, User.avatar, User.reputation, User.level, points.c.window_score).join(
            points, points.c.user_id == User.id).order_by(points.c.window_score.desc())
    else:
        query = query.order_by(User.reputation.desc())
    rows = (await db.execute(query.limit(limit))).mappings().all()
    return {"items": [dict(row) for row in rows], "window": window}
