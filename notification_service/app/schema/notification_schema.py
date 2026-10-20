from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, ConfigDict


class NotificationCreateRequest(BaseModel):
    recipient_id: int = Field(..., description="Target user ID to receive the notification")
    actor_id: Optional[int] = Field(None, description="User ID who initiated the event")
    type: str = Field(..., description="Notification category/type")
    title: str = Field(..., min_length=1, max_length=255)
    body: str = Field(..., min_length=1)
    link: Optional[str] = Field(None, max_length=255)
    data: Optional[Dict[str, Any]] = None


class NotificationResponse(BaseModel):
    id: int
    recipient_id: int
    actor_id: Optional[int] = None
    type: str
    title: str
    body: str
    link: Optional[str] = None
    data: Optional[Dict[str, Any]] = None
    is_read: bool
    read_at: Optional[datetime] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class NotificationListResponse(BaseModel):
    items: List[NotificationResponse]
    total: int
    unread_count: int


class UnreadCountResponse(BaseModel):
    unread_count: int


class NotificationPreferenceResponse(BaseModel):
    user_id: int
    email_notifications: bool
    in_app_notifications: bool
    chat_notifications: bool
    marketplace_notifications: bool
    social_notifications: bool

    model_config = ConfigDict(from_attributes=True)


class NotificationPreferenceUpdate(BaseModel):
    email_notifications: Optional[bool] = None
    in_app_notifications: Optional[bool] = None
    chat_notifications: Optional[bool] = None
    marketplace_notifications: Optional[bool] = None
    social_notifications: Optional[bool] = None
