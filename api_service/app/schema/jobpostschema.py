# app/schemas/job_post.py

from datetime import datetime
from typing import Optional, Any

from pydantic import BaseModel, Field, ConfigDict, model_validator

from app.models.job_post import JobStatus


class JobPostCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=255)
    description: str = Field(..., min_length=1)

    location: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    employment_type: Optional[str] = None
    salary: Optional[str] = None

    status: JobStatus = JobStatus.DRAFT

    @model_validator(mode="before")
    @classmethod
    def handle_lattitude_alias(cls, data: Any) -> Any:
        if isinstance(data, dict):
            if "latitude" not in data and "lattitude" in data:
                data["latitude"] = data["lattitude"]
        return data


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
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    employment_type: Optional[str] = None
    salary: Optional[str] = None

    @model_validator(mode="before")
    @classmethod
    def handle_lattitude_alias(cls, data: Any) -> Any:
        if isinstance(data, dict):
            if "latitude" not in data and "lattitude" in data:
                data["latitude"] = data["lattitude"]
        return data


class JobPostResponse(BaseModel):
    id: int
    owner_id: int

    title: str
    description: str

    location: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    employment_type: Optional[str] = None
    salary: Optional[str] = None

    status: JobStatus

    created_at: datetime
    updated_at: datetime

    published_at: Optional[datetime] = None
    closed_at: Optional[datetime] = None
    archived_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class NearbyJobPostResponse(JobPostResponse):
    distance_km: Optional[float] = None


class NearbyJobsListResponse(BaseModel):
    items: list[NearbyJobPostResponse]
    total: int
    user_location: dict
    search_radius_km: float