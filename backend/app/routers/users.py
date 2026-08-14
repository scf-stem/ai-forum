"""用户接口路由。

提供当前用户信息、资料更新、用户主页与用户发帖/回复列表。
"""
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.middleware.auth import get_current_user
from app.models.board import Board
from app.models.post import Post
from app.models.reply import Reply
from app.models.user import User
from app.models.community import ReputationLog, UserBadge
from app.models.growth import ContentReward
from app.models.vote import Vote
from app.routers.boards import _build_post_list_item
from app.schemas.auth import UserPublic
from app.schemas.post import PostListItem
from app.schemas.user import UserProfile, UserReplyItem, UserUpdate

router = APIRouter()


@router.get("/me", response_model=UserPublic)
async def get_me(user: User = Depends(get_current_user)) -> UserPublic:
    """返回当前登录用户信息。"""
    return UserPublic.from_orm_user(user)


@router.patch("/me", response_model=UserPublic)
async def update_me(
    payload: UserUpdate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> UserPublic:
    """更新当前用户资料（avatar, bio, tech_stack）。"""
    # 仅更新非 None 字段
    update_data = payload.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(user, field, value)

    await db.commit()
    await db.refresh(user)
    return UserPublic.from_orm_user(user)


async def _get_user_by_username(username: str, db: AsyncSession) -> User:
    """根据用户名查询未删除用户，不存在则 404。"""
    result = await db.execute(
        select(User).where(User.username == username, User.deleted_at.is_(None))
    )
    user = result.scalar_one_or_none()
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="用户不存在")
    return user


@router.get("/{username}", response_model=UserProfile)
async def get_user_profile(username: str, db: AsyncSession = Depends(get_db)) -> UserProfile:
    """返回用户公开资料（游客可访问）。"""
    user = await _get_user_by_username(username, db)
    badges = (await db.execute(select(UserBadge).where(UserBadge.user_id == user.id)
                               .order_by(UserBadge.awarded_at.desc()))).scalars().all()
    accepted_count = (await db.execute(select(func.count()).select_from(Reply).where(
        Reply.author_id == user.id, Reply.is_accepted.is_(True)))).scalar_one()
    post_upvotes = (await db.execute(select(func.count()).select_from(Vote).join(
        Post, Vote.target_id == Post.id).where(Vote.target_type == "post",
        Vote.direction == "up", Post.author_id == user.id))).scalar_one()
    reply_upvotes = (await db.execute(select(func.count()).select_from(Vote).join(
        Reply, Vote.target_id == Reply.id).where(Vote.target_type == "reply",
        Vote.direction == "up", Reply.author_id == user.id))).scalar_one()
    return UserProfile(
        id=user.id, username=user.username, avatar=user.avatar, role=user.role,
        tech_stack=user.tech_stack or [], bio=user.bio, created_at=user.created_at,
        last_active_at=user.last_active_at, reputation=user.reputation, level=user.level,
        points_balance=user.points_balance,
        badges=[{"code": item.badge_code, "metadata": item.metadata_json,
                 "awarded_at": item.awarded_at.isoformat()} for item in badges],
        received_upvotes=post_upvotes + reply_upvotes, accepted_count=accepted_count,
    )


@router.get("/me/reputation")
async def my_reputation(page: int = Query(1, ge=1), page_size: int = Query(20, ge=1, le=100),
                        user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)) -> dict:
    total = (await db.execute(select(func.count()).select_from(ReputationLog).where(
        ReputationLog.user_id == user.id))).scalar_one()
    items = (await db.execute(select(ReputationLog).where(ReputationLog.user_id == user.id)
        .order_by(ReputationLog.created_at.desc()).offset((page - 1) * page_size)
        .limit(page_size))).scalars().all()
    return {"items": items, "total": total, "page": page, "page_size": page_size,
            "has_more": page * page_size < total}


@router.get("/me/rewards")
async def my_rewards(direction: str = Query("received", pattern="^(received|sent)$"),
                     page: int = Query(1, ge=1), page_size: int = Query(20, ge=1, le=100),
                     user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)) -> dict:
    field = ContentReward.to_user_id if direction == "received" else ContentReward.from_user_id
    total = (await db.execute(select(func.count()).select_from(ContentReward).where(field == user.id))).scalar_one()
    items = (await db.execute(select(ContentReward).where(field == user.id)
        .order_by(ContentReward.created_at.desc()).offset((page - 1) * page_size)
        .limit(page_size))).scalars().all()
    return {"items": items, "total": total, "direction": direction,
            "page": page, "page_size": page_size, "has_more": page * page_size < total}


@router.get("/{username}/posts")
async def get_user_posts(
    username: str,
    type: str = Query("all", pattern="^(all|question|share)$"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """返回用户帖子列表（游客可访问），含作者与版块信息以兼容前端 PostCard。"""
    user = await _get_user_by_username(username, db)

    # 基础查询：用户已发布且未删除的帖子
    base_filter = [
        Post.author_id == user.id,
        Post.deleted_at.is_(None),
        Post.status == "published",
    ]
    if type != "all":
        base_filter.append(Post.type == type)

    # 查询总数
    count_q = select(func.count()).select_from(Post).where(*base_filter)
    total = (await db.execute(count_q)).scalar_one()

    # 联表查询帖子+版块，复用 boards 路由的构造方法以返回完整 PostListItem
    list_q = (
        select(Post, Board)
        .join(Board, Post.board_id == Board.id)
        .where(*base_filter)
        .order_by(Post.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    rows = (await db.execute(list_q)).all()

    # 复用 _build_post_list_item 构造完整列表项（含 author 与 board）
    items: list[PostListItem] = [
        _build_post_list_item(post, user, board) for post, board in rows
    ]

    return {
        "items": items,
        "total": total,
        "page": page,
        "page_size": page_size,
        "has_more": page * page_size < total,
    }


@router.get("/{username}/replies")
async def get_user_replies(
    username: str,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """返回用户回复列表（游客可访问）。"""
    user = await _get_user_by_username(username, db)

    base_filter = [
        Reply.author_id == user.id,
        Reply.deleted_at.is_(None),
    ]

    # 查询总数
    count_q = select(func.count()).select_from(Reply).where(*base_filter)
    total = (await db.execute(count_q)).scalar_one()

    # 查询回复列表（联表获取帖子标题）
    list_q = (
        select(Reply, Post.title.label("post_title"))
        .join(Post, Reply.post_id == Post.id)
        .where(*base_filter)
        .order_by(Reply.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    rows = (await db.execute(list_q)).all()

    items = [
        UserReplyItem(
            id=str(reply.id),
            content=reply.content,
            kind=reply.kind,
            vote_count=reply.vote_count,
            created_at=reply.created_at,
            post_id=str(reply.post_id),
            post_title=post_title,
        )
        for reply, post_title in rows
    ]

    return {
        "items": items,
        "total": total,
        "page": page,
        "page_size": page_size,
        "has_more": page * page_size < total,
    }
