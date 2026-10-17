from sqlalchemy import Column, BigInteger, String, Text, JSON, DateTime
from sqlalchemy.sql import func
from app.database import Base


class MarketplaceAuditLog(Base):
    __tablename__ = "marketplace_audit_logs"

    id = Column(BigInteger, primary_key=True, index=True)
    moderator_id = Column(BigInteger, nullable=False, index=True)
    action = Column(String(100), nullable=False, index=True)  # approve_agency, reject_agency, suspend_agency, approve_listing, reject_listing, etc.
    target_type = Column(String(50), nullable=False, index=True)  # agency, listing, review, category
    target_id = Column(BigInteger, nullable=False, index=True)
    reason = Column(Text, nullable=True)
    metadata_snapshot = Column(JSON, default=dict, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False, index=True)
