"""Analytics ingestion and administrator operations APIs."""
import hashlib
import secrets
from datetime import date, datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import get_db
from app.middleware.auth import get_admin_user, get_current_user_optional
from app.models.board import Board
from app.models.growth import AnalyticsEvent, PointLedger
from app.models.community import ReputationLog
from app.models.ops import (BackgroundJob, CrawlItem, CrawlSource, DailyMetric,
                            EvaluationCase, EvaluationResult, EvaluationReview, EvaluationRun,
                            SeedInvitation)
from app.models.post import Post
from app.models.user import User
from app.schemas.platform import (AdminPointAdjustment, CrawlReviewRequest,
    CrawlSourceCreate, EvaluationCaseCreate, EvaluationRunCreate,
    EvaluationScoreRequest, EventBatchRequest, SeedInviteInput)
from app.services.community_service import deactivate_post_index, index_content
from app.services.evaluation_service import summarize_evaluation
from app.services.ai_service import PROMPT_INSTRUCTIONS
from app.services.growth_service import record_event
from app.services.job_service import enqueue_job, retry_job

router = APIRouter()


@router.post("/events/batch", status_code=status.HTTP_202_ACCEPTED)
async def ingest_events(payload: EventBatchRequest, user: User | None = Depends(get_current_user_optional),
                        db: AsyncSession = Depends(get_db)) -> dict:
    event_ids = [item.event_id for item in payload.events]
    existing = set((await db.execute(select(AnalyticsEvent.event_id).where(
        AnalyticsEvent.event_id.in_(event_ids)))).scalars().all())
    accepted = 0
    for item in payload.events:
        event_uuid = item.event_id
        if event_uuid in existing: continue
        properties = {key: value for key, value in item.properties.items()
                      if key in ("position", "strategy", "query_length", "referrer_type")}
        await record_event(db, event_name=item.event_name, event_id=event_uuid,
                           user_id=user.id if user else None, anonymous_id=item.anonymous_id,
                           session_id=item.session_id, post_id=item.post_id, board_id=item.board_id,
                           properties=properties, occurred_at=item.occurred_at, source="client")
        accepted += 1
        existing.add(event_uuid)
    await db.commit()
    return {"accepted": accepted, "duplicates": len(payload.events) - accepted}


@router.get("/ops/metrics")
async def metrics(days: int = Query(30, ge=7, le=90), admin: User = Depends(get_admin_user),
                  db: AsyncSession = Depends(get_db)) -> dict:
    today = date.today()
    cutoff = today - timedelta(days=days - 1)
    previous_cutoff = cutoff - timedelta(days=days)
    all_rows = (await db.execute(select(DailyMetric).where(DailyMetric.date >= previous_cutoff)
                             .order_by(DailyMetric.date, DailyMetric.metric_name))).scalars().all()
    rows = [row for row in all_rows if row.date >= cutoff]
    previous_rows = [row for row in all_rows if row.date < cutoff]
    names = {row.metric_name for row in all_rows}
    comparisons = {}
    for name in names:
        current_values = [row.value for row in rows if row.metric_name == name]
        previous_values = [row.value for row in previous_rows if row.metric_name == name]
        if name.endswith("_bp") or name == "dau":
            current = round(sum(current_values) / len(current_values)) if current_values else 0
            previous = round(sum(previous_values) / len(previous_values)) if previous_values else 0
        elif name == "search_documents":
            current = current_values[-1] if current_values else 0
            previous = previous_values[-1] if previous_values else 0
        else:
            current, previous = sum(current_values), sum(previous_values)
        comparisons[name] = {"current": current, "previous": previous,
            "change_rate": ((current - previous) / previous) if previous else None}
    return {"days": days, "items": rows, "comparisons": comparisons,
            "targets": {"dau_month_6": 3000, "monthly_organic_posts": 10000,
                        "high_confidence_helpful_rate": .60, "low_confidence_verified_24h": .50}}


@router.post("/ops/metrics/rollup")
async def enqueue_metrics(metric_date: date | None = None, admin: User = Depends(get_admin_user),
                          db: AsyncSession = Depends(get_db)) -> dict:
    target = metric_date or date.today() - timedelta(days=1)
    job = await enqueue_job(db, type="rollup_metrics", payload={"date": target.isoformat()},
                            idempotency_key=f"metrics:{target.isoformat()}")
    return {"job_id": str(job.id), "status": job.status}


@router.post("/ops/users/{user_id}/points")
async def adjust_points(user_id: str, payload: AdminPointAdjustment,
                        admin: User = Depends(get_admin_user), db: AsyncSession = Depends(get_db)) -> dict:
    target = (await db.execute(select(User).where(User.id == user_id).with_for_update())).scalar_one_or_none()
    if target is None: raise HTTPException(status_code=404, detail="用户不存在")
    if target.points_balance + payload.delta < 0:
        raise HTTPException(status_code=409, detail="调整后余额不能为负")
    target.points_balance += payload.delta
    db.add(PointLedger(user_id=target.id, delta=payload.delta, balance_after=target.points_balance,
                       reason="admin_adjustment", event_key=f"admin:{admin.id}:{target.id}:{secrets.token_hex(8)}",
                       metadata_json={"admin_id": str(admin.id), "reason": payload.reason}))
    await db.commit()
    return {"user_id": str(target.id), "points_balance": target.points_balance}


@router.get("/ops/reputation/anomalies")
async def reputation_anomalies(days: int = Query(7, ge=1, le=90),
                               admin: User = Depends(get_admin_user),
                               db: AsyncSession = Depends(get_db)) -> dict:
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    rows = (await db.execute(select(
        ReputationLog.user_id, func.date(ReputationLog.created_at).label("date"),
        func.sum(ReputationLog.delta).label("delta")).where(
        ReputationLog.created_at >= cutoff).group_by(
        ReputationLog.user_id, func.date(ReputationLog.created_at)).having(
        func.abs(func.sum(ReputationLog.delta)) >= 100).order_by(
        func.abs(func.sum(ReputationLog.delta)).desc()).limit(100))).mappings().all()
    return {"items": [dict(row) for row in rows], "days": days}


@router.get("/ops/crawl-sources", response_model=None)
async def list_sources(admin: User = Depends(get_admin_user), db: AsyncSession = Depends(get_db)) -> list[CrawlSource]:
    return list((await db.execute(select(CrawlSource).order_by(CrawlSource.created_at.desc()))).scalars().all())


@router.post("/ops/crawl-sources", status_code=201, response_model=None)
async def create_source(payload: CrawlSourceCreate, admin: User = Depends(get_admin_user),
                        db: AsyncSession = Depends(get_db)) -> CrawlSource:
    from urllib.parse import urlparse
    base, entry = urlparse(payload.base_url), urlparse(payload.entry_url)
    terms = urlparse(payload.terms_url)
    if base.scheme != "https" or entry.scheme != "https" or terms.scheme != "https" or base.hostname != entry.hostname:
        raise HTTPException(status_code=400, detail="来源和入口必须是同域 HTTPS 地址")
    if not payload.compliance_confirmed:
        raise HTTPException(status_code=400, detail="必须确认已核对站点条款与转载边界")
    data = payload.model_dump(exclude={"compliance_confirmed"})
    item = CrawlSource(**data, compliance_confirmed_at=datetime.now(timezone.utc), created_by=admin.id)
    db.add(item); await db.commit(); await db.refresh(item); return item


@router.post("/ops/crawl-sources/{source_id}/run")
async def run_source(source_id: str, admin: User = Depends(get_admin_user),
                     db: AsyncSession = Depends(get_db)) -> dict:
    source = (await db.execute(select(CrawlSource).where(CrawlSource.id == source_id, CrawlSource.active.is_(True)))).scalar_one_or_none()
    if source is None: raise HTTPException(status_code=404, detail="来源不存在或已停用")
    job = await enqueue_job(db, type="crawl_source", payload={"source_id": str(source.id)},
                            idempotency_key=f"crawl:{source.id}:{datetime.now(timezone.utc):%Y%m%d%H}")
    return {"job_id": str(job.id), "status": job.status}


@router.delete("/ops/crawl-sources/{source_id}")
async def disable_source(source_id: str, admin: User = Depends(get_admin_user),
                         db: AsyncSession = Depends(get_db)) -> dict:
    source = (await db.execute(select(CrawlSource).where(CrawlSource.id == source_id))).scalar_one_or_none()
    if source is None: raise HTTPException(status_code=404, detail="来源不存在")
    source.active = False
    items = (await db.execute(select(CrawlItem).where(CrawlItem.source_id == source.id))).scalars().all()
    for item in items:
        if item.published_post_id:
            post = (await db.execute(select(Post).where(Post.id == item.published_post_id))).scalar_one_or_none()
            if post: post.status = "archived"; await deactivate_post_index(db, post.id)
    await db.commit(); return {"detail": "来源及其种子帖已停用"}


@router.get("/ops/crawl-items")
async def list_crawl_items(state: str = Query("pending", alias="status"), page: int = Query(1, ge=1),
                           page_size: int = Query(20, ge=1, le=100), admin: User = Depends(get_admin_user),
                           db: AsyncSession = Depends(get_db)) -> dict:
    filters = [CrawlItem.status == state] if state != "all" else []
    total = (await db.execute(select(func.count()).select_from(CrawlItem).where(*filters))).scalar_one()
    items = (await db.execute(select(CrawlItem).where(*filters).order_by(CrawlItem.created_at.desc())
                              .offset((page - 1) * page_size).limit(page_size))).scalars().all()
    return {"items": items, "total": total, "page": page, "page_size": page_size, "has_more": page * page_size < total}


async def _seed_bot(db: AsyncSession) -> User:
    bot = (await db.execute(select(User).where(User.is_system.is_(True), User.username == "seed_bot"))).scalar_one_or_none()
    if bot is None:
        bot = User(email="seed-bot@system.invalid", username="seed_bot", password_hash="!",
                   role="developer", tech_stack=[], is_system=True)
        db.add(bot); await db.flush()
    return bot


@router.patch("/ops/crawl-items/{item_id}/review")
async def review_item(item_id: str, payload: CrawlReviewRequest, admin: User = Depends(get_admin_user),
                      db: AsyncSession = Depends(get_db)) -> dict:
    item = (await db.execute(select(CrawlItem).where(CrawlItem.id == item_id).with_for_update())).scalar_one_or_none()
    if item is None: raise HTTPException(status_code=404, detail="抓取条目不存在")
    if item.status == "published":
        return {"detail": "已发布", "post_id": str(item.published_post_id)}
    if payload.action == "reject":
        item.status = "rejected"; item.rejection_reason = payload.reason or "运营拒绝"
        item.reviewed_at = datetime.now(timezone.utc); await db.commit(); return {"detail": "已拒绝"}
    if not payload.board_id: raise HTTPException(status_code=400, detail="发布时必须选择版块")
    board = (await db.execute(select(Board).where(Board.id == payload.board_id))).scalar_one_or_none()
    if board is None: raise HTTPException(status_code=404, detail="版块不存在")
    bot = await _seed_bot(db); summary = payload.summary or item.summary; tags = payload.tags or item.tags
    post = Post(author_id=bot.id, board_id=board.id, title=item.source_title[:200],
                content=f"{summary}\n\n[阅读原文]({item.canonical_url})", summary=summary[:2000],
                type="share", tags=tags, origin_type="seed_summary", source_url=item.canonical_url,
                source_title=item.source_title, crawl_item_id=item.id)
    post.source_published_at = item.source_published_at
    db.add(post); await db.flush(); board.post_count += 1
    item.status = "published"; item.published_post_id = post.id; item.reviewed_at = datetime.now(timezone.utc)
    await index_content(db, source_type="post", source_id=post.id, post=post, content=post.content, quality_score=0)
    await db.commit(); return {"detail": "已发布", "post_id": str(post.id)}


@router.post("/ops/seed-invitations")
async def create_invitations(items: list[SeedInviteInput], admin: User = Depends(get_admin_user),
                             db: AsyncSession = Depends(get_db)) -> dict:
    if not items or len(items) > 500: raise HTTPException(status_code=400, detail="每次导入 1-500 条邀请")
    links = []
    for payload in items:
        existing = (await db.execute(select(SeedInvitation.id).where(
            func.lower(SeedInvitation.email) == payload.email.lower(),
            SeedInvitation.accepted_at.is_(None),
            SeedInvitation.expires_at > datetime.now(timezone.utc)))).scalar_one_or_none()
        if existing:
            continue
        token = secrets.token_urlsafe(32)
        invitation = SeedInvitation(**payload.model_dump(), token_hash=hashlib.sha256(token.encode()).hexdigest(),
            expires_at=datetime.now(timezone.utc) + timedelta(days=7), created_by=admin.id)
        db.add(invitation)
        links.append({"email": payload.email, "activation_url": f"{settings.PUBLIC_APP_URL}/auth?invite={token}"})
    await db.commit(); return {"items": links}


@router.post("/ops/evaluation-cases", status_code=201, response_model=None)
async def create_case(payload: EvaluationCaseCreate, admin: User = Depends(get_admin_user),
                      db: AsyncSession = Depends(get_db)) -> EvaluationCase:
    item = EvaluationCase(**payload.model_dump(), created_by=admin.id)
    db.add(item); await db.commit(); await db.refresh(item); return item


@router.get("/ops/evaluation-cases", response_model=None)
async def list_cases(version: str = "v1", admin: User = Depends(get_admin_user),
                     db: AsyncSession = Depends(get_db)) -> list[EvaluationCase]:
    return list((await db.execute(select(EvaluationCase).where(EvaluationCase.version == version)
                                  .order_by(EvaluationCase.category, EvaluationCase.id))).scalars().all())


@router.post("/ops/evaluation-runs", status_code=201)
async def create_run(payload: EvaluationRunCreate, admin: User = Depends(get_admin_user),
                     db: AsyncSession = Depends(get_db)) -> dict:
    if payload.prompt_version not in PROMPT_INSTRUCTIONS:
        raise HTTPException(status_code=400, detail="未知 Prompt 版本")
    case_count = (await db.execute(select(func.count()).select_from(EvaluationCase).where(
        EvaluationCase.version == payload.dataset_version,
        EvaluationCase.active.is_(True)))).scalar_one()
    if case_count != 100:
        raise HTTPException(status_code=409, detail=f"金标集必须正好 100 条，当前为 {case_count} 条")
    run = EvaluationRun(prompt_version=payload.prompt_version, model_name=settings.DEEPSEEK_MODEL,
                        dataset_version=payload.dataset_version,
                        baseline_run_id=payload.baseline_run_id, created_by=admin.id)
    db.add(run); await db.flush(); await db.commit(); await db.refresh(run)
    job = await enqueue_job(db, type="evaluation_run", payload={"run_id": str(run.id)}, idempotency_key=f"evaluation:{run.id}")
    return {"run_id": str(run.id), "job_id": str(job.id), "status": run.status}


@router.get("/ops/prompt-versions")
async def prompt_versions(admin: User = Depends(get_admin_user)) -> dict:
    return {"items": list(PROMPT_INSTRUCTIONS)}


@router.get("/ops/evaluation-runs", response_model=None)
async def list_runs(admin: User = Depends(get_admin_user), db: AsyncSession = Depends(get_db)) -> list[EvaluationRun]:
    return list((await db.execute(select(EvaluationRun).order_by(EvaluationRun.created_at.desc()))).scalars().all())


@router.get("/ops/evaluation-runs/{run_id}")
async def get_run(run_id: str, admin: User = Depends(get_admin_user),
                  db: AsyncSession = Depends(get_db)) -> dict:
    run = (await db.execute(select(EvaluationRun).where(EvaluationRun.id == run_id))).scalar_one_or_none()
    if run is None: raise HTTPException(status_code=404, detail="评测任务不存在")
    rows = (await db.execute(select(EvaluationResult, EvaluationCase).join(
        EvaluationCase, EvaluationResult.case_id == EvaluationCase.id).where(
        EvaluationResult.run_id == run.id).order_by(EvaluationCase.category,
        EvaluationCase.id))).all()
    return {"run": run, "results": [{
        "id": str(result.id), "case": case, "answer": result.answer,
        "sources": result.sources, "token_usage": result.token_usage,
        "confidence_level": result.confidence_level, "correctness": result.correctness,
        "completeness": result.completeness, "citation_validity": result.citation_validity,
        "hallucination": result.hallucination,
    } for result, case in rows]}


@router.post("/ops/evaluation-runs/{run_id}/cancel")
async def cancel_run(run_id: str, admin: User = Depends(get_admin_user),
                     db: AsyncSession = Depends(get_db)) -> dict:
    run = (await db.execute(select(EvaluationRun).where(EvaluationRun.id == run_id).with_for_update())).scalar_one_or_none()
    if run is None: raise HTTPException(status_code=404, detail="评测任务不存在")
    if run.status in ("passed", "failed"):
        raise HTTPException(status_code=409, detail="已结束任务不能取消")
    run.status = "cancelled"; await db.commit()
    return {"run_id": str(run.id), "status": run.status}


@router.post("/ops/evaluation-runs/{run_id}/resume")
async def resume_run(run_id: str, admin: User = Depends(get_admin_user),
                     db: AsyncSession = Depends(get_db)) -> dict:
    run = (await db.execute(select(EvaluationRun).where(EvaluationRun.id == run_id).with_for_update())).scalar_one_or_none()
    if run is None: raise HTTPException(status_code=404, detail="评测任务不存在")
    if run.status not in ("cancelled", "failed"):
        raise HTTPException(status_code=409, detail="当前状态不能续跑")
    run.status = "queued"; await db.commit()
    job = await enqueue_job(db, type="evaluation_run", payload={"run_id": str(run.id)},
        idempotency_key=f"evaluation:{run.id}:resume:{secrets.token_hex(8)}")
    return {"run_id": str(run.id), "job_id": str(job.id), "status": run.status}


@router.patch("/ops/evaluation-results/{result_id}/score")
async def score_result(result_id: str, payload: EvaluationScoreRequest, admin: User = Depends(get_admin_user),
                       db: AsyncSession = Depends(get_db)) -> dict:
    result = (await db.execute(select(EvaluationResult).where(EvaluationResult.id == result_id))).scalar_one_or_none()
    if result is None: raise HTTPException(status_code=404, detail="评测结果不存在")
    review = (await db.execute(select(EvaluationReview).where(
        EvaluationReview.result_id == result.id,
        EvaluationReview.reviewer_id == admin.id))).scalar_one_or_none()
    if review is None:
        review = EvaluationReview(result_id=result.id, reviewer_id=admin.id, **payload.model_dump())
        db.add(review)
    else:
        for key, value in payload.model_dump().items(): setattr(review, key, value)
    await db.flush()
    reviews = (await db.execute(select(EvaluationReview).where(
        EvaluationReview.result_id == result.id).order_by(EvaluationReview.created_at))).scalars().all()
    adjudicated = False
    if len(reviews) >= 2:
        fields = ("correctness", "completeness", "citation_validity", "hallucination")
        first_two_agree = all(getattr(reviews[0], field) == getattr(reviews[1], field) for field in fields)
        final_review = reviews[0] if first_two_agree else (reviews[2] if len(reviews) >= 3 else None)
        if final_review:
            for field in fields:
                setattr(result, field, getattr(final_review, field))
            result.reviewed_by = final_review.reviewer_id
            adjudicated = True
    run = (await db.execute(select(EvaluationRun).where(EvaluationRun.id == result.run_id))).scalar_one()
    await db.commit(); summary = await summarize_evaluation(db, run)
    return {"detail": "评分已保存", "review_count": len(reviews),
            "needs_adjudication": len(reviews) >= 2 and not adjudicated,
            "adjudicated": adjudicated, "summary": summary}


@router.get("/ops/jobs", response_model=None)
async def list_jobs(state: str | None = Query(None, alias="status"), admin: User = Depends(get_admin_user),
                    db: AsyncSession = Depends(get_db)) -> list[BackgroundJob]:
    query = select(BackgroundJob)
    if state: query = query.where(BackgroundJob.status == state)
    return list((await db.execute(query.order_by(BackgroundJob.created_at.desc()).limit(100))).scalars().all())


@router.post("/ops/jobs/{job_id}/retry")
async def retry(job_id: str, admin: User = Depends(get_admin_user), db: AsyncSession = Depends(get_db)) -> dict:
    job = (await db.execute(select(BackgroundJob).where(BackgroundJob.id == job_id))).scalar_one_or_none()
    if job is None: raise HTTPException(status_code=404, detail="任务不存在")
    await retry_job(db, job); return {"job_id": str(job.id), "status": job.status}
