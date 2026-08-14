"""Standalone durable worker: ``python -m app.worker``."""
import asyncio
import logging
import time
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

from sqlalchemy import select

from app.config import settings
from app.database import AsyncSessionLocal
from app.models.ops import BackgroundJob, CrawlSource, EvaluationRun
from app.redis_client import redis_client
from app.services.badge_service import evaluate_badges
from app.services.crawler_service import crawl_source
from app.services.evaluation_service import execute_evaluation
from app.services.job_service import QUEUE_KEY, enqueue_job, mark_job
from app.services.metrics_service import purge_old_events, rollup_day

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def handle_job(job_id: str) -> None:
    async with AsyncSessionLocal() as db:
        job = (await db.execute(select(BackgroundJob).where(BackgroundJob.id == job_id))).scalar_one_or_none()
        if job is None or job.status != "queued": return
        await mark_job(db, job, "running", progress=1)
        async def progress(value: int):
            await mark_job(db, job, "running", progress=value)
        try:
            if job.type == "crawl_source":
                source = (await db.execute(select(CrawlSource).where(CrawlSource.id == job.payload["source_id"]))).scalar_one()
                count = await crawl_source(db, source, progress); job.payload = {**job.payload, "stored": count}
            elif job.type == "rollup_metrics":
                target = date.fromisoformat(job.payload.get("date")) if job.payload.get("date") else date.today() - timedelta(days=1)
                job.payload = {**job.payload, "metrics": await rollup_day(db, target)}
            elif job.type == "cleanup_events":
                job.payload = {**job.payload, "deleted": await purge_old_events(db, settings.RAW_EVENT_RETENTION_DAYS)}
            elif job.type == "evaluate_badges":
                job.payload = {**job.payload, "awarded": await evaluate_badges(db)}
            elif job.type == "evaluation_run":
                run = (await db.execute(select(EvaluationRun).where(EvaluationRun.id == job.payload["run_id"]))).scalar_one()
                await execute_evaluation(db, run, progress)
            else:
                raise ValueError(f"未知任务类型：{job.type}")
            await mark_job(db, job, "completed", progress=100)
        except Exception as exc:
            logger.exception("job failed id=%s", job_id)
            if job.type == "evaluation_run":
                run = (await db.execute(select(EvaluationRun).where(
                    EvaluationRun.id == job.payload.get("run_id")))).scalar_one_or_none()
                if run:
                    run.status = "failed"
                    run.summary = {**(run.summary or {}), "error": str(exc)[:500]}
                    await db.commit()
            await mark_job(db, job, "failed", error=str(exc))
            if job.attempts < 3:
                job.status = "queued"; await db.commit(); await redis_client.rpush(QUEUE_KEY, job_id)


async def main() -> None:
    logger.info("platform worker started")
    next_schedule = 0.0
    while True:
        if time.monotonic() >= next_schedule:
            shanghai_today = datetime.now(ZoneInfo("Asia/Shanghai")).date()
            async with AsyncSessionLocal() as db:
                target = shanghai_today - timedelta(days=1)
                await enqueue_job(db, type="rollup_metrics", payload={"date": target.isoformat()},
                                  idempotency_key=f"metrics:{target.isoformat()}")
                await enqueue_job(db, type="evaluate_badges", payload={},
                                  idempotency_key=f"badges:{shanghai_today.isoformat()}")
                await enqueue_job(db, type="cleanup_events", payload={},
                                  idempotency_key=f"cleanup:{shanghai_today.isoformat()}")
            next_schedule = time.monotonic() + 3600
        result = await redis_client.blpop(QUEUE_KEY, timeout=5)
        if result:
            await handle_job(result[1])


if __name__ == "__main__":
    asyncio.run(main())
