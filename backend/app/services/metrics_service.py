"""KPI rollups with fixed Asia/Shanghai definitions."""
from datetime import date, datetime, time, timedelta
from zoneinfo import ZoneInfo

from sqlalchemy import delete, func, select, text
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.community import AIAnswerFeedback, SearchDocument
from app.models.growth import AnalyticsEvent
from app.models.ops import DailyMetric
from app.models.post import Post
from app.models.ai_answer import AIAnswer
from app.models.user import User

TZ = ZoneInfo("Asia/Shanghai")
QUALIFIED = ("session_started", "post_open", "post_created", "reply_created", "vote_cast", "reply_accepted", "reward_sent", "ai_followup")


async def rollup_day(db: AsyncSession, metric_date: date) -> dict[str, int]:
    start = datetime.combine(metric_date, time.min, TZ)
    end = start + timedelta(days=1)
    eligible_users = select(User.id).where(User.is_admin.is_(False), User.is_system.is_(False)).subquery()
    dau = (await db.execute(select(func.count(func.distinct(AnalyticsEvent.user_id))).where(
        AnalyticsEvent.user_id.in_(select(eligible_users.c.id)), AnalyticsEvent.event_name.in_(QUALIFIED),
        AnalyticsEvent.occurred_at >= start, AnalyticsEvent.occurred_at < end))).scalar_one()
    organic_posts = (await db.execute(select(func.count()).select_from(Post).join(User, Post.author_id == User.id).where(
        Post.origin_type == "user", User.is_admin.is_(False), User.is_system.is_(False),
        Post.deleted_at.is_(None), Post.created_at >= start, Post.created_at < end))).scalar_one()
    seed_posts = (await db.execute(select(func.count()).select_from(Post).where(
        Post.origin_type == "seed_summary", Post.created_at >= start, Post.created_at < end))).scalar_one()
    sedimented = (await db.execute(select(func.count()).select_from(SearchDocument).where(
        SearchDocument.is_active.is_(True), SearchDocument.source_type.in_(("accepted_reply", "high_confidence_ai_answer"))))).scalar_one()
    def basis_points(numerator: int, denominator: int) -> int:
        return round(numerator * 10000 / denominator) if denominator else 0

    matured_end = end - timedelta(days=7)
    ai_rows = (await db.execute(select(AIAnswer, Post).join(Post, AIAnswer.post_id == Post.id).where(
        AIAnswer.created_at < matured_end, AIAnswer.status != "generating"))).all()
    helpful_total = len(ai_rows)
    helpful_ids = set((await db.execute(select(AIAnswerFeedback.ai_answer_id).join(
        AIAnswer, AIAnswerFeedback.ai_answer_id == AIAnswer.id).join(
        Post, AIAnswer.post_id == Post.id).where(
        AIAnswerFeedback.user_id == Post.author_id,
        AIAnswerFeedback.value == "helpful", AIAnswer.created_at < matured_end))).scalars().all())
    high_rows = [answer for answer, _ in ai_rows if answer.confidence == "high"]
    high_helpful = sum(1 for answer in high_rows if answer.id in helpful_ids)

    low_stats = (await db.execute(text("""
        SELECT count(*) total, count(*) FILTER (WHERE EXISTS (
          SELECT 1 FROM ai_answer_feedback f JOIN users u ON u.id=f.user_id
          WHERE f.ai_answer_id=a.id AND f.created_at <= a.created_at + interval '24 hours'
            AND (f.user_id=p.author_id OR u.level >= 3)
        ) OR EXISTS (
          SELECT 1 FROM replies r WHERE r.id=a.corrected_by_reply_id
            AND r.is_accepted AND r.created_at <= a.created_at + interval '24 hours'
        )) verified
        FROM ai_answers a JOIN posts p ON p.id=a.post_id
        WHERE a.confidence='low' AND a.created_at < :cutoff
    """), {"cutoff": end - timedelta(hours=24)})).one()

    acceptance_stats = (await db.execute(text("""
        SELECT count(*) total, count(*) FILTER (WHERE p.accepted_reply_id IS NOT NULL) accepted
        FROM posts p WHERE p.type='question' AND p.deleted_at IS NULL
          AND p.created_at < :cutoff AND EXISTS (
            SELECT 1 FROM replies r WHERE r.post_id=p.id AND r.deleted_at IS NULL)
    """), {"cutoff": matured_end})).one()

    content_stats = (await db.execute(text("""
        SELECT
          (SELECT count(*) FROM posts p JOIN users u ON u.id=p.author_id
             WHERE p.created_at>=:start AND p.created_at<:end AND p.deleted_at IS NULL
               AND NOT u.is_admin AND NOT u.is_system)
          + (SELECT count(*) FROM replies r JOIN users u ON u.id=r.author_id
             WHERE r.created_at>=:start AND r.created_at<:end AND r.deleted_at IS NULL
               AND NOT u.is_admin AND NOT u.is_system) organic,
          (SELECT count(*) FROM posts p WHERE p.created_at>=:start AND p.created_at<:end AND p.deleted_at IS NULL)
          + (SELECT count(*) FROM replies r WHERE r.created_at>=:start AND r.created_at<:end AND r.deleted_at IS NULL) total,
          (SELECT count(*) FROM posts p WHERE p.type='question' AND p.created_at>=:start AND p.created_at<:end AND p.deleted_at IS NULL) questions,
          (SELECT count(*) FROM posts p WHERE p.type='question' AND p.created_at>=:start AND p.created_at<:end AND p.deleted_at IS NULL
             AND EXISTS (SELECT 1 FROM replies r JOIN users u ON u.id=r.author_id WHERE r.post_id=p.id AND r.deleted_at IS NULL
               AND NOT u.is_admin AND NOT u.is_system AND r.created_at <= p.created_at + interval '24 hours')) answered
    """), {"start": start, "end": end})).one()

    retention: dict[str, int] = {}
    for lag in (1, 7):
        cohort_start = start - timedelta(days=lag)
        cohort_end = cohort_start + timedelta(days=1)
        row = (await db.execute(text("""
            WITH cohort AS (
              SELECT DISTINCT u.id FROM users u JOIN analytics_events e ON e.user_id=u.id
              WHERE u.created_at>=:cohort_start AND u.created_at<:cohort_end
                AND e.occurred_at>=:cohort_start AND e.occurred_at<:cohort_end
                AND e.event_name = ANY(:qualified) AND NOT u.is_admin AND NOT u.is_system
            ) SELECT count(*) total, count(*) FILTER (WHERE EXISTS (
              SELECT 1 FROM analytics_events e WHERE e.user_id=cohort.id
                AND e.occurred_at>=:start AND e.occurred_at<:end
                AND e.event_name = ANY(:qualified))) returned FROM cohort
        """), {"cohort_start": cohort_start, "cohort_end": cohort_end,
                  "start": start, "end": end, "qualified": list(QUALIFIED)})).one()
        retention[f"retention_d{lag}_bp"] = basis_points(int(row.returned), int(row.total))

    ctr_metrics: dict[str, int] = {}
    for strategy in ("cold_start", "cooccurrence", "hot", "latest"):
        impressions = (await db.execute(select(func.count()).select_from(AnalyticsEvent).where(
            AnalyticsEvent.event_name == "post_impression", AnalyticsEvent.source == "client",
            AnalyticsEvent.occurred_at >= start, AnalyticsEvent.occurred_at < end,
            AnalyticsEvent.properties["strategy"].astext == strategy))).scalar_one()
        opens = (await db.execute(select(func.count()).select_from(AnalyticsEvent).where(
            AnalyticsEvent.event_name == "post_open", AnalyticsEvent.source == "client",
            AnalyticsEvent.occurred_at >= start, AnalyticsEvent.occurred_at < end,
            AnalyticsEvent.properties["strategy"].astext == strategy))).scalar_one()
        ctr_metrics[f"recommendation_ctr_{strategy}_bp"] = basis_points(int(opens), int(impressions))

    metrics = {
        "dau": int(dau), "organic_posts": int(organic_posts), "seed_posts": int(seed_posts),
        "search_documents": int(sedimented),
        "ai_helpful_rate_bp": basis_points(len(helpful_ids), helpful_total),
        "high_confidence_helpful_rate_bp": basis_points(high_helpful, len(high_rows)),
        "low_confidence_verified_24h_bp": basis_points(int(low_stats.verified), int(low_stats.total)),
        "human_reply_acceptance_bp": basis_points(int(acceptance_stats.accepted), int(acceptance_stats.total)),
        "organic_content_share_bp": basis_points(int(content_stats.organic), int(content_stats.total)),
        "human_reply_24h_bp": basis_points(int(content_stats.answered), int(content_stats.questions)),
        **retention, **ctr_metrics,
    }
    for name, value in metrics.items():
        dimensions = {"unit": "basis_points"} if name.endswith("_bp") else {"unit": "count"}
        stmt = insert(DailyMetric).values(date=metric_date, metric_name=name, value=value, dimensions=dimensions)
        stmt = stmt.on_conflict_do_update(index_elements=[DailyMetric.date, DailyMetric.metric_name],
                                          set_={"value": value, "dimensions": dimensions,
                                                "calculated_at": func.now()})
        await db.execute(stmt)
    await db.commit()
    return metrics


async def purge_old_events(db: AsyncSession, retention_days: int) -> int:
    cutoff = datetime.now(TZ) - timedelta(days=retention_days)
    result = await db.execute(delete(AnalyticsEvent).where(AnalyticsEvent.occurred_at < cutoff))
    await db.commit()
    return result.rowcount or 0
