from typing import Optional
from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import desc

from app.database import get_db_global
from app.models.agency import AgencyProfile
from app.models.listing import ServiceListing
from app.models.audit_log import MarketplaceAuditLog
from app.schema.admin_schema import (
    AgencyModerationRequest,
    ListingModerationRequest,
    AuditLogResponse,
    AuditLogListResponse,
)
from app.utils.auth_validation import get_admin_user
from app.utils.response import success_response, error_response
from app.logger import logger

router = APIRouter(prefix="/admin", tags=["Admin & Moderation"])


def log_moderation_action(
    db: Session,
    moderator_id: int,
    action: str,
    target_type: str,
    target_id: int,
    reason: Optional[str] = None,
    metadata_snapshot: Optional[dict] = None,
):
    audit = MarketplaceAuditLog(
        moderator_id=moderator_id,
        action=action,
        target_type=target_type,
        target_id=target_id,
        reason=reason,
        metadata_snapshot=metadata_snapshot or {},
    )
    db.add(audit)
    db.commit()


@router.get("/agencies")
def list_agencies_for_moderation(
    status: Optional[str] = Query(None, description="pending, verified, rejected, suspended"),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    admin_user=Depends(get_admin_user),
    db: Session = Depends(get_db_global),
):
    """
    Admin: View all agency profiles with optional status filter (Spec 9.9).
    """
    try:
        query = db.query(AgencyProfile)
        if status:
            query = query.filter(AgencyProfile.status == status.lower())

        total = query.count()
        agencies = query.order_by(desc(AgencyProfile.created_at)).offset(skip).limit(limit).all()

        items = [
            {
                "id": a.id,
                "user_id": a.user_id,
                "business_name": a.business_name,
                "slug": a.slug,
                "short_summary": a.short_summary,
                "category_ids": a.category_ids,
                "service_areas": a.service_areas,
                "contact_email": a.contact_email,
                "contact_phone": a.contact_phone,
                "status": a.status,
                "is_active": a.is_active,
                "created_at": a.created_at.isoformat() if a.created_at else None,
            }
            for a in agencies
        ]
        return success_response("Agencies fetched for moderation.", {"items": items, "total": total}, 200)

    except Exception as e:
        logger.error(f"Admin error listing agencies: {str(e)}")
        return error_response(str(e), None, 500)


@router.post("/agencies/{agency_id}/moderate")
def moderate_agency(
    agency_id: int,
    req: AgencyModerationRequest,
    admin_user=Depends(get_admin_user),
    db: Session = Depends(get_db_global),
):
    """
    Admin: Approve, verify, reject, or suspend an agency profile.
    Automatically creates an entry in MarketplaceAuditLog (Spec 9.9).
    """
    admin_id = admin_user.get("id")
    try:
        agency = db.query(AgencyProfile).filter(AgencyProfile.id == agency_id).first()
        if not agency:
            return error_response("Agency not found.", None, 404)

        action = req.action.lower()
        if action == "approve" or action == "verify":
            agency.status = "verified"
            agency.is_active = True
        elif action == "reject":
            agency.status = "rejected"
        elif action == "suspend":
            agency.status = "suspended"
            agency.is_active = False
        elif action == "unverify":
            agency.status = "unverified"
        else:
            return error_response(f"Unsupported moderation action '{action}'.", None, 400)

        db.commit()

        # Audit log recording (Spec 9.9)
        log_moderation_action(
            db=db,
            moderator_id=admin_id,
            action=f"agency_{action}",
            target_type="agency",
            target_id=agency.id,
            reason=req.reason,
            metadata_snapshot={"new_status": agency.status, "business_name": agency.business_name},
        )

        logger.info(f"Admin {admin_id} moderated agency {agency_id} -> {agency.status}. Reason: {req.reason}")
        return success_response(f"Agency {action}d successfully.", {"id": agency.id, "status": agency.status}, 200)

    except Exception as e:
        db.rollback()
        logger.error(f"Error moderating agency {agency_id}: {str(e)}")
        return error_response(str(e), None, 500)


@router.get("/listings")
def list_listings_for_moderation(
    status: Optional[str] = Query(None, description="pending_review, published, rejected, paused"),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    admin_user=Depends(get_admin_user),
    db: Session = Depends(get_db_global),
):
    try:
        query = db.query(ServiceListing)
        if status:
            query = query.filter(ServiceListing.status == status.lower())

        total = query.count()
        listings = query.order_by(desc(ServiceListing.created_at)).offset(skip).limit(limit).all()

        items = [
            {
                "id": l.id,
                "agency_id": l.agency_id,
                "agency_name": l.agency.business_name if l.agency else None,
                "category_id": l.category_id,
                "title": l.title,
                "summary": l.summary,
                "pricing_model": l.pricing_model,
                "price": float(l.price) if l.price is not None else None,
                "status": l.status,
                "created_at": l.created_at.isoformat() if l.created_at else None,
            }
            for l in listings
        ]
        return success_response("Listings fetched for moderation.", {"items": items, "total": total}, 200)

    except Exception as e:
        logger.error(f"Admin error listing listings: {str(e)}")
        return error_response(str(e), None, 500)


@router.post("/listings/{listing_id}/moderate")
def moderate_listing(
    listing_id: int,
    req: ListingModerationRequest,
    admin_user=Depends(get_admin_user),
    db: Session = Depends(get_db_global),
):
    """
    Admin: Approve, reject, or pause a service listing.
    Recorded in MarketplaceAuditLog (Spec 9.9).
    """
    admin_id = admin_user.get("id")
    try:
        listing = db.query(ServiceListing).filter(ServiceListing.id == listing_id).first()
        if not listing:
            return error_response("Listing not found.", None, 404)

        action = req.action.lower()
        if action == "approve":
            listing.status = "published"
        elif action == "reject":
            listing.status = "rejected"
        elif action == "pause":
            listing.status = "paused"
        elif action == "close":
            listing.status = "closed"
        else:
            return error_response(f"Unsupported action '{action}'.", None, 400)

        db.commit()

        log_moderation_action(
            db=db,
            moderator_id=admin_id,
            action=f"listing_{action}",
            target_type="listing",
            target_id=listing.id,
            reason=req.reason,
            metadata_snapshot={"new_status": listing.status, "title": listing.title},
        )

        logger.info(f"Admin {admin_id} moderated listing {listing_id} -> {listing.status}. Reason: {req.reason}")
        return success_response(f"Listing {action}d successfully.", {"id": listing.id, "status": listing.status}, 200)

    except Exception as e:
        db.rollback()
        logger.error(f"Error moderating listing {listing_id}: {str(e)}")
        return error_response(str(e), None, 500)


@router.get("/audit-logs")
def get_audit_logs(
    target_type: Optional[str] = Query(None, description="agency, listing, review, category"),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    admin_user=Depends(get_admin_user),
    db: Session = Depends(get_db_global),
):
    """
    Admin: Retrieve moderator audit logs (Spec 9.9).
    """
    try:
        query = db.query(MarketplaceAuditLog)
        if target_type:
            query = query.filter(MarketplaceAuditLog.target_type == target_type.lower())

        total = query.count()
        logs = query.order_by(desc(MarketplaceAuditLog.created_at)).offset(skip).limit(limit).all()

        items = [
            {
                "id": l.id,
                "moderator_id": l.moderator_id,
                "action": l.action,
                "target_type": l.target_type,
                "target_id": l.target_id,
                "reason": l.reason,
                "metadata_snapshot": l.metadata_snapshot or {},
                "created_at": l.created_at.isoformat() if l.created_at else None,
            }
            for l in logs
        ]
        return success_response("Audit logs fetched.", {"items": items, "total": total}, 200)

    except Exception as e:
        logger.error(f"Error fetching audit logs: {str(e)}")
        return error_response(str(e), None, 500)
