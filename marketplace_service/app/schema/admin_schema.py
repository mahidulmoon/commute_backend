from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, ConfigDict


class AgencyModerationRequest(BaseModel):
    action: str = Field(..., description="approve, reject, suspend, verify, unverify")
    reason: Optional[str] = None


class ListingModerationRequest(BaseModel):
    action: str = Field(..., description="approve, reject, pause, close")
    reason: Optional[str] = None


class AuditLogResponse(BaseModel):
    id: int
    moderator_id: int
    action: str
    target_type: str
    target_id: int
    reason: Optional[str] = None
    metadata_snapshot: Optional[Dict[str, Any]] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class AuditLogListResponse(BaseModel):
    items: List[AuditLogResponse]
    total: int
