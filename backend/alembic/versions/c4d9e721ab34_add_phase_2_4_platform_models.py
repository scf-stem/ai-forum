"""Add Phase 2-4 platform models.

Revision ID: c4d9e721ab34
Revises: 8f2c922fc69e
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "c4d9e721ab34"
down_revision: Union[str, None] = "8f2c922fc69e"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _uuid_pk():
    return sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False)


def upgrade() -> None:
    op.add_column("users", sa.Column("reputation", sa.Integer(), server_default="0", nullable=False))
    op.add_column("users", sa.Column("level", sa.Integer(), server_default="1", nullable=False))
    op.add_column("users", sa.Column("points_balance", sa.Integer(), server_default="100", nullable=False))
    op.add_column("users", sa.Column("is_admin", sa.Boolean(), server_default=sa.false(), nullable=False))
    op.add_column("users", sa.Column("is_system", sa.Boolean(), server_default=sa.false(), nullable=False))
    op.add_column("users", sa.Column("personalization_enabled", sa.Boolean(), server_default=sa.true(), nullable=False))
    op.add_column("posts", sa.Column("summary", sa.Text(), nullable=True))
    op.add_column("posts", sa.Column("origin_type", sa.String(20), server_default="user", nullable=False))
    op.add_column("posts", sa.Column("source_url", sa.String(1000), nullable=True))
    op.add_column("posts", sa.Column("source_title", sa.String(500), nullable=True))
    op.add_column("posts", sa.Column("source_published_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("posts", sa.Column("crawl_item_id", sa.UUID(), nullable=True))
    op.add_column("replies", sa.Column("target_ai_answer_id", sa.UUID(), nullable=True))
    op.create_foreign_key("fk_replies_target_ai_answer_id", "replies", "ai_answers", ["target_ai_answer_id"], ["id"], ondelete="SET NULL")
    op.add_column("ai_answers", sa.Column("corrected_by_reply_id", sa.UUID(), nullable=True))
    op.add_column("ai_answers", sa.Column("prompt_version", sa.String(50), server_default="answer-v1", nullable=False))
    op.create_foreign_key("fk_ai_answers_corrected_by_reply_id", "ai_answers", "replies", ["corrected_by_reply_id"], ["id"], ondelete="SET NULL")
    op.create_foreign_key("fk_posts_accepted_reply_id", "posts", "replies", ["accepted_reply_id"], ["id"], ondelete="SET NULL")

    op.create_table("reputation_logs", _uuid_pk(),
        sa.Column("user_id", sa.UUID(), nullable=False), sa.Column("delta", sa.Integer(), nullable=False),
        sa.Column("reason", sa.String(40), nullable=False), sa.Column("event_key", sa.String(200), nullable=False),
        sa.Column("ref_type", sa.String(30), nullable=False), sa.Column("ref_id", sa.UUID(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]), sa.PrimaryKeyConstraint("id"), sa.UniqueConstraint("event_key"))
    op.create_index("ix_reputation_logs_user_id", "reputation_logs", ["user_id"])
    op.create_table("user_badges", _uuid_pk(), sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("badge_code", sa.String(50), nullable=False), sa.Column("metadata_json", postgresql.JSONB(), server_default="{}", nullable=False),
        sa.Column("awarded_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]), sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "badge_code", name="uq_user_badges_user_code"))
    op.create_index("ix_user_badges_user_id", "user_badges", ["user_id"])
    op.create_table("search_documents", _uuid_pk(), sa.Column("source_type", sa.String(40), nullable=False),
        sa.Column("source_id", sa.UUID(), nullable=False), sa.Column("post_id", sa.UUID(), nullable=False),
        sa.Column("title", sa.String(200), nullable=False), sa.Column("content", sa.Text(), nullable=False),
        sa.Column("tags", postgresql.JSONB(), server_default="[]", nullable=False), sa.Column("quality_score", sa.Integer(), server_default="0", nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default=sa.true(), nullable=False),
        sa.Column("indexed_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["post_id"], ["posts.id"], ondelete="CASCADE"), sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("source_type", "source_id", name="uq_search_documents_source"))
    op.create_index("ix_search_documents_post_id", "search_documents", ["post_id"])
    op.execute("CREATE INDEX ix_search_documents_fts ON search_documents USING gin(to_tsvector('simple', coalesce(title, '') || ' ' || coalesce(content, ''))) WHERE is_active")

    op.create_table("notification_preferences", sa.Column("user_id", sa.UUID(), nullable=False),
        *[sa.Column(f"{name}_enabled", sa.Boolean(), server_default=sa.true(), nullable=False) for name in ("reply", "upvote", "accepted", "reward", "reputation", "system")],
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"), sa.PrimaryKeyConstraint("user_id"))
    op.create_table("notifications", _uuid_pk(), sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("type", sa.String(30), nullable=False), sa.Column("actor_id", sa.UUID(), nullable=True),
        sa.Column("post_id", sa.UUID(), nullable=True), sa.Column("reply_id", sa.UUID(), nullable=True),
        sa.Column("title", sa.String(300), nullable=False), sa.Column("body", sa.String(500), server_default="", nullable=False),
        sa.Column("aggregation_key", sa.String(250), nullable=True), sa.Column("actor_count", sa.Integer(), server_default="1", nullable=False),
        sa.Column("read_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]), sa.ForeignKeyConstraint(["actor_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["post_id"], ["posts.id"], ondelete="CASCADE"), sa.ForeignKeyConstraint(["reply_id"], ["replies.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"), sa.UniqueConstraint("aggregation_key"))
    op.create_index("ix_notifications_user_created", "notifications", ["user_id", "created_at"])
    op.create_table("ai_answer_feedback", _uuid_pk(), sa.Column("ai_answer_id", sa.UUID(), nullable=False),
        sa.Column("user_id", sa.UUID(), nullable=False), sa.Column("value", sa.String(20), nullable=False),
        sa.Column("reason", sa.String(500), nullable=True), sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["ai_answer_id"], ["ai_answers.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"), sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("ai_answer_id", "user_id", name="uq_ai_feedback_answer_user"))

    op.create_table("point_ledger", _uuid_pk(), sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("delta", sa.Integer(), nullable=False), sa.Column("balance_after", sa.Integer(), nullable=False),
        sa.Column("reason", sa.String(40), nullable=False), sa.Column("event_key", sa.String(200), nullable=False),
        sa.Column("ref_id", sa.UUID(), nullable=True), sa.Column("metadata_json", postgresql.JSONB(), server_default="{}", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]), sa.PrimaryKeyConstraint("id"), sa.UniqueConstraint("event_key"))
    op.create_index("ix_point_ledger_user_id", "point_ledger", ["user_id"])
    op.create_table("content_rewards", _uuid_pk(), sa.Column("from_user_id", sa.UUID(), nullable=False),
        sa.Column("to_user_id", sa.UUID(), nullable=False), sa.Column("target_type", sa.String(10), nullable=False),
        sa.Column("target_id", sa.UUID(), nullable=False), sa.Column("post_id", sa.UUID(), nullable=False),
        sa.Column("amount", sa.Integer(), nullable=False), sa.Column("idempotency_key", sa.String(100), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["from_user_id"], ["users.id"]), sa.ForeignKeyConstraint(["to_user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["post_id"], ["posts.id"]), sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("from_user_id", "idempotency_key", name="uq_rewards_sender_idempotency"))
    op.create_index("ix_content_rewards_from_user_id", "content_rewards", ["from_user_id"])
    op.create_index("ix_content_rewards_to_user_id", "content_rewards", ["to_user_id"])
    op.create_table("analytics_events", _uuid_pk(), sa.Column("event_id", sa.UUID(), nullable=False),
        sa.Column("event_name", sa.String(50), nullable=False), sa.Column("user_id", sa.UUID(), nullable=True),
        sa.Column("anonymous_id", sa.String(100), nullable=True), sa.Column("session_id", sa.String(100), nullable=True),
        sa.Column("post_id", sa.UUID(), nullable=True), sa.Column("board_id", sa.UUID(), nullable=True),
        sa.Column("properties", postgresql.JSONB(), server_default="{}", nullable=False), sa.Column("source", sa.String(20), server_default="server", nullable=False),
        sa.Column("occurred_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("ingested_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="SET NULL"), sa.ForeignKeyConstraint(["post_id"], ["posts.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["board_id"], ["boards.id"], ondelete="SET NULL"), sa.PrimaryKeyConstraint("id"), sa.UniqueConstraint("event_id"))
    for column in ("event_name", "user_id", "post_id"):
        op.create_index(f"ix_analytics_events_{column}", "analytics_events", [column])
    op.create_table("post_similarities", sa.Column("post_id", sa.UUID(), nullable=False), sa.Column("similar_post_id", sa.UUID(), nullable=False),
        sa.Column("score", sa.Integer(), server_default="0", nullable=False), sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["post_id"], ["posts.id"], ondelete="CASCADE"), sa.ForeignKeyConstraint(["similar_post_id"], ["posts.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("post_id", "similar_post_id"))
    op.create_table("ai_followups", _uuid_pk(), sa.Column("ai_answer_id", sa.UUID(), nullable=False), sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("question", sa.Text(), nullable=False), sa.Column("answer", sa.Text(), nullable=False), sa.Column("mode", sa.String(20), server_default="normal", nullable=False),
        sa.Column("glossary", postgresql.JSONB(), server_default="[]", nullable=False), sa.Column("prompt_version", sa.String(50), server_default="followup-v1", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["ai_answer_id"], ["ai_answers.id"], ondelete="CASCADE"), sa.ForeignKeyConstraint(["user_id"], ["users.id"]), sa.PrimaryKeyConstraint("id"))
    op.create_index("ix_ai_followups_ai_answer_id", "ai_followups", ["ai_answer_id"])

    op.create_table("background_jobs", _uuid_pk(), sa.Column("type", sa.String(50), nullable=False), sa.Column("payload", postgresql.JSONB(), server_default="{}", nullable=False),
        sa.Column("status", sa.String(20), server_default="queued", nullable=False), sa.Column("attempts", sa.Integer(), server_default="0", nullable=False),
        sa.Column("progress", sa.Integer(), server_default="0", nullable=False), sa.Column("error", sa.Text(), nullable=True),
        sa.Column("idempotency_key", sa.String(200), nullable=False), sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True), sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"), sa.UniqueConstraint("idempotency_key"))
    op.create_index("ix_background_jobs_type", "background_jobs", ["type"]); op.create_index("ix_background_jobs_status", "background_jobs", ["status"])
    op.create_table("crawl_sources", _uuid_pk(), sa.Column("name", sa.String(100), nullable=False), sa.Column("base_url", sa.String(1000), nullable=False),
        sa.Column("entry_url", sa.String(1000), nullable=False), sa.Column("rate_limit_seconds", sa.Integer(), server_default="2", nullable=False),
        sa.Column("max_pages", sa.Integer(), server_default="20", nullable=False), sa.Column("active", sa.Boolean(), server_default=sa.true(), nullable=False),
        sa.Column("terms_url", sa.String(1000), nullable=False), sa.Column("compliance_confirmed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_by", sa.UUID(), nullable=False), sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"]), sa.PrimaryKeyConstraint("id"), sa.UniqueConstraint("base_url"))
    op.create_table("crawl_items", _uuid_pk(), sa.Column("source_id", sa.UUID(), nullable=False), sa.Column("canonical_url", sa.String(1000), nullable=False),
        sa.Column("source_title", sa.String(500), nullable=False), sa.Column("content_hash", sa.String(64), nullable=False), sa.Column("source_published_at", sa.DateTime(timezone=True), nullable=True), sa.Column("summary", sa.Text(), nullable=False),
        sa.Column("tags", postgresql.JSONB(), server_default="[]", nullable=False), sa.Column("status", sa.String(20), server_default="pending", nullable=False),
        sa.Column("rejection_reason", sa.String(500), nullable=True), sa.Column("published_post_id", sa.UUID(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False), sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["source_id"], ["crawl_sources.id"], ondelete="CASCADE"), sa.ForeignKeyConstraint(["published_post_id"], ["posts.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"), sa.UniqueConstraint("canonical_url"), sa.UniqueConstraint("content_hash"))
    op.create_index("ix_crawl_items_source_id", "crawl_items", ["source_id"]); op.create_index("ix_crawl_items_status", "crawl_items", ["status"])
    op.create_foreign_key("fk_posts_crawl_item_id", "posts", "crawl_items", ["crawl_item_id"], ["id"], ondelete="SET NULL")
    op.create_table("seed_invitations", _uuid_pk(), sa.Column("email", sa.String(255), nullable=False), sa.Column("username", sa.String(50), nullable=False),
        sa.Column("role", sa.String(20), nullable=False), sa.Column("tech_stack", postgresql.JSONB(), server_default="[]", nullable=False),
        sa.Column("token_hash", sa.String(64), nullable=False), sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("accepted_at", sa.DateTime(timezone=True), nullable=True), sa.Column("created_by", sa.UUID(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"]), sa.PrimaryKeyConstraint("id"), sa.UniqueConstraint("token_hash"))
    op.create_index("ix_seed_invitations_email", "seed_invitations", ["email"])
    op.create_table("daily_metrics", sa.Column("date", sa.Date(), nullable=False), sa.Column("metric_name", sa.String(60), nullable=False),
        sa.Column("value", sa.Integer(), nullable=False), sa.Column("dimensions", postgresql.JSONB(), server_default="{}", nullable=False),
        sa.Column("calculated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False), sa.PrimaryKeyConstraint("date", "metric_name"))
    op.create_table("evaluation_cases", _uuid_pk(), sa.Column("category", sa.String(40), nullable=False), sa.Column("question", sa.Text(), nullable=False),
        sa.Column("expected_key_points", postgresql.JSONB(), server_default="[]", nullable=False), sa.Column("forbidden_claims", postgresql.JSONB(), server_default="[]", nullable=False),
        sa.Column("expected_sources", postgresql.JSONB(), server_default="[]", nullable=False), sa.Column("difficulty", sa.String(20), nullable=False),
        sa.Column("version", sa.String(30), server_default="v1", nullable=False), sa.Column("active", sa.Boolean(), server_default=sa.true(), nullable=False),
        sa.Column("created_by", sa.UUID(), nullable=False), sa.ForeignKeyConstraint(["created_by"], ["users.id"]), sa.PrimaryKeyConstraint("id"))
    op.create_index("ix_evaluation_cases_category", "evaluation_cases", ["category"])
    op.create_table("evaluation_runs", _uuid_pk(), sa.Column("prompt_version", sa.String(50), nullable=False), sa.Column("model_name", sa.String(100), nullable=False),
        sa.Column("dataset_version", sa.String(30), nullable=False), sa.Column("baseline_run_id", sa.UUID(), nullable=True), sa.Column("status", sa.String(20), server_default="queued", nullable=False),
        sa.Column("summary", postgresql.JSONB(), server_default="{}", nullable=False), sa.Column("created_by", sa.UUID(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False), sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"]), sa.ForeignKeyConstraint(["baseline_run_id"], ["evaluation_runs.id"]), sa.PrimaryKeyConstraint("id"))
    op.create_table("evaluation_results", _uuid_pk(), sa.Column("run_id", sa.UUID(), nullable=False), sa.Column("case_id", sa.UUID(), nullable=False),
        sa.Column("answer", sa.Text(), server_default="", nullable=False), sa.Column("sources", postgresql.JSONB(), server_default="[]", nullable=False),
        sa.Column("token_usage", postgresql.JSONB(), server_default="{}", nullable=False), sa.Column("confidence_level", sa.String(20), server_default="low", nullable=False),
        sa.Column("correctness", sa.Integer(), nullable=True), sa.Column("completeness", sa.Integer(), nullable=True),
        sa.Column("citation_validity", sa.Integer(), nullable=True), sa.Column("hallucination", sa.Boolean(), nullable=True),
        sa.Column("judge_scores", postgresql.JSONB(), server_default="{}", nullable=False), sa.Column("reviewed_by", sa.UUID(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["run_id"], ["evaluation_runs.id"], ondelete="CASCADE"), sa.ForeignKeyConstraint(["case_id"], ["evaluation_cases.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["reviewed_by"], ["users.id"]), sa.PrimaryKeyConstraint("id"), sa.UniqueConstraint("run_id", "case_id", name="uq_evaluation_result_run_case"))
    op.create_table("evaluation_reviews", _uuid_pk(), sa.Column("result_id", sa.UUID(), nullable=False), sa.Column("reviewer_id", sa.UUID(), nullable=False),
        sa.Column("correctness", sa.Integer(), nullable=False), sa.Column("completeness", sa.Integer(), nullable=False), sa.Column("citation_validity", sa.Integer(), nullable=False),
        sa.Column("hallucination", sa.Boolean(), nullable=False), sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["result_id"], ["evaluation_results.id"], ondelete="CASCADE"), sa.ForeignKeyConstraint(["reviewer_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"), sa.UniqueConstraint("result_id", "reviewer_id", name="uq_evaluation_review_result_reviewer"))

    op.execute("INSERT INTO point_ledger (user_id, delta, balance_after, reason, event_key) SELECT id, 100, 100, 'welcome', 'welcome:' || id::text FROM users ON CONFLICT DO NOTHING")
    op.execute("""INSERT INTO reputation_logs (user_id, delta, reason, event_key, ref_type, ref_id)
        SELECT CASE WHEN v.target_type='post' THEN p.author_id ELSE r.author_id END,
               CASE WHEN v.target_type='post' THEN 1 ELSE 2 END, 'content_upvoted', 'backfill:vote:' || v.id::text,
               v.target_type, v.target_id
        FROM votes v LEFT JOIN posts p ON v.target_type='post' AND p.id=v.target_id
        LEFT JOIN replies r ON v.target_type='reply' AND r.id=v.target_id
        WHERE v.direction='up' AND v.user_id <> CASE WHEN v.target_type='post' THEN p.author_id ELSE r.author_id END""")
    op.execute("UPDATE users u SET reputation=s.total FROM (SELECT user_id, sum(delta)::int total FROM reputation_logs GROUP BY user_id) s WHERE u.id=s.user_id")
    op.execute("UPDATE users SET level=CASE WHEN reputation>=20000 THEN 10 WHEN reputation>=10000 THEN 9 WHEN reputation>=6000 THEN 8 WHEN reputation>=3000 THEN 7 WHEN reputation>=1200 THEN 6 WHEN reputation>=600 THEN 5 WHEN reputation>=300 THEN 4 WHEN reputation>=150 THEN 3 WHEN reputation>=50 THEN 2 ELSE 1 END")
    op.execute("INSERT INTO search_documents (source_type, source_id, post_id, title, content, tags, quality_score) SELECT 'post', id, id, title, content, tags, vote_count FROM posts WHERE deleted_at IS NULL AND NOT is_folded ON CONFLICT DO NOTHING")
    op.execute("INSERT INTO search_documents (source_type, source_id, post_id, title, content, tags, quality_score) SELECT 'high_confidence_ai_answer', a.id, a.post_id, p.title, a.content, p.tags, 50 FROM ai_answers a JOIN posts p ON p.id=a.post_id WHERE a.confidence='high' AND a.status IN ('published','verified') ON CONFLICT DO NOTHING")
    op.execute("INSERT INTO search_documents (source_type, source_id, post_id, title, content, tags, quality_score) SELECT 'accepted_reply', r.id, r.post_id, p.title, r.content, p.tags, 100+r.vote_count FROM replies r JOIN posts p ON p.id=r.post_id WHERE r.is_accepted AND r.deleted_at IS NULL ON CONFLICT DO NOTHING")


def downgrade() -> None:
    op.drop_constraint("fk_posts_crawl_item_id", "posts", type_="foreignkey")
    for table in ("evaluation_reviews", "evaluation_results", "evaluation_runs", "evaluation_cases", "daily_metrics", "seed_invitations", "crawl_items", "crawl_sources", "background_jobs", "ai_followups", "post_similarities", "analytics_events", "content_rewards", "point_ledger", "ai_answer_feedback", "notifications", "notification_preferences", "search_documents", "user_badges", "reputation_logs"):
        op.drop_table(table)
    op.drop_constraint("fk_posts_accepted_reply_id", "posts", type_="foreignkey")
    op.drop_constraint("fk_ai_answers_corrected_by_reply_id", "ai_answers", type_="foreignkey")
    op.drop_column("ai_answers", "prompt_version"); op.drop_column("ai_answers", "corrected_by_reply_id")
    op.drop_constraint("fk_replies_target_ai_answer_id", "replies", type_="foreignkey"); op.drop_column("replies", "target_ai_answer_id")
    for column in ("crawl_item_id", "source_published_at", "source_title", "source_url", "origin_type", "summary"):
        op.drop_column("posts", column)
    for column in ("personalization_enabled", "is_system", "is_admin", "points_balance", "level", "reputation"):
        op.drop_column("users", column)
