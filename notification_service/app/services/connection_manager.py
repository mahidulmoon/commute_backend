from typing import Dict, Set
from fastapi import WebSocket
from app.logger import logger


class NotificationConnectionManager:
    """
    Manages active WebSocket connections for live real-time notification push.
    Maintains a mapping of user_id -> set of active WebSockets (supports multiple tabs/devices).
    """

    def __init__(self):
        self.active_connections: Dict[int, Set[WebSocket]] = {}

    async def connect(self, user_id: int, websocket: WebSocket):
        await websocket.accept()
        if user_id not in self.active_connections:
            self.active_connections[user_id] = set()
        self.active_connections[user_id].add(websocket)
        logger.info(f"Notification WebSocket connected: user_id={user_id}. Active tabs: {len(self.active_connections[user_id])}")

    def disconnect(self, user_id: int, websocket: WebSocket):
        if user_id in self.active_connections:
            self.active_connections[user_id].discard(websocket)
            if not self.active_connections[user_id]:
                del self.active_connections[user_id]
        logger.info(f"Notification WebSocket disconnected: user_id={user_id}.")

    def is_online(self, user_id: int) -> bool:
        return user_id in self.active_connections and len(self.active_connections[user_id]) > 0

    async def send_personal_notification(self, user_id: int, payload: dict):
        """Send live notification to all active browser tabs/devices of user_id."""
        if user_id not in self.active_connections:
            return

        dead_connections = set()
        for connection in list(self.active_connections[user_id]):
            try:
                await connection.send_json(payload)
            except Exception as e:
                logger.warning(f"Failed to send live notification to user {user_id} on socket: {e}")
                dead_connections.add(connection)

        for dead in dead_connections:
            self.disconnect(user_id, dead)


manager = NotificationConnectionManager()
