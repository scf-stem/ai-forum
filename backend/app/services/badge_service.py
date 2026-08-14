"""Fixed, versioned badge award rules."""
from datetime import datetime, timedelta, timezone

from sqlalchemy import Integer, cast, distinct, func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.community import ReputationLog, UserBadge
from app.models.growth import AnalyticsEvent, ContentReward
from app.models.post import Post
from app.models.reply import Reply

BADGE_RULES_VERSION = "2026-08-v1"


async def _award(db: AsyncSession, user_id, code: str, metadata: dict | None = None) -> None:
    await db.execute(insert(UserBadge).values(user_id=user_id, badge_code=code,
        metadata_json={"rules_version": BADGE_RULES_VERSION, **(metadata or {})}).on_conflict_do_nothing(
        index_elements=[UserBadge.user_id, UserBadge.badge_code]))


async def evaluate_badges(db: AsyncSession) -> int:
    now = datetime.now(timezone.utc); awarded = 0
    quality_rows = (await db.execute(select(Reply.author_id, func.count(Reply.id),
        func.sum(cast(Reply.is_accepted, Integer))).where(
        Reply.parent_id.is_(None), Reply.created_at >= now - timedelta(days=90),
        Reply.deleted_at.is_(None)).group_by(Reply.author_id))).all()
    for user_id, total, accepted in quality_rows:
        if total >= 15 and int(accepted or 0) / total >= .4:
            await _award(db, user_id, "high_quality_answerer"); awarded += 1
    fast_rows = (await db.execute(select(Reply.author_id).join(Post, Reply.post_id == Post.id).where(
        Reply.is_accepted.is_(True), Reply.vote_count >= 50,
        Reply.created_at <= Post.created_at + timedelta(minutes=30)).distinct())).scalars().all()
    for user_id in fast_rows:
        await _award(db, user_id, "lightning_reply"); awarded += 1
    stars = (await db.execute(select(ReputationLog.user_id, func.sum(ReputationLog.delta)).where(
        ReputationLog.created_at >= now - timedelta(days=7)).group_by(ReputationLog.user_id)
        .having(func.sum(ReputationLog.delta) >= 200))).all()
    for user_id, score in stars:
        await _award(db, user_id, "community_star", {"rolling_score": int(score)}); awarded += 1
    active = (await db.execute(select(AnalyticsEvent.user_id).where(
        AnalyticsEvent.user_id.is_not(None), AnalyticsEvent.occurred_at >= now - timedelta(days=60))
        .group_by(AnalyticsEvent.user_id).having(func.count(distinct(func.date(AnalyticsEvent.occurred_at))) >= 60))).scalars().all()
    for user_id in active:
        await _award(db, user_id, "continuous_active"); awarded += 1
    generous = (await db.execute(select(ContentReward.from_user_id).group_by(ContentReward.from_user_id)
        .having(func.count(distinct(ContentReward.to_user_id)) >= 50))).scalars().all()
    for user_id in generous:
        await _award(db, user_id, "generous_rewarder"); awarded += 1
    first_this_month = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    prior_start = (first_this_month - timedelta(days=1)).replace(day=1)
    leaders = (await db.execute(select(ReputationLog.user_id, func.sum(ReputationLog.delta).label("score")).where(
        ReputationLog.created_at >= prior_start, ReputationLog.created_at < first_this_month)
        .group_by(ReputationLog.user_id).order_by(func.sum(ReputationLog.delta).desc()).limit(3))).all()
    for rank, (user_id, score) in enumerate(leaders, start=1):
        await _award(db, user_id, f"monthly_top3_{prior_start:%Y%m}", {"rank": rank, "score": int(score)}); awarded += 1
    await db.commit()
    return awarded
