from sqlalchemy import Column, BigInteger, String, Text, Boolean, JSON, Enum
from sqlalchemy.orm import relationship
from app.models.base import BaseModel


class AgencyProfile(BaseModel):
    __tablename__ = "agency_profiles"

    user_id = Column(BigInteger, unique=True, nullable=False, index=True)
    business_name = Column(String(255), nullable=False, index=True)
    slug = Column(String(255), unique=True, nullable=False, index=True)
    logo_url = Column(String(255), nullable=True)
    
    short_summary = Column(String(500), nullable=False)
    full_description = Column(Text, nullable=True)

    # Categories associated with this agency (list of category IDs)
    category_ids = Column(JSON, default=list, nullable=False)

    # Service areas (Spec 9.1): e.g. {"cities": ["London"], "towns": [], "postcodes": ["SW1", "E1"], "radius_km": 25, "remote_online": false}
    service_areas = Column(JSON, default=dict, nullable=False)

    # Private contact details (not public by default)
    contact_email = Column(String(150), nullable=True)
    contact_phone = Column(String(50), nullable=True)
    contact_methods = Column(JSON, default=dict, nullable=False)

    website = Column(String(255), nullable=True)
    opening_hours = Column(JSON, nullable=True)
    languages = Column(JSON, default=list, nullable=True)
    qualifications = Column(JSON, default=list, nullable=True)

    # System-managed status (Spec 9.1): Pending, Verified, Rejected, Suspended, Unverified, Published, Archived
    status = Column(
        String(50),
        default="pending",
        nullable=False,
        index=True
    )
    is_active = Column(Boolean, default=True, nullable=False, index=True)

    listings = relationship("ServiceListing", back_populates="agency", cascade="all, delete-orphan")
    enquiries = relationship("ServiceEnquiry", back_populates="agency", cascade="all, delete-orphan")
    reviews = relationship("ServiceReview", back_populates="agency", cascade="all, delete-orphan")
