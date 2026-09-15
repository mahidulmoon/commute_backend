from sqlalchemy import Column, BigInteger, String, Text, Boolean, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base


class MessageModel(Base):
    __tablename__ = "messages"

    id = Column(BigInteger, primary_key=True, index=True)
    conversation_id = Column(
        BigInteger,
        ForeignKey("conversations.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    sender_id = Column(BigInteger, nullable=False, index=True)
    receiver_id = Column(BigInteger, nullable=False, index=True)

    message_type = Column(String(50), default="text", nullable=False)
    content = Column(Text, nullable=False)

    is_read = Column(Boolean, default=False, nullable=False, index=True)
    read_at = Column(DateTime(timezone=True), nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False, index=True)

    conversation = relationship("ConversationModel", back_populates="messages")
