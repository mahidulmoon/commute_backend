import json
from datetime import datetime
from typing import Optional
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query, status
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.database import SessionLocal
from app.utils.auth_validation import validate_token_string
from app.models.conversation import ConversationModel
from app.models.message import MessageModel
from app.services.connection_manager import manager
from app.logger import logger

router = APIRouter()


@router.websocket("/ws")
async def websocket_chat_endpoint(
    websocket: WebSocket,
    token: Optional[str] = Query(None),
):
    """
    Real-time bidirectional WebSocket connection for 1-to-1 chat.
    Authentication is performed during connection handshake using JWT query token.

    Supported client event types:
      - "send_message": {"action": "send_message", "conversation_id": 1, "content": "Hello", "temp_id": "uuid"}
      - "typing": {"action": "typing", "conversation_id": 1, "is_typing": true}
      - "mark_read": {"action": "mark_read", "conversation_id": 1}
      - "ping": {"action": "ping"}
    """
    if not token:
        logger.warning("WebSocket rejected: missing token query param.")
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    try:
        user_data = validate_token_string(token)
        user_id = user_data["id"]
    except Exception as err:
        logger.warning(f"WebSocket auth failed: {err}")
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    await manager.connect(user_id, websocket)

    # Send initial welcome / connected status
    try:
        await websocket.send_json({
            "event": "connected",
            "data": {
                "user_id": user_id,
                "message": "Connected to chat service WebSocket."
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
                await websocket.send_json({"event": "pong", "timestamp": datetime.utcnow().isoformat()})

            elif action == "send_message":
                conv_id = payload.get("conversation_id")
                content = (payload.get("content") or "").strip()
                msg_type = payload.get("message_type", "text")
                temp_id = payload.get("temp_id")

                if not conv_id or not content:
                    await websocket.send_json({
                        "event": "error",
                        "message": "conversation_id and non-empty content are required.",
                        "temp_id": temp_id
                    })
                    continue

                db: Session = SessionLocal()
                try:
                    conv = db.query(ConversationModel).filter(ConversationModel.id == conv_id).first()
                    if not conv or (conv.user1_id != user_id and conv.user2_id != user_id):
                        await websocket.send_json({
                            "event": "error",
                            "message": "Conversation not found or access denied.",
                            "temp_id": temp_id
                        })
                        continue

                    receiver_id = conv.user2_id if conv.user1_id == user_id else conv.user1_id

                    msg = MessageModel(
                        conversation_id=conv_id,
                        sender_id=user_id,
                        receiver_id=receiver_id,
                        content=content,
                        message_type=msg_type,
                    )
                    db.add(msg)
                    conv.last_message_at = func.now()
                    db.commit()
                    db.refresh(msg)

                    msg_data = {
                        "id": msg.id,
                        "conversation_id": msg.conversation_id,
                        "sender_id": msg.sender_id,
                        "receiver_id": msg.receiver_id,
                        "message_type": msg.message_type,
                        "content": msg.content,
                        "is_read": msg.is_read,
                        "read_at": None,
                        "created_at": msg.created_at.isoformat(),
                        "temp_id": temp_id,
                    }

                    # Acknowledge to sender with generated message ID
                    await websocket.send_json({
                        "event": "message_sent",
                        "data": msg_data,
                        "temp_id": temp_id,
                    })

                    # Dispatch to receiver in real-time
                    await manager.send_personal_message(receiver_id, {
                        "event": "new_message",
                        "data": msg_data
                    })

                except Exception as e:
                    db.rollback()
                    logger.error(f"WebSocket error sending message: {e}")
                    await websocket.send_json({
                        "event": "error",
                        "message": f"Failed to deliver message: {str(e)}",
                        "temp_id": temp_id
                    })
                finally:
                    db.close()

            elif action == "typing":
                conv_id = payload.get("conversation_id")
                is_typing = bool(payload.get("is_typing", True))

                if conv_id:
                    db: Session = SessionLocal()
                    try:
                        conv = db.query(ConversationModel).filter(ConversationModel.id == conv_id).first()
                        if conv and (conv.user1_id == user_id or conv.user2_id == user_id):
                            other_id = conv.user2_id if conv.user1_id == user_id else conv.user1_id
                            await manager.send_personal_message(other_id, {
                                "event": "typing",
                                "data": {
                                    "conversation_id": conv_id,
                                    "user_id": user_id,
                                    "is_typing": is_typing,
                                }
                            })
                    finally:
                        db.close()

            elif action == "mark_read":
                conv_id = payload.get("conversation_id")
                if conv_id:
                    db: Session = SessionLocal()
                    try:
                        conv = db.query(ConversationModel).filter(ConversationModel.id == conv_id).first()
                        if conv and (conv.user1_id == user_id or conv.user2_id == user_id):
                            other_id = conv.user2_id if conv.user1_id == user_id else conv.user1_id

                            updated = (
                                db.query(MessageModel)
                                .filter(
                                    MessageModel.conversation_id == conv_id,
                                    MessageModel.receiver_id == user_id,
                                    MessageModel.is_read.is_(False),
                                )
                                .update(
                                    {"is_read": True, "read_at": func.now()},
                                    synchronize_session=False,
                                )
                            )
                            db.commit()

                            if updated > 0:
                                await manager.send_personal_message(other_id, {
                                    "event": "messages_read",
                                    "data": {
                                        "conversation_id": conv_id,
                                        "read_by": user_id,
                                        "messages_count": updated,
                                        "read_at": datetime.utcnow().isoformat(),
                                    }
                                })
                    except Exception as e:
                        db.rollback()
                        logger.error(f"WebSocket mark_read error: {e}")
                    finally:
                        db.close()

    except WebSocketDisconnect:
        manager.disconnect(user_id, websocket)
        logger.info(f"WebSocket disconnected gracefully for user_id={user_id}")
    except Exception as e:
        manager.disconnect(user_id, websocket)
        logger.error(f"WebSocket unexpected error for user_id={user_id}: {e}")
