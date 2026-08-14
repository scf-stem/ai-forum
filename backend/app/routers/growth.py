"""Points rewards, recommendations, writing assistance and follow-ups."""
import json
import math
import re
import time
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, Header, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.middleware.auth import get_current_user, get_current_user_optional
from app.models.ai_answer import AIAnswer
from app.models.board import Board
from app.models.growth import AIFollowUp, AnalyticsEvent, ContentReward, PointLedger, PostSimilarity
from app.models.post import Post
from app.models.reply import Reply
from app.models.user import User
from app.redis_client import redis_client
from app.routers.boards import _build_post_list_item
from app.schemas.platform import FollowUpRequest, RewardRequest, WritingAssistRequest
from app.services.ai_service import generate_specialized
from app.services.community_service import apply_reputation, create_notification
from app.services.growth_service import event_weight, record_event
from app.routers.notifications import push_notification

router = APIRouter()


@router.post("/rewards", status_code=status.HTTP_201_CREATED)
async def reward_content(payload: RewardRequest, idempotency_key: str = Header(..., alias="Idempotency-Key"),
                         user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)) -> dict:
    existing = (await db.execute(select(ContentReward).where(
        ContentReward.from_user_id == user.id, ContentReward.idempotency_key == idempotency_key
    ))).scalar_one_or_none()
    if existing:
        return {"id": str(existing.id), "amount": existing.amount, "points_balance": user.points_balance, "duplicate": True}

    if payload.target_type == "post":
        target = (await db.execute(select(Post).where(Post.id == payload.target_id, Post.deleted_at.is_(None)).with_for_update())).scalar_one_or_none()
        post = target
    else:
        target = (await db.execute(select(Reply).where(Reply.id == payload.target_id, Reply.deleted_at.is_(None)).with_for_update())).scalar_one_or_none()
        post = (await db.execute(select(Post).where(Post.id == target.post_id))).scalar_one_or_none() if target else None
    if target is None or post is None:
        raise HTTPException(status_code=404, detail="打赏内容不存在")
    if target.is_folded:
        raise HTTPException(status_code=400, detail="不能打赏已折叠内容")
    if str(target.author_id) == str(user.id):
        raise HTTPException(status_code=400, detail="不能打赏自己的内容")

    locked_users = (await db.execute(select(User).where(
        User.id.in_([user.id, target.author_id])).order_by(User.id).with_for_update())).scalars().all()
    users_by_id = {str(item.id): item for item in locked_users}
    sender = users_by_id[str(user.id)]
    recipient = users_by_id[str(target.author_id)]
    existing = (await db.execute(select(ContentReward).where(
        ContentReward.from_user_id == sender.id,
        ContentReward.idempotency_key == idempotency_key))).scalar_one_or_none()
    if existing:
        return {"id": str(existing.id), "amount": existing.amount,
                "points_balance": sender.points_balance, "duplicate": True}
    today = datetime.now(timezone.utc).date()
    spent = (await db.execute(select(func.coalesce(func.sum(ContentReward.amount), 0)).where(
        ContentReward.from_user_id == user.id, func.date(ContentReward.created_at) == today
    ))).scalar_one()
    if int(spent) + payload.amount > 1000:
        raise HTTPException(status_code=429, detail="今日打赏积分已达上限")
    if sender.points_balance < payload.amount:
        raise HTTPException(status_code=409, detail="积分余额不足")
    sender.points_balance -= payload.amount
    recipient.points_balance += payload.amount
    reward = ContentReward(from_user_id=sender.id, to_user_id=recipient.id,
                           target_type=payload.target_type, target_id=target.id,
                           post_id=post.id, amount=payload.amount,
                           idempotency_key=idempotency_key)
    db.add(reward); await db.flush()
    db.add_all([
        PointLedger(user_id=sender.id, delta=-payload.amount, balance_after=sender.points_balance,
                    reason="reward_sent", event_key=f"reward:{reward.id}:sent", ref_id=reward.id),
        PointLedger(user_id=recipient.id, delta=payload.amount, balance_after=recipient.points_balance,
                    reason="reward_received", event_key=f"reward:{reward.id}:received", ref_id=reward.id),
    ])
    await apply_reputation(db, user_id=recipient.id, delta=2, reason="bounty_received",
                           event_key=f"reward:{reward.id}:reputation", ref_type="reward", ref_id=reward.id)
    notification = await create_notification(db, user_id=recipient.id, type="reward", actor_id=sender.id,
                              post_id=post.id, reply_id=target.id if payload.target_type == "reply" else None,
                              title=f"{sender.username} 向你的内容打赏了 {payload.amount} 积分", body=post.title)
    await record_event(db, event_name="reward_sent", user_id=sender.id, post_id=post.id,
                       board_id=post.board_id, properties={"amount": payload.amount, "target_type": payload.target_type})
    await db.commit()
    await push_notification(notification)
    return {"id": str(reward.id), "amount": reward.amount,
            "points_balance": sender.points_balance, "duplicate": False}


@router.get("/points/ledger")
async def point_history(page: int = Query(1, ge=1), page_size: int = Query(20, ge=1, le=100),
                        user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)) -> dict:
    total = (await db.execute(select(func.count()).select_from(PointLedger).where(PointLedger.user_id == user.id))).scalar_one()
    items = (await db.execute(select(PointLedger).where(PointLedger.user_id == user.id)
                              .order_by(PointLedger.created_at.desc()).offset((page - 1) * page_size).limit(page_size))).scalars().all()
    return {"items": items, "total": total, "page": page, "page_size": page_size,
            "has_more": page * page_size < total, "balance": user.points_balance}


def _normalize(values: list[float]) -> list[float]:
    if not values:
        return []
    low, high = min(values), max(values)
    if high == low:
        return [1.0 if high > 0 else 0.0 for _ in values]
    return [(v - low) / (high - low) for v in values]


@router.get("/feed")
async def personalized_feed(mode: str = Query("for_you", pattern="^(for_you|hot|latest)$"),
                            page: int = Query(1, ge=1), page_size: int = Query(20, ge=1, le=50),
                            user: User | None = Depends(get_current_user_optional), db: AsyncSession = Depends(get_db)) -> dict:
    rows = (await db.execute(select(Post, User, Board).join(User, Post.author_id == User.id)
        .join(Board, Post.board_id == Board.id).where(Post.deleted_at.is_(None), Post.status == "published", Post.is_folded.is_(False))
        .order_by(Post.created_at.desc()).limit(300))).all()
    if not rows:
        return {"items": [], "total": 0, "page": page, "page_size": page_size, "has_more": False, "strategy": "empty"}
    now = datetime.now(timezone.utc)
    votes = _normalize([max(0, p.vote_count) for p, _, _ in rows])
    replies = _normalize([p.reply_count for p, _, _ in rows])
    views = _normalize([p.view_count for p, _, _ in rows])
    scored = []
    strategy = "hot"
    recent_post_scores: dict[str, int] = {}
    behavior_weight = distinct_posts = 0
    excluded: set[str] = set()
    if user and user.personalization_enabled:
        cutoff = now - timedelta(days=30)
        events = (await db.execute(select(AnalyticsEvent).where(
            AnalyticsEvent.user_id == user.id, AnalyticsEvent.occurred_at >= cutoff,
            AnalyticsEvent.post_id.is_not(None)))).scalars().all()
        behavior_weight = sum(event_weight(e.event_name, e.properties) for e in events)
        distinct_posts = len({str(e.post_id) for e in events if event_weight(e.event_name, e.properties) > 0})
        excluded = {str(e.post_id) for e in events if e.event_name == "post_open" and e.occurred_at >= now - timedelta(days=7)}
        excluded.update(str(e.post_id) for e in events if e.event_name == "negative_feedback" or
                        (e.event_name == "vote_cast" and e.properties.get("direction") == "down"))
        positive = [e.post_id for e in events if event_weight(e.event_name, e.properties) > 0]
        if positive:
            similarities = (await db.execute(select(PostSimilarity).where(PostSimilarity.post_id.in_(positive)))).scalars().all()
            for item in similarities:
                recent_post_scores[str(item.similar_post_id)] = recent_post_scores.get(str(item.similar_post_id), 0) + item.score
    cf_norm_values = _normalize([float(recent_post_scores.get(str(p.id), 0)) for p, _, _ in rows])
    for idx, (post, author, board) in enumerate(rows):
        age_hours = max(0.0, (now - post.created_at).total_seconds() / 3600)
        freshness = math.exp(-age_hours / 336)
        hot = .40 * votes[idx] + .20 * replies[idx] + .15 * views[idx] + .25 * math.exp(-age_hours / 168)
        tag_match = 0.0
        if user and user.tech_stack:
            user_tags = {str(t).lower() for t in user.tech_stack}
            tag_match = len(user_tags & {str(t).lower() for t in post.tags or []}) / max(1, len(user_tags))
        reason = "本周热门"
        if mode == "latest":
            score = post.created_at.timestamp(); strategy = "latest"
        elif mode == "hot" or user is None or not user.personalization_enabled:
            score = hot; strategy = "hot"
        elif behavior_weight < 20 or distinct_posts < 5:
            score = .50 * tag_match + .30 * hot + .20 * freshness; strategy = "cold_start"
            if tag_match: reason = "与你的技术栈相关"
        else:
            score = .25 * tag_match + .20 * hot + .15 * freshness + .40 * cf_norm_values[idx]; strategy = "cooccurrence"
            if cf_norm_values[idx] > 0: reason = "浏览相似内容的用户也看过"
        if user and (str(post.author_id) == str(user.id) or str(post.id) in excluded):
            continue
        scored.append((score, post, author, board, reason))
    scored.sort(key=lambda item: item[0], reverse=True)
    diversified = []
    board_counts: dict[str, int] = {}; author_counts: dict[str, int] = {}
    for item in scored:
        _, post, author, board, _ = item
        if len(diversified) < 10 and (board_counts.get(str(board.id), 0) >= 3 or author_counts.get(str(author.id), 0) >= 2):
            continue
        diversified.append(item); board_counts[str(board.id)] = board_counts.get(str(board.id), 0) + 1; author_counts[str(author.id)] = author_counts.get(str(author.id), 0) + 1
    start, end = (page - 1) * page_size, page * page_size
    items = []
    for score, post, author, board, reason in diversified[start:end]:
        data = _build_post_list_item(post, author, board).model_dump()
        data.update({"recommendation_reason": reason, "recommendation_score": round(float(score), 4)})
        items.append(data)
    return {"items": items, "total": len(diversified), "page": page, "page_size": page_size,
            "has_more": end < len(diversified), "strategy": strategy}


@router.get("/recommendations/boards")
async def recommended_boards(limit: int = Query(5, ge=1, le=20),
                             user: User | None = Depends(get_current_user_optional),
                             db: AsyncSession = Depends(get_db)) -> dict:
    cutoff = datetime.now(timezone.utc) - timedelta(days=30)
    rows = (await db.execute(select(Board, func.count(Post.id).label("activity")).outerjoin(
        Post, (Post.board_id == Board.id) & (Post.created_at >= cutoff) &
        Post.deleted_at.is_(None)).group_by(Board.id).order_by(func.count(Post.id).desc())
        .limit(limit * 3))).all()
    user_tags = {tag.lower() for tag in (user.tech_stack if user else [])}
    scored = []
    for board, activity in rows:
        match = 1 if board.name.lower() in user_tags else 0
        scored.append((match, int(activity), board))
    scored.sort(key=lambda item: (item[0], item[1]), reverse=True)
    return {"items": [{"id": str(board.id), "name": board.name, "tier": board.tier,
        "activity": activity, "reason": "与你的技术栈相关" if match else "近期活跃版块"}
        for match, activity, board in scored[:limit]]}


@router.get("/recommendations/authors")
async def active_authors(limit: int = Query(5, ge=1, le=20),
                         user: User | None = Depends(get_current_user_optional),
                         db: AsyncSession = Depends(get_db)) -> dict:
    cutoff = datetime.now(timezone.utc) - timedelta(days=30)
    rows = (await db.execute(select(User, func.count(Reply.id).label("replies")).join(
        Reply, Reply.author_id == User.id).where(Reply.created_at >= cutoff,
        Reply.deleted_at.is_(None), User.is_admin.is_(False), User.is_system.is_(False))
        .group_by(User.id).order_by(func.count(Reply.id).desc(), User.reputation.desc())
        .limit(limit + 1))).all()
    return {"items": [{"id": str(author.id), "username": author.username,
        "avatar": author.avatar, "level": author.level, "reputation": author.reputation,
        "recent_replies": int(replies), "reason": "近 30 天活跃回答者"}
        for author, replies in rows if user is None or str(author.id) != str(user.id)][:limit]}


@router.post("/ai/writing-assist")
async def writing_assist(payload: WritingAssistRequest, user: User = Depends(get_current_user),
                         db: AsyncSession = Depends(get_db)) -> dict:
    minute_key = f"writing:minute:{user.id}:{datetime.now(timezone.utc).strftime('%Y%m%d%H%M')}"
    day_key = f"writing:day:{user.id}:{datetime.now(timezone.utc).strftime('%Y%m%d')}"
    minute_count = await redis_client.incr(minute_key); await redis_client.expire(minute_key, 120)
    day_count = await redis_client.incr(day_key); await redis_client.expire(day_key, 172800)
    if minute_count > 5 or day_count > 30:
        raise HTTPException(status_code=429, detail="AI 写作辅助调用过于频繁")
    prompts = {
        "polish": "你是技术编辑。仅润色表达，不改变事实、代码、链接和结论；输出完整润色稿，不要代写新内容。",
        "format_code": "你是 Markdown 编辑。只补全和规范代码围栏与缩进，不执行代码、不改变代码语义；输出完整正文。",
        "summarize": "为技术帖子生成不超过 200 字的中文摘要，只概括原文已有信息。",
        "suggest_tags": "从正文提取最多五个技术标签，只输出 JSON 字符串数组，不输出解释。",
    }
    started = time.monotonic()
    try:
        result, usage = await generate_specialized(prompts[payload.action], f"标题：{payload.title}\n\n正文：{payload.content}")
    except Exception as exc:
        raise HTTPException(status_code=503, detail="AI 写作辅助暂不可用") from exc
    tags = []
    if payload.action == "suggest_tags":
        try:
            tags = json.loads(re.search(r"\[[\s\S]*\]", result).group(0))[:5]
        except Exception:
            tags = [t.strip() for t in result.split(",") if t.strip()][:5]
    await record_event(db, event_name="write_assist_used", user_id=user.id,
                       properties={"action": payload.action, "prompt_version": "writing-v1",
                                   "latency_ms": int((time.monotonic() - started) * 1000), "token_usage": usage})
    await db.commit()
    return {"action": payload.action, "content": result if payload.action != "suggest_tags" else None,
            "tags": tags, "prompt_version": "writing-v1", "token_usage": usage}


@router.post("/ai-answers/{answer_id}/follow-ups")
async def follow_up(answer_id: str, payload: FollowUpRequest, user: User = Depends(get_current_user),
                    db: AsyncSession = Depends(get_db)) -> dict:
    row = (await db.execute(select(AIAnswer, Post, Board).join(Post, AIAnswer.post_id == Post.id)
                            .join(Board, Post.board_id == Board.id).where(AIAnswer.id == answer_id))).first()
    if not row:
        raise HTTPException(status_code=404, detail="AI 答案不存在")
    answer, post, board = row
    prior = (await db.execute(select(AIFollowUp).where(AIFollowUp.ai_answer_id == answer.id,
            AIFollowUp.user_id == user.id).order_by(AIFollowUp.created_at.desc()).limit(2))).scalars().all()
    intent = bool(re.search(r"是什么|什么意思|看不懂|通俗|举例|what is|explain", payload.question, re.I))
    prior_basic = bool(prior and re.search(r"是什么|什么意思|看不懂|通俗|举例|what is|explain", prior[0].question, re.I))
    simplified = (user.role == "beginner" and board.tier == "entry") or (intent and prior_basic)
    mode = "simplified" if simplified else "normal"
    system = ("用初学者能懂的中文回答，必须包含生活化例子和‘术语表’小节。" if simplified else
              "基于原答案回答后续技术问题，保持准确、简洁，不编造来源。")
    content, usage = await generate_specialized(system, f"原问题：{post.title}\n原答案：{answer.content}\n追问：{payload.question}")
    glossary = []
    if simplified:
        for line in content.splitlines():
            if "：" in line and len(line) < 120:
                term, desc = line.lstrip("-* ").split("：", 1)
                if term and desc: glossary.append({"term": term, "description": desc})
        glossary = glossary[:8]
    item = AIFollowUp(ai_answer_id=answer.id, user_id=user.id, question=payload.question,
                      answer=content, mode=mode, glossary=glossary)
    db.add(item)
    await record_event(db, event_name="ai_followup", user_id=user.id, post_id=post.id,
                       board_id=board.id, properties={"mode": mode, "token_usage": usage})
    await db.commit(); await db.refresh(item)
    return {"id": str(item.id), "answer": content, "mode": mode, "glossary": glossary,
            "prompt_version": item.prompt_version, "created_at": item.created_at}
