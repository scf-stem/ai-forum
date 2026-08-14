"""Durable in-app notification APIs and authenticated WebSocket."""
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Query, WebSocket, WebSocketDisconnect
from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import AsyncSessionLocal, get_db
from app.middleware.auth import get_current_user
from app.models.community import Notification, NotificationPreference
from app.models.user import User
from app.schemas.platform import NotificationPreferenceUpdate
from app.services.auth_service import decode_token

router = APIRouter()
connections: dict[str, set[WebSocket]] = {}


async def push_notification(item: Notification | None) -> None:
    """Best-effort push after the creating transaction has committed."""
    if item is None:
        return
    payload = {"type": "notification", "notification": {
        "id": str(item.id), "type": item.type, "title": item.title,
        "body": item.body, "post_id": str(item.post_id) if item.post_id else None,
        "reply_id": str(item.reply_id) if item.reply_id else None,
        "actor_count": item.actor_count,
        "created_at": item.created_at.isoformat() if item.created_at else None,
    }}
    for websocket in list(connections.get(str(item.user_id), set())):
        try:
            await websocket.send_json(payload)
        except Exception:
            connections.get(str(item.user_id), set()).discard(websocket)


@router.get("/notifications")
async def list_notifications(type: str | None = None, unread_only: bool = False,
                             page: int = Query(1, ge=1), page_size: int = Query(20, ge=1, le=100),
                             user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)) -> dict:
    filters = [Notification.user_id == user.id]
    if type:
        filters.append(Notification.type == type)
    if unread_only:
        filters.append(Notification.read_at.is_(None))
    total = (await db.execute(select(func.count()).select_from(Notification).where(*filters))).scalar_one()
    items = (await db.execute(select(Notification).where(*filters).order_by(Notification.created_at.desc())
                              .offset((page - 1) * page_size).limit(page_size))).scalars().all()
    return {"items": items, "total": total, "page": page, "page_size": page_size, "has_more": page * page_size < total}


@router.get("/notifications/unread-count")
async def unread_count(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)) -> dict:
    value = (await db.execute(select(func.count()).select_from(Notification).where(
        Notification.user_id == user.id, Notification.read_at.is_(None)))).scalar_one()
    return {"count": value}


@router.patch("/notifications/{notification_id}/read")
async def mark_read(notification_id: str, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)) -> dict:
    await db.execute(update(Notification).where(Notification.id == notification_id, Notification.user_id == user.id)
                     .values(read_at=datetime.now(timezone.utc)))
    await db.commit()
    return {"detail": "已读"}


@router.post("/notifications/read-all")
async def mark_all_read(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)) -> dict:
    await db.execute(update(Notification).where(Notification.user_id == user.id, Notification.read_at.is_(None))
                     .values(read_at=datetime.now(timezone.utc)))
    await db.commit()
    return {"detail": "全部已读"}


@router.get("/notification-preferences", response_model=None)
async def get_preferences(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)) -> NotificationPreference:
    item = (await db.execute(select(NotificationPreference).where(NotificationPreference.user_id == user.id))).scalar_one_or_none()
    if item is None:
        item = NotificationPreference(user_id=user.id)
        db.add(item); await db.commit(); await db.refresh(item)
    return item


@router.patch("/notification-preferences", response_model=None)
async def update_preferences(payload: NotificationPreferenceUpdate, user: User = Depends(get_current_user),
                             db: AsyncSession = Depends(get_db)) -> NotificationPreference:
    item = (await db.execute(select(NotificationPreference).where(NotificationPreference.user_id == user.id))).scalar_one_or_none()
    if item is None:
        item = NotificationPreference(user_id=user.id); db.add(item)
    for key, value in payload.model_dump(exclude_none=True).items():
        setattr(item, key, value)
    await db.commit(); await db.refresh(item)
    return item


@router.websocket("/ws/notifications")
async def notification_ws(websocket: WebSocket, token: str):
    try:
        user_id = decode_token(token).get("sub")
    except Exception:
        await websocket.close(code=1008); return
    async with AsyncSessionLocal() as db:
        user = (await db.execute(select(User).where(User.id == user_id, User.deleted_at.is_(None)))).scalar_one_or_none()
    if user is None:
        await websocket.close(code=1008); return
    await websocket.accept(); connections.setdefault(str(user.id), set()).add(websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        connections.get(str(user.id), set()).discard(websocket)
