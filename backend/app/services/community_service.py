"""Transactional Phase 2 community side effects."""
from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.community import Notification, NotificationPreference, ReputationLog, SearchDocument
from app.models.post import Post
from app.models.ai_answer import AIAnswer
from app.models.report import Report
from app.models.user import User
from app.config import settings

LEVEL_THRESHOLDS = [(10, 20000), (9, 10000), (8, 6000), (7, 3000), (6, 1200), (5, 600), (4, 300), (3, 150), (2, 50)]


def level_for_reputation(value: int) -> int:
    for level, threshold in LEVEL_THRESHOLDS:
        if value >= threshold:
            return level
    return 1


async def apply_reputation(
    db: AsyncSession, *, user_id, delta: int, reason: str, event_key: str,
    ref_type: str, ref_id, cap_vote_daily: bool = False,
) -> int:
    """Apply a reputation event once and return the applied delta."""
    if (await db.execute(select(ReputationLog.id).where(ReputationLog.event_key == event_key))).scalar_one_or_none():
        return 0
    user = (await db.execute(select(User).where(User.id == user_id).with_for_update())).scalar_one()
    applied = delta
    if cap_vote_daily and delta > 0:
        today = datetime.now(timezone.utc).date()
        current = (await db.execute(
            select(func.coalesce(func.sum(ReputationLog.delta), 0)).where(
                ReputationLog.user_id == user_id,
                ReputationLog.reason == "content_upvoted",
                func.date(ReputationLog.created_at) == today,
            )
        )).scalar_one()
        applied = max(0, min(delta, 20 - int(current)))
    if applied == 0:
        return 0
    user.reputation = max(0, user.reputation + applied)
    user.level = level_for_reputation(user.reputation)
    db.add(ReputationLog(user_id=user_id, delta=applied, reason=reason, event_key=event_key,
                         ref_type=ref_type, ref_id=ref_id))
    return applied


async def reverse_reputation(db: AsyncSession, original_event_key: str, reverse_event_key: str) -> int:
    original = (await db.execute(select(ReputationLog).where(ReputationLog.event_key == original_event_key))).scalar_one_or_none()
    if original is None:
        return 0
    return await apply_reputation(db, user_id=original.user_id, delta=-original.delta,
                                  reason=f"reversed_{original.reason}"[:40], event_key=reverse_event_key,
                                  ref_type=original.ref_type, ref_id=original.ref_id)


async def reverse_active_reputation(
    db: AsyncSession, *, user_id, reason: str, ref_type: str, ref_id,
    event_key_prefix: str | None = None,
) -> int:
    """Reverse the newest unreversed positive event for one business effect."""
    query = select(ReputationLog).where(
        ReputationLog.user_id == user_id,
        ReputationLog.reason == reason,
        ReputationLog.ref_type == ref_type,
        ReputationLog.ref_id == ref_id,
        ReputationLog.delta > 0,
    )
    if event_key_prefix:
        query = query.where(ReputationLog.event_key.startswith(event_key_prefix))
    originals = (await db.execute(query.order_by(ReputationLog.created_at.desc()))).scalars().all()
    for original in originals:
        reverse_key = f"reversal:{original.id}"
        already_reversed = (await db.execute(select(ReputationLog.id).where(
            ReputationLog.event_key == reverse_key))).scalar_one_or_none()
        if already_reversed is None:
            return await reverse_reputation(db, original.event_key, reverse_key)
    return 0


async def index_content(db: AsyncSession, *, source_type: str, source_id, post: Post,
                        content: str, quality_score: int) -> None:
    stmt = insert(SearchDocument).values(
        source_type=source_type, source_id=source_id, post_id=post.id, title=post.title,
        content=content, tags=post.tags or [], quality_score=quality_score, is_active=True,
        indexed_at=datetime.now(timezone.utc),
    ).on_conflict_do_update(
        constraint="uq_search_documents_source",
        set_={"post_id": post.id, "title": post.title, "content": content,
              "tags": post.tags or [], "quality_score": quality_score, "is_active": True,
              "indexed_at": datetime.now(timezone.utc)},
    )
    await db.execute(stmt)


async def deactivate_index(db: AsyncSession, source_type: str, source_id) -> None:
    doc = (await db.execute(select(SearchDocument).where(
        SearchDocument.source_type == source_type, SearchDocument.source_id == source_id
    ))).scalar_one_or_none()
    if doc:
        doc.is_active = False


async def deactivate_post_index(db: AsyncSession, post_id) -> None:
    documents = (await db.execute(select(SearchDocument).where(
        SearchDocument.post_id == post_id,
        SearchDocument.is_active.is_(True)))).scalars().all()
    for document in documents:
        document.is_active = False


async def refresh_post_index_metadata(db: AsyncSession, post: Post) -> None:
    documents = (await db.execute(select(SearchDocument).where(
        SearchDocument.post_id == post.id))).scalars().all()
    for document in documents:
        document.title = post.title
        document.tags = post.tags or []
        document.indexed_at = datetime.now(timezone.utc)


async def restore_ai_answer_if_allowed(db: AsyncSession, answer: AIAnswer) -> bool:
    report_count = (await db.execute(select(func.count()).select_from(Report).where(
        Report.target_type == "ai_answer", Report.target_id == answer.id))).scalar_one()
    if report_count >= settings.REPORT_THRESHOLD:
        answer.status = "folded"
        return False
    answer.status = "published"
    return True


async def create_notification(
    db: AsyncSession, *, user_id, type: str, title: str, body: str = "",
    actor_id=None, post_id=None, reply_id=None, aggregation_key: str | None = None,
) -> Notification | None:
    if actor_id is not None and str(actor_id) == str(user_id):
        return None
    prefs = (await db.execute(select(NotificationPreference).where(NotificationPreference.user_id == user_id))).scalar_one_or_none()
    if prefs is not None and not getattr(prefs, f"{type}_enabled", True):
        return None
    if aggregation_key:
        existing = (await db.execute(select(Notification).where(Notification.aggregation_key == aggregation_key).with_for_update())).scalar_one_or_none()
        if existing:
            existing.actor_id = actor_id
            existing.actor_count += 1
            existing.title = title
            existing.read_at = None
            existing.updated_at = datetime.now(timezone.utc)
            return existing
    item = Notification(user_id=user_id, type=type, actor_id=actor_id, post_id=post_id,
                        reply_id=reply_id, title=title, body=body,
                        aggregation_key=aggregation_key)
    db.add(item)
    await db.flush()
    return item
