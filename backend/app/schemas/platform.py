"""Phase 2-4 API schemas."""
from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class AcceptReplyRequest(BaseModel):
    reply_id: str | None = None


class AIFeedbackRequest(BaseModel):
    value: Literal["helpful", "not_helpful"]
    reason: str | None = Field(default=None, max_length=500)


class NotificationItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    type: str
    actor_id: str | None = None
    post_id: str | None = None
    reply_id: str | None = None
    title: str
    body: str
    actor_count: int
    read_at: datetime | None = None
    created_at: datetime


class NotificationPreferenceUpdate(BaseModel):
    reply_enabled: bool | None = None
    upvote_enabled: bool | None = None
    accepted_enabled: bool | None = None
    reward_enabled: bool | None = None
    reputation_enabled: bool | None = None
    system_enabled: bool | None = None


class RewardRequest(BaseModel):
    target_type: Literal["post", "reply"]
    target_id: str
    amount: int = Field(ge=1, le=500)


class WritingAssistRequest(BaseModel):
    action: Literal["polish", "format_code", "summarize", "suggest_tags"]
    title: str = Field(default="", max_length=200)
    content: str = Field(min_length=1, max_length=20000)


class FollowUpRequest(BaseModel):
    question: str = Field(min_length=1, max_length=1000)


class EventInput(BaseModel):
    event_id: UUID
    event_name: Literal["session_started", "page_view", "post_impression", "post_open", "search", "similar_post_clicked", "notification_opened"]
    anonymous_id: str | None = Field(default=None, max_length=100)
    session_id: str | None = Field(default=None, max_length=100)
    post_id: UUID | None = None
    board_id: UUID | None = None
    properties: dict = Field(default_factory=dict)
    occurred_at: datetime | None = None


class EventBatchRequest(BaseModel):
    events: list[EventInput] = Field(min_length=1, max_length=50)


class AdminPointAdjustment(BaseModel):
    delta: int = Field(ge=-100000, le=100000)
    reason: str = Field(min_length=3, max_length=200)


class CrawlSourceCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    base_url: str = Field(max_length=1000)
    entry_url: str = Field(max_length=1000)
    rate_limit_seconds: int = Field(default=2, ge=2, le=60)
    max_pages: int = Field(default=20, ge=1, le=200)
    terms_url: str = Field(max_length=1000)
    compliance_confirmed: bool


class CrawlReviewRequest(BaseModel):
    action: Literal["approve", "reject"]
    summary: str | None = Field(default=None, max_length=10000)
    tags: list[str] | None = None
    board_id: str | None = None
    reason: str | None = Field(default=None, max_length=500)


class SeedInviteInput(BaseModel):
    email: str
    username: str = Field(min_length=2, max_length=50)
    role: Literal["developer", "beginner"]
    tech_stack: list[str] = Field(default_factory=list)


class SeedInviteAccept(BaseModel):
    token: str = Field(min_length=20)
    password: str = Field(min_length=8, max_length=128)


class EvaluationCaseCreate(BaseModel):
    category: Literal["rag", "agent", "model_inference", "deployment_tooling", "beginner"]
    question: str = Field(min_length=5)
    expected_key_points: list[str]
    forbidden_claims: list[str] = Field(default_factory=list)
    expected_sources: list[str] = Field(default_factory=list)
    difficulty: Literal["easy", "medium", "hard"]
    version: str = "v1"


class EvaluationRunCreate(BaseModel):
    prompt_version: str = Field(min_length=1, max_length=50)
    dataset_version: str = Field(default="v1", max_length=30)
    baseline_run_id: UUID | None = None


class EvaluationScoreRequest(BaseModel):
    correctness: int = Field(ge=0, le=4)
    completeness: int = Field(ge=0, le=4)
    citation_validity: int = Field(ge=0, le=4)
    hallucination: bool
