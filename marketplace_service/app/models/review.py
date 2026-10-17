from sqlalchemy import Column, BigInteger, Integer, String, Text, ForeignKey
from sqlalchemy.orm import relationship
from app.models.base import BaseModel


class ServiceReview(BaseModel):
    __tablename__ = "service_reviews"

    service_id = Column(BigInteger, ForeignKey("service_listings.id", ondelete="CASCADE"), nullable=False, index=True)
    agency_id = Column(BigInteger, ForeignKey("agency_profiles.id", ondelete="CASCADE"), nullable=False, index=True)
    customer_id = Column(BigInteger, nullable=False, index=True)
    
    # Linked to enquiry ensuring review only occurs after a qualifying interaction (Spec 9.7)
    enquiry_id = Column(BigInteger, ForeignKey("service_enquiries.id", ondelete="SET NULL"), nullable=True, index=True)

    rating = Column(Integer, nullable=False)  # 1 to 5
    review_text = Column(Text, nullable=True)
    provider_response = Column(Text, nullable=True)

    # Status: published, pending_moderation, reported, removed
    status = Column(String(50), default="published", nullable=False, index=True)

    service = relationship("ServiceListing", back_populates="reviews")
    agency = relationship("AgencyProfile", back_populates="reviews")
