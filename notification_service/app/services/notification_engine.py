from typing import Optional, Dict, Any
from sqlalchemy.orm import Session
from app.models.notification import NotificationModel
from app.models.preference import NotificationPreference
from app.services.connection_manager import manager
from app.logger import logger


def is_notification_permitted(db: Session, recipient_id: int, notif_type: str) -> bool:
    """
    Check if the recipient's notification preference permits this category of notification.
    """
    pref = db.query(NotificationPreference).filter(NotificationPreference.user_id == recipient_id).first()
    if not pref:
        return True  # Defaults to enabled

    if not pref.in_app_notifications:
        return False

    social_types = ["post_reaction", "post_comment", "event_created", "social"]
    if notif_type in social_types and not pref.social_notifications:
        return False

    chat_types = ["chat_message", "chat"]
    if notif_type in chat_types and not pref.chat_notifications:
        return False

    marketplace_types = ["marketplace_enquiry", "marketplace_quote", "agency_verified", "marketplace"]
    if notif_type in marketplace_types and not pref.marketplace_notifications:
        return False

    return True


async def create_and_dispatch_notification(
    db: Session,
    recipient_id: int,
    notif_type: str,
    title: str,
    body: str,
    actor_id: Optional[int] = None,
    link: Optional[str] = None,
    data: Optional[Dict[str, Any]] = None,
) -> Optional[NotificationModel]:
    """
    Create a notification in the database, check recipient preferences,
    and push in real-time over WebSocket if the user is currently online.
    """
    try:
        # Check preference
        if not is_notification_permitted(db, recipient_id, notif_type):
            logger.info(f"Notification type '{notif_type}' silenced by user {recipient_id} preferences.")
            return None

        notif = NotificationModel(
            recipient_id=recipient_id,
            actor_id=actor_id,
            type=notif_type,
            title=title,
            body=body,
            link=link,
            data=data or {},
            is_read=False,
            is_deleted=False,
        )
        db.add(notif)
        db.commit()
        db.refresh(notif)

        notif_dict = {
            "id": notif.id,
            "recipient_id": notif.recipient_id,
            "actor_id": notif.actor_id,
            "type": notif.type,
            "title": notif.title,
            "body": notif.body,
            "link": notif.link,
            "data": notif.data,
            "is_read": notif.is_read,
            "read_at": None,
            "created_at": notif.created_at.isoformat(),
        }

        # Deliver real-time update via WebSocket
        await manager.send_personal_notification(
            user_id=recipient_id,
            payload={
                "event": "new_notification",
                "data": notif_dict,
            }
        )

        logger.info(f"Notification {notif.id} created & dispatched for user {recipient_id} (type={notif_type})")
        return notif

    except Exception as e:
        db.rollback()
        logger.error(f"Error creating notification for user {recipient_id}: {str(e)}")
        raise
