# app/models/job_post.py

import enum

from sqlalchemy import (
    Column,
    Integer,
    Float,
    String,
    Text,
    DateTime,
    ForeignKey,
    Enum,
)
from sqlalchemy.sql import func

from app.database import Base


class JobStatus(str, enum.Enum):
    DRAFT = "draft"
    PUBLISHED = "published"
    CLOSED = "closed"
    ARCHIVED = "archived"


class JobPost(Base):
    __tablename__ = "job_posts"

    id = Column(Integer, primary_key=True, index=True)

    owner_id = Column(
        Integer,
        # ForeignKey("users.id"),
        nullable=False,
        index=True,
    )

    title = Column(String(255), nullable=False)

    description = Column(Text, nullable=False)

    location = Column(String(255), nullable=True)

    latitude = Column(Float, nullable=True)

    longitude = Column(Float, nullable=True)

    employment_type = Column(String(50), nullable=True)

    salary = Column(String(100), nullable=True)

    status = Column(
        Enum(JobStatus, name="job_status"),
        nullable=False,
        default=JobStatus.DRAFT,
        index=True,
    )

    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    published_at = Column(
        DateTime(timezone=True),
        nullable=True,
    )

    closed_at = Column(
        DateTime(timezone=True),
        nullable=True,
    )

    archived_at = Column(
        DateTime(timezone=True),
        nullable=True,
    )