from sqlalchemy import Column, Integer, String, DateTime, Boolean, ForeignKey, Text, Float, JSON, Enum
from sqlalchemy.sql import func
from app.database import Base


class GroupRule(Base):
    __tablename__ = "group_rules"

    id = Column(Integer, primary_key=True)

    group_id = Column(
        Integer,
        ForeignKey("groups.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    field = Column(String(100), nullable=False)

    operator = Column(String(50), nullable=False)

    value = Column(Text, nullable=False)

    is_active = Column(Boolean, default=True, nullable=False)