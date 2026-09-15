import json
from typing import Dict, Set, List
from fastapi import WebSocket
from app.logger import logger


class ConnectionManager:
    """
    Manages active WebSocket connections for real-time 1-on-1 chat.
    Maintains a mapping of user_id -> set of active WebSockets.
    """

    def __init__(self):
        # Map user_id to set of active WebSockets (supports multi-device/multi-tab per user)
        self.active_connections: Dict[int, Set[WebSocket]] = {}

    async def connect(self, user_id: int, websocket: WebSocket):
        await websocket.accept()
        if user_id not in self.active_connections:
            self.active_connections[user_id] = set()
        self.active_connections[user_id].add(websocket)
        logger.info(f"WebSocket connected: user_id={user_id}. Total connections for user: {len(self.active_connections[user_id])}")

    def disconnect(self, user_id: int, websocket: WebSocket):
        if user_id in self.active_connections:
            self.active_connections[user_id].discard(websocket)
            if not self.active_connections[user_id]:
                del self.active_connections[user_id]
        logger.info(f"WebSocket disconnected: user_id={user_id}.")

    def is_online(self, user_id: int) -> bool:
        return user_id in self.active_connections and len(self.active_connections[user_id]) > 0

    async def send_personal_message(self, user_id: int, message: dict):
        """Send message to all active sockets belonging to user_id."""
        if user_id not in self.active_connections:
            return

        dead_connections = set()
        for connection in list(self.active_connections[user_id]):
            try:
                await connection.send_json(message)
            except Exception as e:
                logger.warning(f"Failed to send to user {user_id} on socket: {e}")
                dead_connections.add(connection)

        # Cleanup any broken connections
        for dead in dead_connections:
            self.disconnect(user_id, dead)

    async def broadcast_to_users(self, user_ids: List[int], message: dict):
        """Send message to multiple users (e.g. both participants in a conversation)."""
        for uid in user_ids:
            await self.send_personal_message(uid, message)


manager = ConnectionManager()
