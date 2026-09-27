from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field, ConfigDict


class EventCreate(BaseModel):
    title: str = Field(
        ...,
        min_length=1,
        max_length=255,
        description="Title of the event",
    )
    description: Optional[str] = Field(
        default=None,
        max_length=10000,
        description="Detailed description of the event",
    )
    location: Optional[str] = Field(
        default=None,
        max_length=255,
        description="Physical location or link for the event",
    )
    event_date: Optional[datetime] = Field(
        default=None,
        description="Date and time when the event takes place",
    )
    group_id: Optional[int] = Field(
        default=None,
        description="Optional group id associated with this event",
    )


class EventUpdate(BaseModel):
    title: Optional[str] = Field(
        default=None,
        min_length=1,
        max_length=255,
    )
    description: Optional[str] = Field(
        default=None,
        max_length=10000,
    )
    location: Optional[str] = Field(
        default=None,
        max_length=255,
    )
    event_date: Optional[datetime] = None
    group_id: Optional[int] = None


class EventResponse(BaseModel):
    id: int
    user_id: int
    group_id: Optional[int] = None
    title: str
    description: Optional[str] = None
    location: Optional[str] = None
    event_date: Optional[datetime] = None
    is_deleted: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class MyEventsResponse(BaseModel):
    items: List[EventResponse]
    total: int
