import json
from datetime import datetime
from typing import Optional
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query, status

from app.utils.auth_validation import validate_token_string
from app.services.connection_manager import manager
from app.logger import logger

router = APIRouter(tags=["WebSocket"])


@router.websocket("/ws")
async def notification_websocket_endpoint(
    websocket: WebSocket,
    token: Optional[str] = Query(None),
):
    """
    Real-time WebSocket endpoint for instant live notification push.
    Frontend connects e.g. ws://localhost:8085/api/notifications/ws?token=<jwt_token>
    """
    if not token:
        logger.warning("Notification WebSocket rejected: missing token query param.")
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    try:
        user_data = validate_token_string(token)
        user_id = user_data["id"]
    except Exception as err:
        logger.warning(f"Notification WebSocket auth failed: {err}")
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    await manager.connect(user_id, websocket)

    try:
        await websocket.send_json({
            "event": "connected",
            "data": {
                "user_id": user_id,
                "message": "Connected to Notification Service WebSocket.",
                "timestamp": datetime.utcnow().isoformat(),
            }
        })
    except Exception as e:
        logger.warning(f"Failed to send connected event: {e}")

    try:
        while True:
            raw_data = await websocket.receive_text()
            try:
                payload = json.loads(raw_data)
            except Exception:
                await websocket.send_json({"event": "error", "message": "Invalid JSON format."})
                continue

            action = payload.get("action")
            if action == "ping":
                await websocket.send_json({
                    "event": "pong",
                    "timestamp": datetime.utcnow().isoformat(),
                })

    except WebSocketDisconnect:
        manager.disconnect(user_id, websocket)
        logger.info(f"Notification WebSocket disconnected for user_id={user_id}")
    except Exception as e:
        manager.disconnect(user_id, websocket)
        logger.error(f"Notification WebSocket unexpected error for user_id={user_id}: {e}")
