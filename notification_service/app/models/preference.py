from sqlalchemy import Column, BigInteger, Boolean
from app.models.base import BaseModel


class NotificationPreference(BaseModel):
    __tablename__ = "notification_preferences"

    user_id = Column(BigInteger, unique=True, nullable=False, index=True)

    email_notifications = Column(Boolean, default=True, nullable=False)
    in_app_notifications = Column(Boolean, default=True, nullable=False)
    chat_notifications = Column(Boolean, default=True, nullable=False)
    marketplace_notifications = Column(Boolean, default=True, nullable=False)
    social_notifications = Column(Boolean, default=True, nullable=False)
