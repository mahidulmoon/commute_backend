from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, EmailStr, ConfigDict


class ServiceAreaSchema(BaseModel):
    cities: Optional[List[str]] = []
    towns: Optional[List[str]] = []
    postcode_districts: Optional[List[str]] = []
    radius_km: Optional[float] = None
    remote_online: Optional[bool] = False


class ContactMethodsSchema(BaseModel):
    allow_enquiry: Optional[bool] = True
    show_phone_publicly: Optional[bool] = False
    show_email_publicly: Optional[bool] = False


class AgencyOnboardingRequest(BaseModel):
    business_name: str = Field(..., min_length=2, max_length=255)
    logo_url: Optional[str] = None
    short_summary: str = Field(..., min_length=10, max_length=500)
    full_description: Optional[str] = None
    category_ids: List[int] = Field(..., min_items=1)
    service_areas: ServiceAreaSchema
    contact_email: Optional[str] = None
    contact_phone: Optional[str] = None
    contact_methods: Optional[ContactMethodsSchema] = Field(default_factory=ContactMethodsSchema)
    website: Optional[str] = None
    opening_hours: Optional[Dict[str, Any]] = None
    languages: Optional[List[str]] = ["English"]
    qualifications: Optional[List[Dict[str, Any]]] = []


class AgencyUpdateRequest(BaseModel):
    business_name: Optional[str] = Field(None, min_length=2, max_length=255)
    logo_url: Optional[str] = None
    short_summary: Optional[str] = Field(None, min_length=10, max_length=500)
    full_description: Optional[str] = None
    category_ids: Optional[List[int]] = None
    service_areas: Optional[ServiceAreaSchema] = None
    contact_email: Optional[str] = None
    contact_phone: Optional[str] = None
    contact_methods: Optional[ContactMethodsSchema] = None
    website: Optional[str] = None
    opening_hours: Optional[Dict[str, Any]] = None
    languages: Optional[List[str]] = None
    qualifications: Optional[List[Dict[str, Any]]] = None


class AgencyResponse(BaseModel):
    id: int
    user_id: int
    business_name: str
    slug: str
    logo_url: Optional[str] = None
    short_summary: str
    full_description: Optional[str] = None
    category_ids: List[int]
    service_areas: Dict[str, Any]
    contact_email: Optional[str] = None
    contact_phone: Optional[str] = None
    contact_methods: Dict[str, Any]
    website: Optional[str] = None
    opening_hours: Optional[Dict[str, Any]] = None
    languages: Optional[List[str]] = None
    qualifications: Optional[List[Dict[str, Any]]] = None
    status: str
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class AgencyDashboardResponse(BaseModel):
    agency_id: int
    business_name: str
    profile_completion_percentage: int
    status: str
    is_verified: bool
    total_listings: int
    published_listings: int
    draft_listings: int
    paused_listings: int
    archived_listings: int
    total_enquiries: int
    new_enquiries: int
    in_progress_enquiries: int
    completed_enquiries: int
    recent_enquiries: List[Dict[str, Any]]
