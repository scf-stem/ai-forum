"""Durable Redis-backed background job orchestration."""
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.ops import BackgroundJob
from app.redis_client import redis_client

QUEUE_KEY = "platform:jobs"


async def enqueue_job(db: AsyncSession, *, type: str, payload: dict,
                      idempotency_key: str) -> BackgroundJob:
    existing = (await db.execute(select(BackgroundJob).where(
        BackgroundJob.idempotency_key == idempotency_key))).scalar_one_or_none()
    if existing:
        return existing
    job = BackgroundJob(type=type, payload=payload, idempotency_key=idempotency_key)
    db.add(job); await db.flush(); await db.commit(); await db.refresh(job)
    await redis_client.rpush(QUEUE_KEY, str(job.id))
    return job


async def retry_job(db: AsyncSession, job: BackgroundJob) -> BackgroundJob:
    if job.status != "failed":
        return job
    job.status = "queued"; job.error = None; job.progress = 0
    job.attempts = 0
    job.finished_at = None
    await db.commit()
    await redis_client.rpush(QUEUE_KEY, str(job.id))
    return job


async def mark_job(db: AsyncSession, job: BackgroundJob, status: str,
                   *, progress: int | None = None, error: str | None = None) -> None:
    was_running = job.status == "running"
    job.status = status
    if progress is not None:
        job.progress = progress
    job.error = error
    if status == "running" and not was_running:
        job.started_at = datetime.now(timezone.utc); job.attempts += 1
    if status in ("completed", "failed"):
        job.finished_at = datetime.now(timezone.utc)
    await db.commit()
