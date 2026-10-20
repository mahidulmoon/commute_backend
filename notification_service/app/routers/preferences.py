from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db_global
from app.models.preference import NotificationPreference
from app.schema.notification_schema import (
    NotificationPreferenceResponse,
    NotificationPreferenceUpdate,
)
from app.utils.auth_validation import get_current_user
from app.utils.response import success_response, error_response
from app.logger import logger

router = APIRouter(prefix="/preferences", tags=["Preferences"])


def get_or_create_preference(db: Session, user_id: int) -> NotificationPreference:
    pref = db.query(NotificationPreference).filter(NotificationPreference.user_id == user_id).first()
    if not pref:
        pref = NotificationPreference(
            user_id=user_id,
            email_notifications=True,
            in_app_notifications=True,
            chat_notifications=True,
            marketplace_notifications=True,
            social_notifications=True,
        )
        db.add(pref)
        db.commit()
        db.refresh(pref)
    return pref



@router.get("/")
def get_my_preferences(
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db_global),
):
    user_id = current_user.get("id")
    try:
        pref = get_or_create_preference(db, user_id)
        data = {
            "user_id": pref.user_id,
            "email_notifications": pref.email_notifications,
            "in_app_notifications": pref.in_app_notifications,
            "chat_notifications": pref.chat_notifications,
            "marketplace_notifications": pref.marketplace_notifications,
            "social_notifications": pref.social_notifications,
        }
        return success_response("Notification preferences fetched.", data, 200)

    except Exception as e:
        logger.error(f"Error fetching preferences for user {user_id}: {str(e)}")
        return error_response(str(e), None, 500)



@router.put("/")
def update_my_preferences(
    req: NotificationPreferenceUpdate,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db_global),
):
    user_id = current_user.get("id")
    try:
        pref = get_or_create_preference(db, user_id)

        if req.email_notifications is not None:
            pref.email_notifications = req.email_notifications
        if req.in_app_notifications is not None:
            pref.in_app_notifications = req.in_app_notifications
        if req.chat_notifications is not None:
            pref.chat_notifications = req.chat_notifications
        if req.marketplace_notifications is not None:
            pref.marketplace_notifications = req.marketplace_notifications
        if req.social_notifications is not None:
            pref.social_notifications = req.social_notifications

        db.commit()
        db.refresh(pref)

        logger.info(f"Notification preferences updated for user {user_id}")
        data = {
            "user_id": pref.user_id,
            "email_notifications": pref.email_notifications,
            "in_app_notifications": pref.in_app_notifications,
            "chat_notifications": pref.chat_notifications,
            "marketplace_notifications": pref.marketplace_notifications,
            "social_notifications": pref.social_notifications,
        }
        return success_response("Notification preferences updated.", data, 200)

    except Exception as e:
        db.rollback()
        logger.error(f"Error updating preferences for user {user_id}: {str(e)}")
        return error_response(str(e), None, 500)
