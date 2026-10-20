from datetime import datetime
from typing import Optional
from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import desc, func

from app.database import get_db_global
from app.models.notification import NotificationModel
from app.schema.notification_schema import (
    NotificationCreateRequest,
    NotificationResponse,
    NotificationListResponse,
    UnreadCountResponse,
)
from app.services.notification_engine import create_and_dispatch_notification
from app.utils.auth_validation import get_current_user
from app.utils.response import success_response, error_response
from app.logger import logger

router = APIRouter(tags=["Notifications"])


def build_notification_dict(n: NotificationModel) -> dict:
    return {
        "id": n.id,
        "recipient_id": n.recipient_id,
        "actor_id": n.actor_id,
        "type": n.type,
        "title": n.title,
        "body": n.body,
        "link": n.link,
        "data": n.data or {},
        "is_read": n.is_read,
        "read_at": n.read_at.isoformat() if n.read_at else None,
        "created_at": n.created_at.isoformat() if n.created_at else None,
    }



@router.get("/")
def list_my_notifications(
    unread_only: bool = Query(False, description="Filter only unread notifications"),
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db_global),
):
    """
    Get paginated notifications for the authenticated user.
    """
    user_id = current_user.get("id")
    try:
        query = db.query(NotificationModel).filter(
            NotificationModel.recipient_id == user_id,
            NotificationModel.is_deleted.is_(False),
        )

        if unread_only:
            query = query.filter(NotificationModel.is_read.is_(False))

        total = query.count()
        unread_count = db.query(NotificationModel).filter(
            NotificationModel.recipient_id == user_id,
            NotificationModel.is_read.is_(False),
            NotificationModel.is_deleted.is_(False),
        ).count()

        notifications = (
            query.order_by(desc(NotificationModel.created_at))
            .offset(skip)
            .limit(limit)
            .all()
        )

        items = [build_notification_dict(n) for n in notifications]
        return success_response(
            "Notifications fetched successfully.",
            {
                "items": items,
                "total": total,
                "unread_count": unread_count,
            },
            200
        )

    except Exception as e:
        logger.error(f"Error fetching notifications for user {user_id}: {str(e)}")
        return error_response(str(e), None, 500)


@router.get("/unread_count")
def get_unread_count(
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db_global),
):
    """
    Get quick unread notifications badge count for the UI bell icon.
    """
    user_id = current_user.get("id")
    try:
        count = db.query(NotificationModel).filter(
            NotificationModel.recipient_id == user_id,
            NotificationModel.is_read.is_(False),
            NotificationModel.is_deleted.is_(False),
        ).count()

        return success_response("Unread count fetched.", {"unread_count": count}, 200)

    except Exception as e:
        logger.error(f"Error getting unread count for user {user_id}: {str(e)}")
        return error_response(str(e), None, 500)


@router.put("/read_all")
def mark_all_notifications_as_read(
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db_global),
):
    """
    Mark all unread notifications for the current user as read.
    """
    user_id = current_user.get("id")
    try:
        updated = (
            db.query(NotificationModel)
            .filter(
                NotificationModel.recipient_id == user_id,
                NotificationModel.is_read.is_(False),
                NotificationModel.is_deleted.is_(False),
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

        logger.info(f"User {user_id} marked {updated} notifications as read.")
        return success_response("All notifications marked as read.", {"marked_count": updated}, 200)

    except Exception as e:
        db.rollback()
        logger.error(f"Error marking all notifications as read for user {user_id}: {str(e)}")
        return error_response(str(e), None, 500)


@router.put("/{notification_id}/read")
def mark_single_notification_as_read(
    notification_id: int,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db_global),
):
    """
    Mark a specific notification as read.
    """
    user_id = current_user.get("id")
    try:
        notif = db.query(NotificationModel).filter(
            NotificationModel.id == notification_id,
            NotificationModel.recipient_id == user_id,
            NotificationModel.is_deleted.is_(False),
        ).first()

        if not notif:
            return error_response("Notification not found.", None, 404)

        if not notif.is_read:
            notif.is_read = True
            notif.read_at = datetime.utcnow()
            db.commit()

        return success_response("Notification marked as read.", build_notification_dict(notif), 200)

    except Exception as e:
        db.rollback()
        logger.error(f"Error marking notification {notification_id} as read: {str(e)}")
        return error_response(str(e), None, 500)


@router.delete("/{notification_id}")
def dismiss_notification(
    notification_id: int,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db_global),
):
    """
    Soft-delete / dismiss a notification.
    """
    user_id = current_user.get("id")
    try:
        notif = db.query(NotificationModel).filter(
            NotificationModel.id == notification_id,
            NotificationModel.recipient_id == user_id,
        ).first()

        if not notif:
            return error_response("Notification not found.", None, 404)

        notif.is_deleted = True
        db.commit()

        return success_response("Notification dismissed.", {"id": notification_id}, 200)

    except Exception as e:
        db.rollback()
        logger.error(f"Error dismissing notification {notification_id}: {str(e)}")
        return error_response(str(e), None, 500)


@router.post("/send")
async def send_notification(
    req: NotificationCreateRequest,
    db: Session = Depends(get_db_global),
):
    """
    Internal / Service dispatch endpoint.
    Used by api_service, chat_service, and marketplace_service to trigger notifications.
    """
    try:
        notif = await create_and_dispatch_notification(
            db=db,
            recipient_id=req.recipient_id,
            notif_type=req.type,
            title=req.title,
            body=req.body,
            actor_id=req.actor_id,
            link=req.link,
            data=req.data,
        )

        if not notif:
            return success_response("Notification skipped based on recipient preferences.", None, 200)

        return success_response("Notification created and dispatched.", build_notification_dict(notif), 201)

    except Exception as e:
        logger.error(f"Error in send_notification endpoint: {str(e)}")
        return error_response(str(e), None, 500)
