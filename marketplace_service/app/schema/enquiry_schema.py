from datetime import datetime
from decimal import Decimal
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, ConfigDict


class EnquiryCreate(BaseModel):
    service_id: int
    description_of_work: str = Field(..., min_length=10, max_length=5000)
    location: str = Field(..., min_length=2, max_length=255)
    preferred_date_time: Optional[datetime] = None
    photos: Optional[List[str]] = []


class QuoteSubmissionRequest(BaseModel):
    quote_amount: Decimal = Field(..., gt=0)
    quote_currency: Optional[str] = "GBP"
    quote_notes: Optional[str] = None


class EnquiryStatusUpdateRequest(BaseModel):
    status: str = Field(..., description="viewed, accepted, declined, cancelled, completed, disputed")
    notes: Optional[str] = None


class EnquiryMessageCreate(BaseModel):
    content: str = Field(..., min_length=1, max_length=5000)
    attachments: Optional[List[str]] = []


class EnquiryMessageResponse(BaseModel):
    id: int
    enquiry_id: int
    sender_id: int
    sender_role: str
    content: str
    attachments: Optional[List[str]] = None
    is_read: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class EnquiryResponse(BaseModel):
    id: int
    service_id: int
    agency_id: int
    customer_id: int
    description_of_work: str
    location: str
    preferred_date_time: Optional[datetime] = None
    photos: Optional[List[str]] = None
    quote_amount: Optional[float] = None
    quote_currency: str
    quote_notes: Optional[str] = None
    status: str
    created_at: datetime
    updated_at: datetime

    service_title: Optional[str] = None
    agency_name: Optional[str] = None
    messages_count: Optional[int] = 0

    model_config = ConfigDict(from_attributes=True)


class EnquiryListResponse(BaseModel):
    items: List[EnquiryResponse]
    total: int
