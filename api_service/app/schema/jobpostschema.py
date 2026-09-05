# app/schemas/job_post.py

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field, ConfigDict

from app.models.job_post import JobStatus


class JobPostCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=255)
    description: str = Field(..., min_length=1)

    location: Optional[str] = None
    employment_type: Optional[str] = None
    salary: Optional[str] = None

    status: JobStatus = JobStatus.DRAFT


class JobPostUpdate(BaseModel):
    title: Optional[str] = Field(
        None,
        min_length=1,
        max_length=255,
    )

    description: Optional[str] = Field(
        None,
        min_length=1,
    )

    location: Optional[str] = None
    employment_type: Optional[str] = None
    salary: Optional[str] = None


class JobPostResponse(BaseModel):
    id: int
    owner_id: int

    title: str
    description: str

    location: Optional[str]
    employment_type: Optional[str]
    salary: Optional[str]

    status: JobStatus

    created_at: datetime
    updated_at: datetime

    published_at: Optional[datetime]
    closed_at: Optional[datetime]
    archived_at: Optional[datetime]

    model_config = ConfigDict(from_attributes=True)