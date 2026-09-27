from sqlalchemy import (
    Column,
    BigInteger,
    String,
    Text,
    DateTime,
    Boolean,
)
from sqlalchemy.sql import func
from app.database import Base


class EventModel(Base):
    __tablename__ = "events"

    id = Column(BigInteger, primary_key=True, index=True)

    group_id = Column(BigInteger, nullable=True, index=True)

    user_id = Column(
        BigInteger,
        nullable=False,
        index=True,
    )

    title = Column(String(255), nullable=False)

    description = Column(Text, nullable=True)

    location = Column(String(255), nullable=True)

    event_date = Column(DateTime(timezone=True), nullable=True)

    is_deleted = Column(
        Boolean,
        nullable=False,
        default=False,
        index=True,
    )

    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        index=True,
    )

    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )
