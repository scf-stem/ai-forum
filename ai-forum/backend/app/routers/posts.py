"""帖子路由。

提供全站热帖列表、帖子详情、创建、更新与软删除接口。
"""
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.middleware.auth import get_current_user, get_current_user_optional
from app.models.board import Board
from app.models.post import Post
from app.models.user import User
from app.models.vote import Vote
from app.routers.boards import _build_post_list_item
from app.schemas.post import (
    AuthorBrief,
    PostCreate,
    PostDetail,
    PostListItem,
    PostUpdate,
)

router = APIRouter()


async def _get_post_or_404(post_id: str, db: AsyncSession) -> Post:
    """查询未删除的帖子，不存在则 404。"""
    result = await db.execute(
        select(Post).where(Post.id == post_id, Post.deleted_at.is_(None))
    )
    post = result.scalar_one_or_none()
    if post is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="帖子不存在")
    return post


@router.get("", response_model=None)
async def list_hot_posts(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """全站热帖列表（首页用），按投票数与创建时间倒序。"""
    base_filter = [Post.deleted_at.is_(None), Post.status == "published"]

    total = (
        await db.execute(select(func.count()).select_from(Post).where(*base_filter))
    ).scalar_one()

    list_q = (
        select(Post, User, Board)
        .join(User, Post.author_id == User.id)
        .join(Board, Post.board_id == Board.id)
        .where(*base_filter)
        .order_by(Post.vote_count.desc(), Post.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    rows = (await db.execute(list_q)).all()

    items = [_build_post_list_item(post, user, board) for post, user, board in rows]

    return {
        "items": items,
        "total": total,
        "page": page,
        "page_size": page_size,
        "has_more": page * page_size < total,
    }


@router.get("/{post_id}", response_model=PostDetail)
async def get_post_detail(
    post_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User | None = Depends(get_current_user_optional),
) -> PostDetail:
    """帖子详情，未登录可访问；增加 view_count；登录后含 my_vote。"""
    post = await _get_post_or_404(post_id, db)

    # 原子自增浏览数
    await db.execute(
        update(Post).where(Post.id == post.id).values(view_count=Post.view_count + 1)
    )
    await db.commit()
    await db.refresh(post)

    # 查询作者与版块
    author_result = await db.execute(select(User).where(User.id == post.author_id))
    author = author_result.scalar_one()
    board_result = await db.execute(select(Board).where(Board.id == post.board_id))
    board = board_result.scalar_one()

    # 查询当前用户对该帖子的投票方向
    my_vote = None
    if current_user is not None:
        vote_result = await db.execute(
            select(Vote).where(
                Vote.user_id == current_user.id,
                Vote.target_type == "post",
                Vote.target_id == post.id,
            )
        )
        vote = vote_result.scalar_one_or_none()
        if vote is not None:
            my_vote = vote.direction

    return PostDetail(
        id=str(post.id),
        title=post.title,
        content=post.content,
        type=post.type,
        tags=post.tags or [],
        status=post.status,
        vote_count=post.vote_count,
        view_count=post.view_count,
        reply_count=post.reply_count,
        is_folded=post.is_folded,
        created_at=post.created_at,
        updated_at=post.updated_at,
        author=AuthorBrief(
            id=str(author.id),
            username=author.username,
            avatar=author.avatar,
            role=author.role,
        ),
        board={"id": str(board.id), "name": board.name, "tier": board.tier},
        my_vote=my_vote,
    )


@router.post("", response_model=PostDetail, status_code=status.HTTP_201_CREATED)
async def create_post(
    payload: PostCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> PostDetail:
    """创建帖子，校验版块存在并更新版块 post_count。"""
    # 校验版块存在
    board_result = await db.execute(select(Board).where(Board.id == payload.board_id))
    board = board_result.scalar_one_or_none()
    if board is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="版块不存在")

    # 创建帖子
    post = Post(
        author_id=user.id,
        board_id=board.id,
        title=payload.title,
        content=payload.content,
        type=payload.type,
        tags=payload.tags,
    )
    db.add(post)
    # 同步更新版块计数
    board.post_count = (board.post_count or 0) + 1
    await db.commit()
    await db.refresh(post)

    return PostDetail(
        id=str(post.id),
        title=post.title,
        content=post.content,
        type=post.type,
        tags=post.tags or [],
        status=post.status,
        vote_count=post.vote_count,
        view_count=post.view_count,
        reply_count=post.reply_count,
        is_folded=post.is_folded,
        created_at=post.created_at,
        updated_at=post.updated_at,
        author=AuthorBrief(
            id=str(user.id),
            username=user.username,
            avatar=user.avatar,
            role=user.role,
        ),
        board={"id": str(board.id), "name": board.name, "tier": board.tier},
        my_vote=None,
    )


@router.patch("/{post_id}", response_model=PostDetail)
async def update_post(
    post_id: str,
    payload: PostUpdate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> PostDetail:
    """更新帖子，仅作者可编辑（403 否则）。"""
    post = await _get_post_or_404(post_id, db)
    if str(post.author_id) != str(user.id):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="无权编辑该帖子")

    # 仅更新非 None 字段
    update_data = payload.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(post, field, value)

    await db.commit()
    await db.refresh(post)

    # 查询作者与版块用于响应
    author_result = await db.execute(select(User).where(User.id == post.author_id))
    author = author_result.scalar_one()
    board_result = await db.execute(select(Board).where(Board.id == post.board_id))
    board = board_result.scalar_one()

    return PostDetail(
        id=str(post.id),
        title=post.title,
        content=post.content,
        type=post.type,
        tags=post.tags or [],
        status=post.status,
        vote_count=post.vote_count,
        view_count=post.view_count,
        reply_count=post.reply_count,
        is_folded=post.is_folded,
        created_at=post.created_at,
        updated_at=post.updated_at,
        author=AuthorBrief(
            id=str(author.id),
            username=author.username,
            avatar=author.avatar,
            role=author.role,
        ),
        board={"id": str(board.id), "name": board.name, "tier": board.tier},
        my_vote=None,
    )


@router.delete("/{post_id}", status_code=status.HTTP_200_OK)
async def delete_post(
    post_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """软删除帖子，仅作者可删除（403 否则），更新版块 post_count。"""
    post = await _get_post_or_404(post_id, db)
    if str(post.author_id) != str(user.id):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="无权删除该帖子")

    # 软删除
    post.deleted_at = datetime.now(timezone.utc)

    # 同步递减版块计数
    board_result = await db.execute(select(Board).where(Board.id == post.board_id))
    board = board_result.scalar_one_or_none()
    if board is not None and board.post_count > 0:
        board.post_count -= 1

    await db.commit()
    return {"detail": "帖子已删除"}
