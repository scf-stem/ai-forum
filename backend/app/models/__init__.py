"""SQLAlchemy 模型层。

集中声明 declarative Base 与命名约定，供各业务模型继承使用。
Alembic 的 env.py 通过此处导入 Base.metadata 进行迁移生成。
"""
from sqlalchemy import MetaData
from sqlalchemy.orm import DeclarativeBase, declared_attr


# 统一命名约定，便于 Alembic 自动生成稳定的约束名
NAMING_CONVENTION = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}


class Base(DeclarativeBase):
    """所有 ORM 模型的基类。

    自动以类名生成表名（驼峰转下划线），并应用统一命名约定。
    """

    metadata = MetaData(naming_convention=NAMING_CONVENTION)

    @declared_attr.directive
    def __tablename__(cls) -> str:
        """将类名转换为下划线命名作为表名。"""
        import re

        # 驼峰命名转下划线命名：UserBoard -> user_board
        name = re.sub(r"(?<!^)(?=[A-Z])", "_", cls.__name__).lower()
        return name


# 导入所有业务模型，确保 Alembic 能发现它们并注册到 Base.metadata
from app.models.user import User  # noqa: E402, F401
from app.models.board import Board  # noqa: E402, F401
from app.models.post import Post  # noqa: E402, F401
from app.models.reply import Reply  # noqa: E402, F401
from app.models.vote import Vote  # noqa: E402, F401
from app.models.report import Report  # noqa: E402, F401
from app.models.ai_answer import AIAnswer  # noqa: E402, F401
from app.models.community import (  # noqa: E402, F401
    AIAnswerFeedback, Notification, NotificationPreference, ReputationLog,
    SearchDocument, UserBadge,
)
from app.models.growth import (  # noqa: E402, F401
    AIFollowUp, AnalyticsEvent, ContentReward, PointLedger, PostSimilarity,
)
from app.models.ops import (  # noqa: E402, F401
    BackgroundJob, CrawlItem, CrawlSource, DailyMetric, EvaluationCase,
    EvaluationResult, EvaluationReview, EvaluationRun, SeedInvitation,
)

__all__ = [
    "Base",
    "User",
    "Board",
    "Post",
    "Reply",
    "Vote",
    "Report",
    "AIAnswer",
    "ReputationLog", "UserBadge", "SearchDocument", "Notification",
    "NotificationPreference", "AIAnswerFeedback", "PointLedger",
    "ContentReward", "AnalyticsEvent", "PostSimilarity", "AIFollowUp",
    "BackgroundJob", "CrawlSource", "CrawlItem", "SeedInvitation",
    "DailyMetric", "EvaluationCase", "EvaluationRun", "EvaluationResult",
    "EvaluationReview",
]
