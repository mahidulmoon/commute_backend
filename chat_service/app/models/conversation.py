from sqlalchemy import Column, BigInteger, DateTime, UniqueConstraint
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base


class ConversationModel(Base):
    __tablename__ = "conversations"

    id = Column(BigInteger, primary_key=True, index=True)

    # In a 1-to-1 conversation, user1_id is always min(user_a, user_b)
    # and user2_id is max(user_a, user_b) to enforce uniqueness.
    user1_id = Column(BigInteger, nullable=False, index=True)
    user2_id = Column(BigInteger, nullable=False, index=True)

    last_message_at = Column(DateTime(timezone=True), nullable=True, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), server_default=func.now(), nullable=False)

    __table_args__ = (
        UniqueConstraint("user1_id", "user2_id", name="uq_conversation_user_pair"),
    )

    messages = relationship(
        "MessageModel",
        back_populates="conversation",
        cascade="all, delete-orphan",
        order_by="MessageModel.created_at.asc()"
    )

    @staticmethod
    def sort_user_ids(uid1: int, uid2: int) -> tuple[int, int]:
        """Normalize pair of user ids so user1_id < user2_id."""
        return (min(uid1, uid2), max(uid1, uid2))
