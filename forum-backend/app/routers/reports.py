"""举报路由。

提供举报接口，达到阈值后自动折叠目标内容。
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import get_db
from app.middleware.auth import get_current_user
from app.models.post import Post
from app.models.reply import Reply
from app.models.report import Report
from app.models.user import User
from app.schemas.report import ReportCreate

router = APIRouter()


async def _get_target(
    target_type: str, target_id: str, db: AsyncSession
) -> Post | Reply:
    """根据目标类型查询目标实体，并校验未删除。"""
    if target_type == "post":
        result = await db.execute(
            select(Post).where(Post.id == target_id, Post.deleted_at.is_(None))
        )
        target = result.scalar_one_or_none()
    else:
        result = await db.execute(
            select(Reply).where(Reply.id == target_id, Reply.deleted_at.is_(None))
        )
        target = result.scalar_one_or_none()

    if target is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="举报目标不存在")
    return target


@router.post("/reports", status_code=status.HTTP_201_CREATED)
async def create_report(
    payload: ReportCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """举报目标内容，达到阈值后自动折叠。"""
    # 校验目标存在
    target = await _get_target(payload.target_type, payload.target_id, db)

    # 创建举报记录（唯一约束会拦截重复举报）
    report = Report(
        reporter_id=user.id,
        target_type=payload.target_type,
        target_id=payload.target_id,
        reason=payload.reason,
    )
    db.add(report)
    try:
        await db.flush()
    except IntegrityError:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="已举报过该内容"
        )

    # 统计该目标的累计举报数
    count_result = await db.execute(
        select(func.count()).select_from(Report).where(
            Report.target_type == payload.target_type,
            Report.target_id == payload.target_id,
        )
    )
    report_count = count_result.scalar_one()

    # 达到阈值则折叠目标
    folded = False
    if report_count >= settings.REPORT_THRESHOLD and not target.is_folded:
        target.is_folded = True
        folded = True

    await db.commit()

    return {
        "detail": "举报成功",
        "report_count": report_count,
        "is_folded": folded,
    }
