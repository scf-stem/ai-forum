"""帖子路由。

提供全站热帖列表、帖子详情、创建、更新与软删除接口。
"""
import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select, text, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import get_db
from app.middleware.auth import get_current_user, get_current_user_optional
from app.models.ai_answer import AIAnswer
from app.models.board import Board
from app.models.community import AIAnswerFeedback
from app.models.post import Post
from app.models.user import User
from app.models.vote import Vote
from app.routers.boards import _build_post_list_item
from app.schemas.ai_answer import AIAnswerDetail
from app.schemas.post import (
    AuthorBrief,
    PostCreate,
    PostDetail,
    PostUpdate,
)
from app.services.ai_orchestrator import schedule_ai_answer_generation
from app.services.community_service import (deactivate_post_index, index_content,
    refresh_post_index_metadata)
from app.services.growth_service import record_event

router = APIRouter()
logger = logging.getLogger(__name__)


async def _get_post_or_404(post_id: str, db: AsyncSession) -> Post:
    """查询未删除的帖子，不存在则 404。"""
    result = await db.execute(
        select(Post).where(Post.id == post_id, Post.deleted_at.is_(None))
    )
    post = result.scalar_one_or_none()
    if post is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="帖子不存在")
    return post


async def _build_ai_answer_detail(
    ai_answer_id: str | None, db: AsyncSession, current_user: User | None = None,
) -> AIAnswerDetail | None:
    """查询 AI 答案记录并构建详情，不存在或校验失败时返回 None。"""
    if ai_answer_id is None:
        return None
    try:
        result = await db.execute(
            select(AIAnswer).where(AIAnswer.id == ai_answer_id)
        )
        ai_answer = result.scalar_one_or_none()
        if ai_answer is None:
            return None
        counts = dict((await db.execute(select(
            AIAnswerFeedback.value, func.count(AIAnswerFeedback.id)).where(
            AIAnswerFeedback.ai_answer_id == ai_answer.id).group_by(
            AIAnswerFeedback.value))).all())
        my_feedback = None
        if current_user:
            my_feedback = (await db.execute(select(AIAnswerFeedback.value).where(
                AIAnswerFeedback.ai_answer_id == ai_answer.id,
                AIAnswerFeedback.user_id == current_user.id))).scalar_one_or_none()
        return AIAnswerDetail.model_validate(ai_answer).model_copy(update={
            "helpful_count": int(counts.get("helpful", 0)),
            "not_helpful_count": int(counts.get("not_helpful", 0)),
            "my_feedback": my_feedback,
        })
    except Exception:
        logger.exception("构建 AIAnswerDetail 失败 ai_answer_id=%s", ai_answer_id)
        return None


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


@router.get("/similar")
async def similar_posts(
    title: str = Query(..., min_length=10, max_length=200),
    content: str = Query("", max_length=2000),
    tags: str = Query(""),
    exclude_post_id: str | None = None,
    limit: int = Query(5, ge=1, le=10),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Lexical similar-question lookup against the normalized SearchIndex."""
    query_text = " ".join(part for part in (title, content[:500], tags.replace(",", " ")) if part)
    sql = text("""
        SELECT * FROM (
          SELECT DISTINCT ON (sd.post_id) sd.post_id, sd.title, left(sd.content, 240) snippet,
                 sd.tags, sd.quality_score,
                 ts_rank(to_tsvector('simple', coalesce(sd.title,'') || ' ' || coalesce(sd.content,'')),
                         plainto_tsquery('simple', :query)) AS text_rank,
                 (SELECT count(*) FROM jsonb_array_elements_text(sd.tags) tag
                    WHERE lower(tag) = ANY(string_to_array(lower(:tags), ','))) AS tag_overlap
          FROM search_documents sd JOIN posts p ON p.id=sd.post_id
          WHERE sd.is_active=true AND p.deleted_at IS NULL AND NOT p.is_folded
            AND (:exclude_id IS NULL OR sd.post_id::text <> :exclude_id)
            AND (to_tsvector('simple', coalesce(sd.title,'') || ' ' || coalesce(sd.content,''))
                @@ plainto_tsquery('simple', :query)
                OR EXISTS (SELECT 1 FROM jsonb_array_elements_text(sd.tags) tag
                    WHERE lower(tag) = ANY(string_to_array(lower(:tags), ','))))
          ORDER BY sd.post_id, text_rank DESC, tag_overlap DESC, sd.quality_score DESC
        ) ranked
        ORDER BY (text_rank * 0.65 + least(tag_overlap, 3) * 0.20
                  + least(quality_score, 100)::float / 100 * 0.15) DESC
        LIMIT :limit
    """)
    rows = (await db.execute(sql, {"query": query_text, "tags": tags,
        "exclude_id": exclude_post_id, "limit": limit})).mappings().all()
    return {"items": [dict(row) for row in rows]}


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
    if current_user is not None:
        await record_event(db, event_name="post_open", user_id=current_user.id,
                           post_id=post.id, board_id=post.board_id)
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
        author_id=post.author_id,
        board_id=post.board_id,
        title=post.title,
        content=post.content,
        type=post.type,
        tags=post.tags or [],
        status=post.status,
        vote_count=post.vote_count,
        view_count=post.view_count,
        reply_count=post.reply_count,
        is_folded=post.is_folded,
        summary=post.summary,
        accepted_reply_id=post.accepted_reply_id,
        origin_type=post.origin_type,
        source_url=post.source_url,
        source_title=post.source_title,
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
        ai_answer=await _build_ai_answer_detail(post.ai_answer_id, db, current_user),
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
        summary=payload.summary,
        type=payload.type,
        tags=payload.tags,
    )
    db.add(post)
    # 同步更新版块计数
    board.post_count = (board.post_count or 0) + 1
    await db.flush()
    await index_content(db, source_type="post", source_id=post.id, post=post,
                        content=post.content, quality_score=0)
    await record_event(db, event_name="post_created", user_id=user.id, post_id=post.id,
                       board_id=board.id, properties={"type": post.type})
    await db.commit()
    await db.refresh(post)

    # 提问帖：创建 AI 答案记录并异步触发生成
    if post.type == "question":
        ai_answer = AIAnswer(
            post_id=post.id,
            status="generating",
            content="",
            sources=[],
            confidence="medium",
            retrieval_path="hybrid",
            model_name=settings.DEEPSEEK_MODEL,
        )
        db.add(ai_answer)
        await db.flush()  # 获取 server_default 生成的 id
        post.ai_answer_id = ai_answer.id
        await db.commit()
        # onupdate=func.now() 会使 updated_at 在 UPDATE 后失效，
        # 需显式 refresh 避免 PostDetail 构造时触发懒加载（async 懒加载会引发 MissingGreenlet）
        await db.refresh(post)
        # 后台生成 AI 答案，不阻塞帖子发布响应
        schedule_ai_answer_generation(str(post.id), str(ai_answer.id))

    return PostDetail(
        id=str(post.id),
        author_id=post.author_id,
        board_id=post.board_id,
        title=post.title,
        content=post.content,
        type=post.type,
        tags=post.tags or [],
        status=post.status,
        vote_count=post.vote_count,
        view_count=post.view_count,
        reply_count=post.reply_count,
        is_folded=post.is_folded,
        summary=post.summary,
        accepted_reply_id=post.accepted_reply_id,
        origin_type=post.origin_type,
        source_url=post.source_url,
        source_title=post.source_title,
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

    await index_content(db, source_type="post", source_id=post.id, post=post,
                        content=post.content, quality_score=post.vote_count)
    await refresh_post_index_metadata(db, post)

    await db.commit()
    await db.refresh(post)

    # 查询作者与版块用于响应
    author_result = await db.execute(select(User).where(User.id == post.author_id))
    author = author_result.scalar_one()
    board_result = await db.execute(select(Board).where(Board.id == post.board_id))
    board = board_result.scalar_one()

    return PostDetail(
        id=str(post.id),
        author_id=post.author_id,
        board_id=post.board_id,
        title=post.title,
        content=post.content,
        type=post.type,
        tags=post.tags or [],
        status=post.status,
        vote_count=post.vote_count,
        view_count=post.view_count,
        reply_count=post.reply_count,
        is_folded=post.is_folded,
        summary=post.summary,
        accepted_reply_id=post.accepted_reply_id,
        origin_type=post.origin_type,
        source_url=post.source_url,
        source_title=post.source_title,
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
    await deactivate_post_index(db, post.id)

    # 同步递减版块计数
    board_result = await db.execute(select(Board).where(Board.id == post.board_id))
    board = board_result.scalar_one_or_none()
    if board is not None and board.post_count > 0:
        board.post_count -= 1

    await db.commit()
    return {"detail": "帖子已删除"}
