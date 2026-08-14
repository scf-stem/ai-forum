"""Analytics event recording and incremental item-item similarity."""
from datetime import datetime, timedelta, timezone
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.growth import AnalyticsEvent, PostSimilarity
from app.models.user import User

EVENT_WEIGHTS = {"post_open": 1, "vote_cast": 3, "reply_created": 4,
                 "reply_accepted": 5, "reward_sent": 5}


def event_weight(event_name: str, properties: dict | None = None) -> int:
    if event_name == "vote_cast" and (properties or {}).get("direction") != "up":
        return 0
    return EVENT_WEIGHTS.get(event_name, 0)


async def record_event(db: AsyncSession, *, event_name: str, user_id=None,
                       post_id=None, board_id=None, properties: dict | None = None,
                       event_id=None, anonymous_id=None, session_id=None,
                       occurred_at=None, source="server") -> None:
    if user_id:
        user = (await db.execute(select(User).where(User.id == user_id))).scalar_one_or_none()
        if user is not None and not user.personalization_enabled and event_name in (*EVENT_WEIGHTS, "negative_feedback"):
            post_id = None
    event = AnalyticsEvent(event_id=event_id or uuid4(), event_name=event_name, user_id=user_id,
                           anonymous_id=anonymous_id, session_id=session_id, post_id=post_id,
                           board_id=board_id, properties=properties or {}, source=source,
                           occurred_at=occurred_at or datetime.now(timezone.utc))
    db.add(event)
    await db.flush()
    weight = event_weight(event_name, properties)
    if user_id and post_id and weight > 0:
        await _update_similarity(db, user_id, post_id, weight)


async def _update_similarity(db: AsyncSession, user_id, post_id, weight: int) -> None:
    cutoff = datetime.now(timezone.utc) - timedelta(days=30)
    recent_events = (await db.execute(
        select(AnalyticsEvent).where(
            AnalyticsEvent.user_id == user_id, AnalyticsEvent.post_id.is_not(None),
            AnalyticsEvent.post_id != post_id, AnalyticsEvent.occurred_at >= cutoff,
            AnalyticsEvent.event_name.in_(tuple(EVENT_WEIGHTS)),
        ).order_by(AnalyticsEvent.occurred_at.desc()).limit(100)
    )).scalars().all()
    recent = [event.post_id for event in recent_events
              if event_weight(event.event_name, event.properties) > 0][:20]
    for other_id in set(recent):
        for left, right in ((post_id, other_id), (other_id, post_id)):
            stmt = insert(PostSimilarity).values(post_id=left, similar_post_id=right, score=weight)
            stmt = stmt.on_conflict_do_update(
                index_elements=[PostSimilarity.post_id, PostSimilarity.similar_post_id],
                set_={"score": PostSimilarity.score + weight, "updated_at": datetime.now(timezone.utc)},
            )
            await db.execute(stmt)
