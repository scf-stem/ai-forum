"""版块路由。

提供版块列表（按层级分组）、版块详情与版块内帖子列表。
"""
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.board import Board
from app.models.post import Post
from app.models.user import User
from app.schemas.board import BoardItem, BoardListResponse
from app.schemas.post import AuthorBrief, PostListItem

router = APIRouter()


@router.get("", response_model=BoardListResponse)
async def list_boards(db: AsyncSession = Depends(get_db)) -> BoardListResponse:
    """返回版块列表，按 tier 分组。"""
    result = await db.execute(select(Board).order_by(Board.sort_order, Board.created_at))
    boards = result.scalars().all()

    entry = [BoardItem.model_validate(b) for b in boards if b.tier == "entry"]
    deep = [BoardItem.model_validate(b) for b in boards if b.tier == "deep"]
    return BoardListResponse(entry=entry, deep=deep)


@router.get("/{board_id}", response_model=BoardItem)
async def get_board(board_id: str, db: AsyncSession = Depends(get_db)) -> BoardItem:
    """返回版块详情。"""
    result = await db.execute(select(Board).where(Board.id == board_id))
    board = result.scalar_one_or_none()
    if board is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="版块不存在")
    return BoardItem.model_validate(board)


@router.get("/{board_id}/posts")
async def list_board_posts(
    board_id: str,
    sort: str = Query("latest", pattern="^(latest|hot)$"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """返回版块内帖子列表。

    - latest: 按创建时间倒序
    - hot: 按投票数倒序，再按创建时间倒序
    """
    # 校验版块存在并保留实例供后续构造响应使用
    board_result = await db.execute(select(Board).where(Board.id == board_id))
    board = board_result.scalar_one_or_none()
    if board is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="版块不存在")

    base_filter = [
        Post.board_id == board_id,
        Post.deleted_at.is_(None),
        Post.status == "published",
    ]

    # 查询总数
    total = (
        await db.execute(select(func.count()).select_from(Post).where(*base_filter))
    ).scalar_one()

    # 排序规则
    if sort == "hot":
        order = (Post.vote_count.desc(), Post.created_at.desc())
    else:
        order = (Post.created_at.desc(),)

    # 联表查询帖子+作者
    list_q = (
        select(Post, User)
        .join(User, Post.author_id == User.id)
        .where(*base_filter)
        .order_by(*order)
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    rows = (await db.execute(list_q)).all()

    items = [_build_post_list_item(post, user, board) for post, user in rows]

    return {
        "items": items,
        "total": total,
        "page": page,
        "page_size": page_size,
        "has_more": page * page_size < total,
    }


def _build_post_list_item(post: Post, user: User, board: Board) -> PostListItem:
    """构造帖子列表项的通用方法，避免重复代码。"""
    return PostListItem(
        id=str(post.id),
        title=post.title,
        type=post.type,
        tags=post.tags or [],
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
    )
