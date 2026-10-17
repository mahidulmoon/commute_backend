from datetime import datetime
from decimal import Decimal
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, ConfigDict


class AdditionalFeesSchema(BaseModel):
    call_out_fee: Optional[float] = None
    travel_fee: Optional[float] = None
    emergency_surcharge: Optional[float] = None
    materials_included: Optional[bool] = False
    materials_note: Optional[str] = None
    minimum_charge: Optional[float] = None
    add_ons: Optional[List[Dict[str, Any]]] = []


class ListingCreate(BaseModel):
    category_id: int
    title: str = Field(..., min_length=3, max_length=255)
    summary: str = Field(..., min_length=10, max_length=500)
    full_description: str = Field(..., min_length=20)
    service_style: str = Field(..., description="on-site, mobile, remote, emergency, scheduled, other")
    included_work: Optional[str] = None
    exclusions: Optional[str] = None
    images: Optional[List[str]] = []
    
    pricing_model: str = Field(..., description="fixed, from-price, hourly, daily, per-unit, package, quote_required")
    price: Optional[Decimal] = Field(None, ge=0)
    currency: Optional[str] = "GBP"
    unit: Optional[str] = None
    additional_fees: Optional[AdditionalFeesSchema] = None

    estimated_duration: Optional[str] = None
    availability: Optional[Dict[str, Any]] = None
    service_area: Optional[Dict[str, Any]] = None
    qualifications_required: Optional[str] = None
    cancellation_terms: Optional[str] = None
    publish_now: Optional[bool] = False


class ListingUpdate(BaseModel):
    category_id: Optional[int] = None
    title: Optional[str] = Field(None, min_length=3, max_length=255)
    summary: Optional[str] = Field(None, min_length=10, max_length=500)
    full_description: Optional[str] = None
    service_style: Optional[str] = None
    included_work: Optional[str] = None
    exclusions: Optional[str] = None
    images: Optional[List[str]] = None
    
    pricing_model: Optional[str] = None
    price: Optional[Decimal] = Field(None, ge=0)
    currency: Optional[str] = None
    unit: Optional[str] = None
    additional_fees: Optional[AdditionalFeesSchema] = None

    estimated_duration: Optional[str] = None
    availability: Optional[Dict[str, Any]] = None
    service_area: Optional[Dict[str, Any]] = None
    qualifications_required: Optional[str] = None
    cancellation_terms: Optional[str] = None


class ListingStatusUpdate(BaseModel):
    status: str = Field(..., description="published, paused, archived, draft")


class ListingResponse(BaseModel):
    id: int
    agency_id: int
    category_id: int
    title: str
    slug: str
    summary: str
    full_description: str
    service_style: str
    included_work: Optional[str] = None
    exclusions: Optional[str] = None
    images: Optional[List[str]] = None
    pricing_model: str
    price: Optional[float] = None
    currency: str
    unit: Optional[str] = None
    additional_fees: Optional[Dict[str, Any]] = None
    estimated_duration: Optional[str] = None
    availability: Optional[Dict[str, Any]] = None
    service_area: Optional[Dict[str, Any]] = None
    qualifications_required: Optional[str] = None
    cancellation_terms: Optional[str] = None
    status: str
    views_count: int
    created_at: datetime
    updated_at: datetime

    # Spec 9.4 formatted pricing output
    pricing_display: Optional[Dict[str, Any]] = None
    agency_name: Optional[str] = None
    agency_status: Optional[str] = None
    category_name: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class ListingListResponse(BaseModel):
    items: List[ListingResponse]
    total: int
