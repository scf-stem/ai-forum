"""回复路由。

提供帖子回复列表、创建回复与软删除回复接口。
"""
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.middleware.auth import get_current_user, get_current_user_optional
from app.models.post import Post
from app.models.reply import Reply
from app.models.user import User
from app.models.vote import Vote
from app.schemas.post import AuthorBrief
from app.schemas.reply import ReplyCreate, ReplyItem

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


async def _build_reply_item(
    reply: Reply,
    author: User,
    my_vote: str | None,
    children: list[ReplyItem] | None = None,
) -> ReplyItem:
    """构造回复项。"""
    return ReplyItem(
        id=str(reply.id),
        post_id=str(reply.post_id),
        parent_id=str(reply.parent_id) if reply.parent_id else None,
        content=reply.content,
        kind=reply.kind,
        vote_count=reply.vote_count,
        is_accepted=reply.is_accepted,
        is_folded=reply.is_folded,
        created_at=reply.created_at,
        updated_at=reply.updated_at,
        author=AuthorBrief(
            id=str(author.id),
            username=author.username,
            avatar=author.avatar,
            role=author.role,
        ),
        children=children or [],
        my_vote=my_vote,
    )


async def _batch_get_my_votes(
    reply_ids: list[str],
    user_id: str,
    db: AsyncSession,
) -> dict[str, str]:
    """批量查询当前用户对多个回复的投票方向。"""
    if not reply_ids:
        return {}
    result = await db.execute(
        select(Vote).where(
            Vote.user_id == user_id,
            Vote.target_type == "reply",
            Vote.target_id.in_(reply_ids),
        )
    )
    return {str(vote.target_id): vote.direction for vote in result.scalars()}


@router.get("/posts/{post_id}/replies")
async def list_post_replies(
    post_id: str,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User | None = Depends(get_current_user_optional),
) -> dict:
    """获取帖子的一级回复列表（按 vote_count DESC），每条含其二级回复。

    未登录可访问；折叠的回复标记 is_folded。
    """
    await _get_post_or_404(post_id, db)

    base_filter = [
        Reply.post_id == post_id,
        Reply.parent_id.is_(None),
        Reply.deleted_at.is_(None),
    ]

    # 一级回复总数
    total = (
        await db.execute(select(func.count()).select_from(Reply).where(*base_filter))
    ).scalar_one()

    # 查询一级回复
    first_level_q = (
        select(Reply, User)
        .join(User, Reply.author_id == User.id)
        .where(*base_filter)
        .order_by(Reply.vote_count.desc(), Reply.created_at.asc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    first_level_rows = (await db.execute(first_level_q)).all()

    if not first_level_rows:
        return {
            "items": [],
            "total": total,
            "page": page,
            "page_size": page_size,
            "has_more": page * page_size < total,
        }

    first_level_replies = [r for r, _ in first_level_rows]
    first_level_ids = [str(r.id) for r in first_level_replies]
    author_map = {str(r.id): u for r, u in first_level_rows}

    # 查询所有二级回复（parent_id IN 一级回复 ID）
    children_q = (
        select(Reply, User)
        .join(User, Reply.author_id == User.id)
        .where(
            Reply.parent_id.in_(first_level_ids),
            Reply.deleted_at.is_(None),
        )
        .order_by(Reply.created_at.asc())
    )
    children_rows = (await db.execute(children_q)).all()

    # 按 parent_id 分组
    children_map: dict[str, list[tuple[Reply, User]]] = {}
    for reply, author in children_rows:
        children_map.setdefault(str(reply.parent_id), []).append((reply, author))

    # 批量查询当前用户对所有回复（一级+二级）的投票
    all_reply_ids = list(first_level_ids)
    for child_list in children_map.values():
        all_reply_ids.extend(str(r.id) for r, _ in child_list)

    my_vote_map: dict[str, str] = {}
    if current_user is not None:
        my_vote_map = await _batch_get_my_votes(all_reply_ids, str(current_user.id), db)

    # 组装回复项
    items: list[ReplyItem] = []
    for reply in first_level_replies:
        author = author_map[str(reply.id)]
        # 构造二级回复列表
        child_items = [
            await _build_reply_item(
                child_reply,
                child_author,
                my_vote_map.get(str(child_reply.id)),
            )
            for child_reply, child_author in children_map.get(str(reply.id), [])
        ]
        item = await _build_reply_item(
            reply,
            author,
            my_vote_map.get(str(reply.id)),
            child_items,
        )
        items.append(item)

    return {
        "items": items,
        "total": total,
        "page": page,
        "page_size": page_size,
        "has_more": page * page_size < total,
    }


@router.post("/posts/{post_id}/replies", response_model=ReplyItem, status_code=status.HTTP_201_CREATED)
async def create_reply(
    post_id: str,
    payload: ReplyCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ReplyItem:
    """创建回复；若指定 parent_id 则校验其合法性。"""
    post = await _get_post_or_404(post_id, db)

    parent_reply: Reply | None = None
    kind = payload.kind

    if payload.parent_id is not None:
        # 校验 parent 回复存在且属于当前帖子
        parent_result = await db.execute(
            select(Reply).where(
                Reply.id == payload.parent_id,
                Reply.deleted_at.is_(None),
            )
        )
        parent_reply = parent_result.scalar_one_or_none()
        if parent_reply is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="父回复不存在"
            )
        if str(parent_reply.post_id) != str(post.id):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="父回复不属于当前帖子",
            )
        if parent_reply.parent_id is not None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="不能回复二级回复",
            )
        # 回复回复时强制设为 discussion
        kind = "discussion"

    # 创建回复
    reply = Reply(
        post_id=post.id,
        parent_id=parent_reply.id if parent_reply else None,
        author_id=user.id,
        content=payload.content,
        kind=kind,
    )
    db.add(reply)
    # 同步更新帖子回复数
    post.reply_count = (post.reply_count or 0) + 1
    await db.commit()
    await db.refresh(reply)

    return await _build_reply_item(reply, user, None)


@router.delete("/replies/{reply_id}", status_code=status.HTTP_200_OK)
async def delete_reply(
    reply_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """软删除回复，仅作者可删除（403 否则），更新帖子 reply_count。"""
    result = await db.execute(
        select(Reply).where(Reply.id == reply_id, Reply.deleted_at.is_(None))
    )
    reply = result.scalar_one_or_none()
    if reply is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="回复不存在")

    if str(reply.author_id) != str(user.id):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="无权删除该回复")

    # 软删除
    reply.deleted_at = datetime.now(timezone.utc)

    # 同步递减帖子回复数
    post_result = await db.execute(select(Post).where(Post.id == reply.post_id))
    post = post_result.scalar_one_or_none()
    if post is not None and post.reply_count > 0:
        post.reply_count -= 1

    await db.commit()
    return {"detail": "回复已删除"}
