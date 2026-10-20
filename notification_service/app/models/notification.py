from sqlalchemy import Column, BigInteger, String, Text, Boolean, JSON, DateTime
from app.models.base import BaseModel


class NotificationModel(BaseModel):
    __tablename__ = "notifications"

    # User who receives the notification
    recipient_id = Column(BigInteger, nullable=False, index=True)

    # User who triggered the notification (optional, null for system notifications)
    actor_id = Column(BigInteger, nullable=True, index=True)

    # Category / Type: post_reaction, post_comment, event_created, chat_message,
    # marketplace_enquiry, marketplace_quote, agency_verified, system_announcement
    type = Column(String(50), nullable=False, index=True)

    title = Column(String(255), nullable=False)
    body = Column(Text, nullable=False)

    # Optional URL or client-side route to navigate on click (e.g. /post/123)
    link = Column(String(255), nullable=True)

    # Metadata payload (e.g. {"post_id": 10, "comment_id": 25})
    data = Column(JSON, default=dict, nullable=True)

    is_read = Column(Boolean, default=False, nullable=False, index=True)
    read_at = Column(DateTime(timezone=True), nullable=True)

    is_deleted = Column(Boolean, default=False, nullable=False, index=True)
