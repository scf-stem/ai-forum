"""Phase 4 operations, crawling, metrics and evaluation models."""
from datetime import date, datetime

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.models import Base


class BackgroundJob(Base):
    __tablename__ = "background_jobs"
    id: Mapped[str] = mapped_column(UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid())
    type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    payload: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="queued", index=True)
    attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    progress: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    idempotency_key: Mapped[str] = mapped_column(String(200), nullable=False, unique=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class CrawlSource(Base):
    __tablename__ = "crawl_sources"
    id: Mapped[str] = mapped_column(UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid())
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    base_url: Mapped[str] = mapped_column(String(1000), nullable=False, unique=True)
    entry_url: Mapped[str] = mapped_column(String(1000), nullable=False)
    rate_limit_seconds: Mapped[int] = mapped_column(Integer, nullable=False, default=2)
    max_pages: Mapped[int] = mapped_column(Integer, nullable=False, default=20)
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    terms_url: Mapped[str] = mapped_column(String(1000), nullable=False)
    compliance_confirmed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_by: Mapped[str] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())


class CrawlItem(Base):
    __tablename__ = "crawl_items"
    id: Mapped[str] = mapped_column(UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid())
    source_id: Mapped[str] = mapped_column(UUID(as_uuid=True), ForeignKey("crawl_sources.id", ondelete="CASCADE"), nullable=False, index=True)
    canonical_url: Mapped[str] = mapped_column(String(1000), nullable=False, unique=True)
    source_title: Mapped[str] = mapped_column(String(500), nullable=False)
    content_hash: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    source_published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    tags: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending", index=True)
    rejection_reason: Mapped[str | None] = mapped_column(String(500), nullable=True)
    published_post_id: Mapped[str | None] = mapped_column(UUID(as_uuid=True), ForeignKey("posts.id", ondelete="SET NULL"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class SeedInvitation(Base):
    __tablename__ = "seed_invitations"
    id: Mapped[str] = mapped_column(UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid())
    email: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    username: Mapped[str] = mapped_column(String(50), nullable=False)
    role: Mapped[str] = mapped_column(String(20), nullable=False)
    tech_stack: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    token_hash: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    accepted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_by: Mapped[str] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())


class DailyMetric(Base):
    __tablename__ = "daily_metrics"
    date: Mapped[date] = mapped_column(Date, primary_key=True)
    metric_name: Mapped[str] = mapped_column(String(60), primary_key=True)
    value: Mapped[int] = mapped_column(Integer, nullable=False)
    dimensions: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    calculated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())


class EvaluationCase(Base):
    __tablename__ = "evaluation_cases"
    id: Mapped[str] = mapped_column(UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid())
    category: Mapped[str] = mapped_column(String(40), nullable=False, index=True)
    question: Mapped[str] = mapped_column(Text, nullable=False)
    expected_key_points: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    forbidden_claims: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    expected_sources: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    difficulty: Mapped[str] = mapped_column(String(20), nullable=False)
    version: Mapped[str] = mapped_column(String(30), nullable=False, default="v1")
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_by: Mapped[str] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)


class EvaluationRun(Base):
    __tablename__ = "evaluation_runs"
    id: Mapped[str] = mapped_column(UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid())
    prompt_version: Mapped[str] = mapped_column(String(50), nullable=False)
    model_name: Mapped[str] = mapped_column(String(100), nullable=False)
    dataset_version: Mapped[str] = mapped_column(String(30), nullable=False)
    baseline_run_id: Mapped[str | None] = mapped_column(UUID(as_uuid=True), ForeignKey("evaluation_runs.id"), nullable=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="queued")
    summary: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    created_by: Mapped[str] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class EvaluationResult(Base):
    __tablename__ = "evaluation_results"
    id: Mapped[str] = mapped_column(UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid())
    run_id: Mapped[str] = mapped_column(UUID(as_uuid=True), ForeignKey("evaluation_runs.id", ondelete="CASCADE"), nullable=False)
    case_id: Mapped[str] = mapped_column(UUID(as_uuid=True), ForeignKey("evaluation_cases.id", ondelete="CASCADE"), nullable=False)
    answer: Mapped[str] = mapped_column(Text, nullable=False, default="")
    sources: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    token_usage: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    confidence_level: Mapped[str] = mapped_column(String(20), nullable=False, default="low")
    correctness: Mapped[int | None] = mapped_column(Integer, nullable=True)
    completeness: Mapped[int | None] = mapped_column(Integer, nullable=True)
    citation_validity: Mapped[int | None] = mapped_column(Integer, nullable=True)
    hallucination: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    judge_scores: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    reviewed_by: Mapped[str | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    __table_args__ = (UniqueConstraint("run_id", "case_id", name="uq_evaluation_result_run_case"),)


class EvaluationReview(Base):
    __tablename__ = "evaluation_reviews"
    id: Mapped[str] = mapped_column(UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid())
    result_id: Mapped[str] = mapped_column(UUID(as_uuid=True), ForeignKey("evaluation_results.id", ondelete="CASCADE"), nullable=False)
    reviewer_id: Mapped[str] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    correctness: Mapped[int] = mapped_column(Integer, nullable=False)
    completeness: Mapped[int] = mapped_column(Integer, nullable=False)
    citation_validity: Mapped[int] = mapped_column(Integer, nullable=False)
    hallucination: Mapped[bool] = mapped_column(Boolean, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    __table_args__ = (UniqueConstraint("result_id", "reviewer_id", name="uq_evaluation_review_result_reviewer"),)
