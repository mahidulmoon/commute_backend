from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field, ConfigDict


class ReviewCreate(BaseModel):
    service_id: int
    enquiry_id: int = Field(..., description="Qualifying enquiry ID confirming interaction (Spec 9.7)")
    rating: int = Field(..., ge=1, le=5)
    review_text: Optional[str] = Field(None, max_length=2000)


class ReviewResponseCreate(BaseModel):
    provider_response: str = Field(..., min_length=2, max_length=2000)


class ReviewResponse(BaseModel):
    id: int
    service_id: int
    agency_id: int
    customer_id: int
    enquiry_id: Optional[int] = None
    rating: int
    review_text: Optional[str] = None
    provider_response: Optional[str] = None
    status: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ReviewListResponse(BaseModel):
    items: List[ReviewResponse]
    total: int
    average_rating: Optional[float] = 0.0
