from typing import Optional, List
from decimal import Decimal
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import desc

from app.database import get_db_global
from app.models.enquiry import ServiceEnquiry, EnquiryMessage
from app.models.listing import ServiceListing
from app.models.agency import AgencyProfile
from app.schema.enquiry_schema import (
    EnquiryCreate,
    QuoteSubmissionRequest,
    EnquiryStatusUpdateRequest,
    EnquiryMessageCreate,
    EnquiryMessageResponse,
    EnquiryResponse,
    EnquiryListResponse,
)
from app.utils.auth_validation import get_current_user
from app.utils.response import success_response, error_response
from app.logger import logger

router = APIRouter(prefix="/enquiries", tags=["Enquiries & Quotes"])

VALID_STATUSES = [
    "submitted",
    "viewed",
    "provider_responded",
    "quote_provided",
    "accepted",
    "declined",
    "cancelled",
    "completed",
    "disputed",
]


def build_enquiry_dict(enquiry: ServiceEnquiry) -> dict:
    return {
        "id": enquiry.id,
        "service_id": enquiry.service_id,
        "agency_id": enquiry.agency_id,
        "customer_id": enquiry.customer_id,
        "description_of_work": enquiry.description_of_work,
        "location": enquiry.location,
        "preferred_date_time": enquiry.preferred_date_time.isoformat() if enquiry.preferred_date_time else None,
        "photos": enquiry.photos or [],
        "quote_amount": float(enquiry.quote_amount) if enquiry.quote_amount is not None else None,
        "quote_currency": enquiry.quote_currency,
        "quote_notes": enquiry.quote_notes,
        "status": enquiry.status,
        "created_at": enquiry.created_at.isoformat() if enquiry.created_at else None,
        "updated_at": enquiry.updated_at.isoformat() if enquiry.updated_at else None,
        "service_title": enquiry.service.title if enquiry.service else None,
        "agency_name": enquiry.agency.business_name if enquiry.agency else None,
        "messages_count": len(enquiry.messages) if enquiry.messages else 0,
    }


@router.post("")
@router.post("/")
def create_enquiry(
    req: EnquiryCreate,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db_global),
):
    """
    Customer submits an enquiry or quote request for a service (Spec 9.6).
    """
    customer_id = current_user.get("id")

    try:
        service = db.query(ServiceListing).filter(
            ServiceListing.id == req.service_id,
            ServiceListing.status == "published"
        ).first()
        if not service:
            return error_response("Service listing not found or is currently not accepting enquiries.", None, 404)

        # Disallow enquiring on own agency listing
        if service.agency.user_id == customer_id:
            return error_response("You cannot submit an enquiry to your own service listing.", None, 400)

        enquiry = ServiceEnquiry(
            service_id=service.id,
            agency_id=service.agency_id,
            customer_id=customer_id,
            description_of_work=req.description_of_work,
            location=req.location,
            preferred_date_time=req.preferred_date_time,
            photos=req.photos or [],
            status="submitted",
        )

        db.add(enquiry)
        db.commit()
        db.refresh(enquiry)

        logger.info(f"Enquiry created: id={enquiry.id} by customer {customer_id} for service {service.id}")
        return success_response("Enquiry submitted successfully.", build_enquiry_dict(enquiry), 201)

    except Exception as e:
        db.rollback()
        logger.error(f"Error submitting enquiry: {str(e)}")
        return error_response(str(e), None, 500)


@router.get("/my/customer")
def list_customer_enquiries(
    status: Optional[str] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db_global),
):
    customer_id = current_user.get("id")
    try:
        query = db.query(ServiceEnquiry).filter(ServiceEnquiry.customer_id == customer_id)
        if status:
            query = query.filter(ServiceEnquiry.status == status.lower())

        total = query.count()
        enquiries = query.order_by(desc(ServiceEnquiry.created_at)).offset(skip).limit(limit).all()

        items = [build_enquiry_dict(e) for e in enquiries]
        return success_response("Customer enquiries fetched.", {"items": items, "total": total}, 200)

    except Exception as e:
        logger.error(f"Error fetching customer enquiries: {str(e)}")
        return error_response(str(e), None, 500)


@router.get("/my/agency")
def list_agency_enquiries(
    status: Optional[str] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db_global),
):
    user_id = current_user.get("id")
    try:
        agency = db.query(AgencyProfile).filter(AgencyProfile.user_id == user_id).first()
        if not agency:
            return error_response("No agency profile found.", None, 403)

        query = db.query(ServiceEnquiry).filter(ServiceEnquiry.agency_id == agency.id)
        if status:
            query = query.filter(ServiceEnquiry.status == status.lower())

        total = query.count()
        enquiries = query.order_by(desc(ServiceEnquiry.created_at)).offset(skip).limit(limit).all()

        items = [build_enquiry_dict(e) for e in enquiries]
        return success_response("Agency enquiries fetched.", {"items": items, "total": total}, 200)

    except Exception as e:
        logger.error(f"Error fetching agency enquiries: {str(e)}")
        return error_response(str(e), None, 500)


@router.get("/{enquiry_id}")
def get_enquiry_detail(
    enquiry_id: int,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db_global),
):
    user_id = current_user.get("id")
    try:
        enquiry = db.query(ServiceEnquiry).filter(ServiceEnquiry.id == enquiry_id).first()
        if not enquiry:
            return error_response("Enquiry not found.", None, 404)

        is_customer = enquiry.customer_id == user_id
        is_provider = enquiry.agency.user_id == user_id
        is_admin = str(current_user.get("type", "")).upper() == "ADMIN"

        if not (is_customer or is_provider or is_admin):
            return error_response("Access denied: You are not a participant in this enquiry.", None, 403)

        # Mark as viewed if provider opens it first time
        if is_provider and enquiry.status == "submitted":
            enquiry.status = "viewed"
            db.commit()

        return success_response("Enquiry detail fetched.", build_enquiry_dict(enquiry), 200)

    except Exception as e:
        db.rollback()
        logger.error(f"Error fetching enquiry {enquiry_id}: {str(e)}")
        return error_response(str(e), None, 500)


@router.post("/{enquiry_id}/quote")
def submit_quote(
    enquiry_id: int,
    req: QuoteSubmissionRequest,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db_global),
):
    """
    Agency provider submits a formal quote for an enquiry (Spec 9.6).
    """
    user_id = current_user.get("id")
    try:
        enquiry = db.query(ServiceEnquiry).filter(ServiceEnquiry.id == enquiry_id).first()
        if not enquiry:
            return error_response("Enquiry not found.", None, 404)

        if enquiry.agency.user_id != user_id:
            return error_response("Only the receiving agency can submit a quote.", None, 403)

        enquiry.quote_amount = req.quote_amount
        enquiry.quote_currency = (req.quote_currency or "GBP").upper()
        enquiry.quote_notes = req.quote_notes
        enquiry.status = "quote_provided"

        # Auto-append a quote announcement in the message thread
        msg = EnquiryMessage(
            enquiry_id=enquiry.id,
            sender_id=user_id,
            sender_role="provider",
            content=f"Quote provided: {enquiry.quote_currency} {req.quote_amount:.2f}. Notes: {req.quote_notes or 'None'}",
        )
        db.add(msg)

        db.commit()
        logger.info(f"Quote submitted for enquiry {enquiry_id}: {enquiry.quote_amount}")
        return success_response("Quote submitted successfully.", build_enquiry_dict(enquiry), 200)

    except Exception as e:
        db.rollback()
        logger.error(f"Error submitting quote: {str(e)}")
        return error_response(str(e), None, 500)


@router.patch("/{enquiry_id}/status")
def update_enquiry_status(
    enquiry_id: int,
    req: EnquiryStatusUpdateRequest,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db_global),
):
    """
    Transition enquiry state: accepted, declined, cancelled, completed, disputed (Spec 9.6).
    """
    user_id = current_user.get("id")
    try:
        enquiry = db.query(ServiceEnquiry).filter(ServiceEnquiry.id == enquiry_id).first()
        if not enquiry:
            return error_response("Enquiry not found.", None, 404)

        is_customer = enquiry.customer_id == user_id
        is_provider = enquiry.agency.user_id == user_id
        is_admin = str(current_user.get("type", "")).upper() == "ADMIN"

        if not (is_customer or is_provider or is_admin):
            return error_response("Access denied: You are not a participant in this enquiry.", None, 403)

        new_status = req.status.lower()
        if new_status not in VALID_STATUSES:
            return error_response(f"Invalid status '{new_status}'. Allowed: {VALID_STATUSES}", None, 400)

        # Role-based transition checks
        if new_status == "accepted" and not is_customer:
            return error_response("Only the customer can accept a quote or enquiry.", None, 403)
        if new_status == "completed" and not (is_customer or is_provider):
            return error_response("Only participants can mark an enquiry as completed.", None, 403)

        enquiry.status = new_status
        db.commit()

        logger.info(f"Enquiry {enquiry_id} status changed to '{new_status}' by user {user_id}")
        return success_response(f"Enquiry status updated to '{new_status}'.", build_enquiry_dict(enquiry), 200)

    except Exception as e:
        db.rollback()
        logger.error(f"Error updating enquiry status: {str(e)}")
        return error_response(str(e), None, 500)


# =====================================================================
# Private Enquiry Message Thread (Spec 9.6)
# Limited strictly to authorised participants in that enquiry.
# =====================================================================

@router.get("/{enquiry_id}/messages")
def get_enquiry_messages(
    enquiry_id: int,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db_global),
):
    user_id = current_user.get("id")
    try:
        enquiry = db.query(ServiceEnquiry).filter(ServiceEnquiry.id == enquiry_id).first()
        if not enquiry:
            return error_response("Enquiry not found.", None, 404)

        is_customer = enquiry.customer_id == user_id
        is_provider = enquiry.agency.user_id == user_id
        is_admin = str(current_user.get("type", "")).upper() == "ADMIN"

        if not (is_customer or is_provider or is_admin):
            return error_response("Access denied: You are not authorized to view messages for this enquiry.", None, 403)

        messages = db.query(EnquiryMessage).filter(EnquiryMessage.enquiry_id == enquiry_id).order_by(EnquiryMessage.created_at.asc()).all()

        items = [
            {
                "id": m.id,
                "enquiry_id": m.enquiry_id,
                "sender_id": m.sender_id,
                "sender_role": m.sender_role,
                "content": m.content,
                "attachments": m.attachments or [],
                "is_read": m.is_read,
                "created_at": m.created_at.isoformat() if m.created_at else None,
            }
            for m in messages
        ]
        return success_response("Enquiry messages retrieved.", {"items": items, "total": len(items)}, 200)

    except Exception as e:
        logger.error(f"Error fetching enquiry messages: {str(e)}")
        return error_response(str(e), None, 500)


@router.post("/{enquiry_id}/messages")
def send_enquiry_message(
    enquiry_id: int,
    req: EnquiryMessageCreate,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db_global),
):
    user_id = current_user.get("id")
    try:
        enquiry = db.query(ServiceEnquiry).filter(ServiceEnquiry.id == enquiry_id).first()
        if not enquiry:
            return error_response("Enquiry not found.", None, 404)

        is_customer = enquiry.customer_id == user_id
        is_provider = enquiry.agency.user_id == user_id
        is_admin = str(current_user.get("type", "")).upper() == "ADMIN"

        if not (is_customer or is_provider or is_admin):
            return error_response("Access denied: You are not authorized to send messages in this enquiry.", None, 403)

        sender_role = "customer" if is_customer else ("provider" if is_provider else "admin")

        msg = EnquiryMessage(
            enquiry_id=enquiry_id,
            sender_id=user_id,
            sender_role=sender_role,
            content=req.content,
            attachments=req.attachments or [],
        )

        if is_provider and enquiry.status in ["submitted", "viewed"]:
            enquiry.status = "provider_responded"

        db.add(msg)
        db.commit()
        db.refresh(msg)

        logger.info(f"Enquiry message sent in {enquiry_id} by {sender_role} {user_id}")
        return success_response(
            "Message sent.",
            {
                "id": msg.id,
                "enquiry_id": msg.enquiry_id,
                "sender_id": msg.sender_id,
                "sender_role": msg.sender_role,
                "content": msg.content,
                "created_at": msg.created_at.isoformat(),
            },
            201
        )

    except Exception as e:
        db.rollback()
        logger.error(f"Error sending enquiry message: {str(e)}")
        return error_response(str(e), None, 500)
