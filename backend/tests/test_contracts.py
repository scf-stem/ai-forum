from sqlalchemy.orm import configure_mappers

from app.main import app
from app.models import Base
from app.services.community_service import level_for_reputation
from app.evaluation_dataset import dataset_rows


def test_openapi_exposes_phase_2_4_contracts():
    paths = app.openapi()["paths"]
    expected = {
        "/api/posts/{post_id}/accepted-reply",
        "/api/ai-answers/{answer_id}/feedback",
        "/api/notifications",
        "/api/rewards",
        "/api/feed",
        "/api/ai/writing-assist",
        "/api/posts/similar",
        "/api/events/batch",
        "/api/ops/metrics",
        "/api/ops/evaluation-runs",
    }
    assert expected <= set(paths)


def test_all_mappers_configure_and_expected_tables_exist():
    configure_mappers()
    expected = {
        "reputation_logs", "search_documents", "notifications", "point_ledger",
        "content_rewards", "analytics_events", "post_similarities", "crawl_sources",
        "daily_metrics", "evaluation_results", "evaluation_reviews",
    }
    assert expected <= set(Base.metadata.tables)


def test_level_threshold_boundaries():
    assert level_for_reputation(0) == 1
    assert level_for_reputation(49) == 1
    assert level_for_reputation(50) == 2
    assert level_for_reputation(149) == 2
    assert level_for_reputation(150) == 3
    assert level_for_reputation(20_000) == 10


def test_gold_dataset_has_twenty_cases_per_domain():
    rows = dataset_rows()
    assert len(rows) == 100
    assert {category: sum(row["category"] == category for row in rows)
            for category in {row["category"] for row in rows}} == {
        "rag": 20, "agent": 20, "model_inference": 20,
        "deployment_tooling": 20, "beginner": 20,
    }
