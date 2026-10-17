from sqlalchemy import Column, BigInteger, String, Text, Numeric, Boolean, JSON, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.models.base import BaseModel


class ServiceEnquiry(BaseModel):
    __tablename__ = "service_enquiries"

    service_id = Column(BigInteger, ForeignKey("service_listings.id", ondelete="CASCADE"), nullable=False, index=True)
    agency_id = Column(BigInteger, ForeignKey("agency_profiles.id", ondelete="CASCADE"), nullable=False, index=True)
    customer_id = Column(BigInteger, nullable=False, index=True)

    description_of_work = Column(Text, nullable=False)
    location = Column(String(255), nullable=False)
    preferred_date_time = Column(DateTime(timezone=True), nullable=True)
    photos = Column(JSON, default=list, nullable=True)

    # Provider quote proposal (optional MVP quote integration)
    quote_amount = Column(Numeric(12, 2), nullable=True)
    quote_currency = Column(String(3), default="GBP", nullable=False)
    quote_notes = Column(Text, nullable=True)

    # State machine: submitted, viewed, provider_responded, quote_provided, accepted, declined, cancelled, completed, disputed
    status = Column(String(50), default="submitted", nullable=False, index=True)

    service = relationship("ServiceListing", back_populates="enquiries")
    agency = relationship("AgencyProfile", back_populates="enquiries")
    messages = relationship("EnquiryMessage", back_populates="enquiry", cascade="all, delete-orphan", order_by="EnquiryMessage.created_at.asc()")


class EnquiryMessage(BaseModel):
    """
    Message thread strictly restricted to authorized participants of this enquiry (Spec 9.6).
    """
    __tablename__ = "enquiry_messages"

    enquiry_id = Column(BigInteger, ForeignKey("service_enquiries.id", ondelete="CASCADE"), nullable=False, index=True)
    sender_id = Column(BigInteger, nullable=False, index=True)
    sender_role = Column(String(20), nullable=False)  # 'customer', 'provider', 'admin'
    content = Column(Text, nullable=False)
    attachments = Column(JSON, default=list, nullable=True)
    is_read = Column(Boolean, default=False, nullable=False)

    enquiry = relationship("ServiceEnquiry", back_populates="messages")
