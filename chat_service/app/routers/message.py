from datetime import datetime
from typing import Optional
from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import desc, func, and_
from app.database import get_db_global
from app.utils.auth_validation import get_current_user
from app.utils.response import success_response, error_response
from app.models.conversation import ConversationModel
from app.models.message import MessageModel
from app.schema.chat import SendMessageRequest
from app.services.connection_manager import manager
from app.logger import logger

router = APIRouter()


@router.get("/conversations/{conversation_id}/messages")
def get_messages(
    conversation_id: int,
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=100),
    before_id: Optional[int] = Query(default=None, description="Fetch messages older than this message ID"),
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db_global),
):
    """
    Fetch message history for a 1-to-1 conversation with pagination.
    Only participants in the conversation are allowed to view messages.
    """
    user_id = current_user.get("id")

    try:
        conv = db.query(ConversationModel).filter(ConversationModel.id == conversation_id).first()
        if not conv:
            return error_response("Conversation not found.", None, 404)

        if conv.user1_id != user_id and conv.user2_id != user_id:
            return error_response("You are not a participant in this conversation.", None, 403)

        query = db.query(MessageModel).filter(MessageModel.conversation_id == conversation_id)
        if before_id:
            query = query.filter(MessageModel.id < before_id)

        messages = (
            query
            .order_by(desc(MessageModel.created_at), desc(MessageModel.id))
            .offset(skip)
            .limit(limit)
            .all()
        )

        total_count = (
            db.query(MessageModel)
            .filter(MessageModel.conversation_id == conversation_id)
            .count()
        )

        # Return messages sorted in chronological order for easier chat display
        items = [
            {
                "id": m.id,
                "conversation_id": m.conversation_id,
                "sender_id": m.sender_id,
                "receiver_id": m.receiver_id,
                "message_type": m.message_type,
                "content": m.content,
                "is_read": m.is_read,
                "read_at": m.read_at.isoformat() if m.read_at else None,
                "created_at": m.created_at.isoformat(),
            }
            for m in reversed(messages)
        ]

        return success_response(
            "Messages retrieved successfully.",
            {
                "items": items,
                "total": total_count,
                "conversation_id": conversation_id,
            },
            200
        )

    except Exception as e:
        logger.error(f"Error fetching messages for conv {conversation_id}: {str(e)}")
        return error_response(str(e), None, 500)


@router.post("/conversations/{conversation_id}/messages")
async def send_message(
    conversation_id: int,
    req: SendMessageRequest,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db_global),
):
    """
    Send a message via REST API.
    Saves message in DB and delivers real-time event via WebSocket to receiver if online.
    """
    user_id = current_user.get("id")

    try:
        conv = db.query(ConversationModel).filter(ConversationModel.id == conversation_id).first()
        if not conv:
            return error_response("Conversation not found.", None, 404)

        if conv.user1_id != user_id and conv.user2_id != user_id:
            return error_response("You are not a participant in this conversation.", None, 403)

        receiver_id = conv.user2_id if conv.user1_id == user_id else conv.user1_id

        msg = MessageModel(
            conversation_id=conversation_id,
            sender_id=user_id,
            receiver_id=receiver_id,
            content=req.content,
            message_type=req.message_type or "text",
        )
        db.add(msg)

        # Update last message timestamp on conversation
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
        }

        # Deliver in real-time via WebSocket to receiver and sender's other devices
        event_payload = {
            "event": "new_message",
            "data": msg_data
        }
        await manager.send_personal_message(receiver_id, event_payload)
        await manager.send_personal_message(user_id, event_payload)

        logger.info(f"Message {msg.id} sent from {user_id} to {receiver_id} in conversation {conversation_id}")
        return success_response("Message sent successfully.", msg_data, 201)

    except Exception as e:
        db.rollback()
        logger.error(f"Error sending message in conv {conversation_id}: {str(e)}")
        return error_response(str(e), None, 500)


@router.put("/conversations/{conversation_id}/read")
async def mark_messages_as_read(
    conversation_id: int,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db_global),
):
    """
    Mark all unread messages sent to the current user in this conversation as read.
    Dispatches WebSocket read receipt to the sender.
    """
    user_id = current_user.get("id")

    try:
        conv = db.query(ConversationModel).filter(ConversationModel.id == conversation_id).first()
        if not conv:
            return error_response("Conversation not found.", None, 404)

        if conv.user1_id != user_id and conv.user2_id != user_id:
            return error_response("You are not a participant in this conversation.", None, 403)

        other_id = conv.user2_id if conv.user1_id == user_id else conv.user1_id

        # Update all unread messages received by current user
        updated_count = (
            db.query(MessageModel)
            .filter(
                MessageModel.conversation_id == conversation_id,
                MessageModel.receiver_id == user_id,
                MessageModel.is_read.is_(False),
            )
            .update(
                {
                    "is_read": True,
                    "read_at": func.now(),
                },
                synchronize_session=False,
            )
        )

        db.commit()

        if updated_count > 0:
            # Notify the sender in real-time that their messages were read
            read_event = {
                "event": "messages_read",
                "data": {
                    "conversation_id": conversation_id,
                    "read_by": user_id,
                    "messages_count": updated_count,
                    "read_at": datetime.utcnow().isoformat(),
                }
            }
            await manager.send_personal_message(other_id, read_event)

        logger.info(f"User {user_id} marked {updated_count} messages as read in conv {conversation_id}")
        return success_response(
            "Messages marked as read.",
            {
                "conversation_id": conversation_id,
                "messages_marked_read": updated_count,
            },
            200
        )

    except Exception as e:
        db.rollback()
        logger.error(f"Error marking messages as read in conv {conversation_id}: {str(e)}")
        return error_response(str(e), None, 500)


@router.get("/unread_count")
def get_total_unread_count(
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db_global),
):
    """
    Get the total count of unread incoming messages across all conversations.
    """
    user_id = current_user.get("id")

    try:
        total_unread = (
            db.query(MessageModel)
            .filter(
                MessageModel.receiver_id == user_id,
                MessageModel.is_read.is_(False),
            )
            .count()
        )

        return success_response("Unread count fetched.", {"total_unread": total_unread}, 200)

    except Exception as e:
        logger.error(f"Error fetching unread count for user {user_id}: {str(e)}")
        return error_response(str(e), None, 500)
