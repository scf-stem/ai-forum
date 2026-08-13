"""WebSocket 流式推送端点。

管理 post_id 到 WebSocket 连接集合的映射，支持向指定帖子的所有连接推送消息。
用于 AI 答案生成过程中的流式 token 推送。
"""
import logging
from collections import defaultdict

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

logger = logging.getLogger(__name__)
router = APIRouter()


class ConnectionManager:
    """管理 post_id → WebSocket 连接集合的映射。"""

    def __init__(self):
        self._connections: dict[str, set[WebSocket]] = defaultdict(set)

    async def connect(self, post_id: str, websocket: WebSocket):
        """接受连接并加入对应帖子的连接集合。"""
        await websocket.accept()
        self._connections[post_id].add(websocket)
        logger.info("WebSocket connected for post %s", post_id)

    def disconnect(self, post_id: str, websocket: WebSocket):
        """从连接集合中移除指定连接，集合为空时清理键。"""
        self._connections[post_id].discard(websocket)
        if not self._connections[post_id]:
            del self._connections[post_id]
        logger.info("WebSocket disconnected for post %s", post_id)

    async def send_to_post(self, post_id: str, message: dict):
        """向指定帖子的所有 WebSocket 连接推送消息，自动清理失效连接。"""
        connections = self._connections.get(post_id, set()).copy()
        dead: list[WebSocket] = []
        for ws in connections:
            try:
                await ws.send_json(message)
            except Exception:
                dead.append(ws)
        for ws in dead:
            self._connections[post_id].discard(ws)


# 全局单例
manager = ConnectionManager()


@router.websocket("/ws/ai-answer/{post_id}")
async def ai_answer_ws(websocket: WebSocket, post_id: str):
    """AI 答案流式推送 WebSocket 端点。

    客户端连接后保持长连接，服务端通过 manager.send_to_post 推送 token 与完成事件。
    同时接收客户端消息（如心跳），断开时自动清理连接。
    """
    await manager.connect(post_id, websocket)
    try:
        while True:
            # 保持连接，接收客户端心跳消息
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(post_id, websocket)
