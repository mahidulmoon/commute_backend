from sqlalchemy import Column, Integer, String, DateTime, Boolean, ForeignKey, Text, Float, JSON, Enum
from sqlalchemy.sql import func
from app.auth_service_db import Base


class Group(Base):
    __tablename__ = "groups"

    id = Column(Integer, primary_key=True)

    name = Column(String(255), nullable=False, unique=True)

    description = Column(Text, nullable=True)

    is_active = Column(Boolean, default=True, nullable=False)

    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(
        DateTime,
        server_default=func.now(),
        onupdate=func.now(),
    )