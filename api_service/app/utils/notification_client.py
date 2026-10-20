import os
import requests
from typing import Optional, Dict, Any
from app.logger import logger

NOTIFICATION_SERVICE_URL = os.getenv(
    "NOTIFICATION_SERVICE_URL",
    "http://192.168.0.100:8085/api/notifications/send"
)


def send_notification(
    recipient_id: int,
    notif_type: str,
    title: str,
    body: str,
    actor_id: Optional[int] = None,
    link: Optional[str] = None,
    data: Optional[Dict[str, Any]] = None,
) -> bool:
    """
    Fire-and-forget helper to dispatch a notification to notification_service.
    Never raises an exception to avoid impacting core user flows if notification_service is unavailable.
    """
    if recipient_id == actor_id:
        # Don't notify users of their own actions
        return False

    payload = {
        "recipient_id": recipient_id,
        "actor_id": actor_id,
        "type": notif_type,
        "title": title,
        "body": body,
        "link": link,
        "data": data or {},
    }

    try:
        response = requests.post(
            NOTIFICATION_SERVICE_URL,
            json=payload,
            timeout=3.0,
        )
        if response.status_code in [200, 201]:
            logger.info(f"Notification dispatched successfully to user {recipient_id} (type={notif_type})")
            return True
        else:
            logger.warning(f"Notification service returned status {response.status_code}: {response.text}")
            return False
    except Exception as e:
        logger.warning(f"Failed to dispatch notification to user {recipient_id}: {e}")
        return False
