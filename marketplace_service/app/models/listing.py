from sqlalchemy import Column, BigInteger, Integer, String, Text, Numeric, Boolean, JSON, ForeignKey
from sqlalchemy.orm import relationship
from app.models.base import BaseModel


class ServiceListing(BaseModel):
    __tablename__ = "service_listings"

    agency_id = Column(BigInteger, ForeignKey("agency_profiles.id", ondelete="CASCADE"), nullable=False, index=True)
    category_id = Column(Integer, ForeignKey("service_categories.id", ondelete="RESTRICT"), nullable=False, index=True)

    title = Column(String(255), nullable=False, index=True)
    slug = Column(String(255), nullable=False, index=True)
    summary = Column(String(500), nullable=False)
    full_description = Column(Text, nullable=False)

    # Required service style: on-site, mobile, remote, emergency, scheduled, other
    service_style = Column(String(50), nullable=False, index=True)

    included_work = Column(Text, nullable=True)
    exclusions = Column(Text, nullable=True)
    images = Column(JSON, default=list, nullable=True)

    # Pricing model: fixed, from-price, hourly, daily, per-unit, package, quote_required
    pricing_model = Column(String(50), nullable=False, index=True)
    price = Column(Numeric(12, 2), nullable=True)
    currency = Column(String(3), default="GBP", nullable=False)
    unit = Column(String(50), nullable=True)

    # Additional fees/options: call-out, travel, emergency surcharge, materials, add-ons, minimum charge
    additional_fees = Column(JSON, default=dict, nullable=True)

    estimated_duration = Column(String(100), nullable=True)
    availability = Column(JSON, default=dict, nullable=True)
    
    # Service area coverage (agency-wide or listing-specific)
    service_area = Column(JSON, default=dict, nullable=True)

    qualifications_required = Column(Text, nullable=True)
    cancellation_terms = Column(Text, nullable=True)

    # Status: draft, pending_review, published, paused, rejected, closed, archived
    status = Column(String(50), default="draft", nullable=False, index=True)
    views_count = Column(Integer, default=0, nullable=False)

    agency = relationship("AgencyProfile", back_populates="listings")
    category = relationship("ServiceCategory", back_populates="listings")
    enquiries = relationship("ServiceEnquiry", back_populates="service", cascade="all, delete-orphan")
    reviews = relationship("ServiceReview", back_populates="service", cascade="all, delete-orphan")
