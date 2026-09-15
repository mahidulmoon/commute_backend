from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import or_, and_, desc
from app.database import get_db_global
from app.utils.auth_validation import get_current_user
from app.utils.response import success_response, error_response
from app.models.conversation import ConversationModel
from app.models.message import MessageModel
from app.schema.chat import StartConversationRequest
from app.logger import logger

router = APIRouter()


@router.post("/conversations")
def start_or_get_conversation(
    req: StartConversationRequest,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db_global),
):
    """
    Start a new 1-to-1 conversation or return the existing one with target_user_id.
    Ensures user1_id < user2_id so that each pair of users has exactly one conversation row.
    """
    user_id = current_user.get("id")
    target_id = req.target_user_id

    if user_id == target_id:
        return error_response("Cannot create a conversation with yourself.", None, 400)

    try:
        u1, u2 = ConversationModel.sort_user_ids(user_id, target_id)

        conversation = (
            db.query(ConversationModel)
            .filter(
                ConversationModel.user1_id == u1,
                ConversationModel.user2_id == u2,
            )
            .first()
        )

        is_new = False
        if not conversation:
            conversation = ConversationModel(user1_id=u1, user2_id=u2)
            db.add(conversation)
            db.commit()
            db.refresh(conversation)
            is_new = True
            logger.info(f"Created new conversation id={conversation.id} between {user_id} and {target_id}")

        other_user_id = target_id
        last_msg = (
            db.query(MessageModel)
            .filter(MessageModel.conversation_id == conversation.id)
            .order_by(desc(MessageModel.created_at))
            .first()
        )

        unread_count = (
            db.query(MessageModel)
            .filter(
                MessageModel.conversation_id == conversation.id,
                MessageModel.receiver_id == user_id,
                MessageModel.is_read.is_(False),
            )
            .count()
        )

        data = {
            "id": conversation.id,
            "user1_id": conversation.user1_id,
            "user2_id": conversation.user2_id,
            "other_user_id": other_user_id,
            "unread_count": unread_count,
            "last_message": {
                "id": last_msg.id,
                "conversation_id": last_msg.conversation_id,
                "sender_id": last_msg.sender_id,
                "receiver_id": last_msg.receiver_id,
                "message_type": last_msg.message_type,
                "content": last_msg.content,
                "is_read": last_msg.is_read,
                "read_at": last_msg.read_at.isoformat() if last_msg.read_at else None,
                "created_at": last_msg.created_at.isoformat(),
            } if last_msg else None,
            "last_message_at": conversation.last_message_at.isoformat() if conversation.last_message_at else None,
            "created_at": conversation.created_at.isoformat(),
        }

        status_code = 201 if is_new else 200
        msg = "Conversation created successfully." if is_new else "Conversation fetched successfully."
        return success_response(msg, data, status_code)

    except Exception as e:
        db.rollback()
        logger.error(f"Error starting conversation: {str(e)}")
        return error_response(str(e), None, 500)


@router.get("/conversations")
def list_my_conversations(
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=20, ge=1, le=100),
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db_global),
):
    """
    List all 1-to-1 conversations for the authenticated user,
    ordered by most recent message activity.
    """
    user_id = current_user.get("id")

    try:
        conversations = (
            db.query(ConversationModel)
            .filter(
                or_(
                    ConversationModel.user1_id == user_id,
                    ConversationModel.user2_id == user_id,
                )
            )
            .order_by(
                desc(ConversationModel.last_message_at).nulls_last(),
                desc(ConversationModel.created_at),
            )
            .offset(skip)
            .limit(limit)
            .all()
        )

        total_count = (
            db.query(ConversationModel)
            .filter(
                or_(
                    ConversationModel.user1_id == user_id,
                    ConversationModel.user2_id == user_id,
                )
            )
            .count()
        )

        items = []
        for conv in conversations:
            other_id = conv.user2_id if conv.user1_id == user_id else conv.user1_id

            last_msg = (
                db.query(MessageModel)
                .filter(MessageModel.conversation_id == conv.id)
                .order_by(desc(MessageModel.created_at))
                .first()
            )

            unread_cnt = (
                db.query(MessageModel)
                .filter(
                    MessageModel.conversation_id == conv.id,
                    MessageModel.receiver_id == user_id,
                    MessageModel.is_read.is_(False),
                )
                .count()
            )

            items.append({
                "id": conv.id,
                "user1_id": conv.user1_id,
                "user2_id": conv.user2_id,
                "other_user_id": other_id,
                "unread_count": unread_cnt,
                "last_message": {
                    "id": last_msg.id,
                    "conversation_id": last_msg.conversation_id,
                    "sender_id": last_msg.sender_id,
                    "receiver_id": last_msg.receiver_id,
                    "message_type": last_msg.message_type,
                    "content": last_msg.content,
                    "is_read": last_msg.is_read,
                    "read_at": last_msg.read_at.isoformat() if last_msg.read_at else None,
                    "created_at": last_msg.created_at.isoformat(),
                } if last_msg else None,
                "last_message_at": conv.last_message_at.isoformat() if conv.last_message_at else None,
                "created_at": conv.created_at.isoformat(),
            })

        return success_response(
            "Conversations fetched successfully.",
            {"items": items, "total": total_count},
            200
        )

    except Exception as e:
        logger.error(f"Error fetching conversations for user {user_id}: {str(e)}")
        return error_response(str(e), None, 500)
