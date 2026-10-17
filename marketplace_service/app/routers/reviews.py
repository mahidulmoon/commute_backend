from typing import Optional
from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import desc, func

from app.database import get_db_global
from app.models.review import ServiceReview
from app.models.listing import ServiceListing
from app.models.agency import AgencyProfile
from app.models.enquiry import ServiceEnquiry
from app.schema.review_schema import ReviewCreate, ReviewResponseCreate, ReviewResponse, ReviewListResponse
from app.utils.auth_validation import get_current_user
from app.utils.response import success_response, error_response
from app.logger import logger

router = APIRouter(prefix="/reviews", tags=["Reviews & Ratings"])


def build_review_dict(review: ServiceReview) -> dict:
    return {
        "id": review.id,
        "service_id": review.service_id,
        "agency_id": review.agency_id,
        "customer_id": review.customer_id,
        "enquiry_id": review.enquiry_id,
        "rating": review.rating,
        "review_text": review.review_text,
        "provider_response": review.provider_response,
        "status": review.status,
        "created_at": review.created_at.isoformat() if review.created_at else None,
        "updated_at": review.updated_at.isoformat() if review.updated_at else None,
    }


@router.post("")
@router.post("/")
def submit_review(
    req: ReviewCreate,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db_global),
):
    """
    Submit a review (Spec 9.7).
    Enforces qualifying interaction: The customer must have a valid completed enquiry for this service.
    """
    customer_id = current_user.get("id")

    try:
        # Check qualifying interaction
        enquiry = db.query(ServiceEnquiry).filter(
            ServiceEnquiry.id == req.enquiry_id,
            ServiceEnquiry.customer_id == customer_id,
            ServiceEnquiry.service_id == req.service_id,
            ServiceEnquiry.status == "completed"
        ).first()

        if not enquiry:
            return error_response(
                "You can only review a service after a completed interaction (qualifying completed enquiry).",
                None,
                400
            )

        # Check if already reviewed this enquiry
        existing_review = db.query(ServiceReview).filter(ServiceReview.enquiry_id == req.enquiry_id).first()
        if existing_review:
            return error_response("You have already reviewed this interaction.", None, 400)

        review = ServiceReview(
            service_id=req.service_id,
            agency_id=enquiry.agency_id,
            customer_id=customer_id,
            enquiry_id=enquiry.id,
            rating=req.rating,
            review_text=req.review_text,
            status="published",
        )

        db.add(review)
        db.commit()
        db.refresh(review)

        logger.info(f"Review created: id={review.id} rating={review.rating} for service {req.service_id}")
        return success_response("Review submitted successfully.", build_review_dict(review), 201)

    except Exception as e:
        db.rollback()
        logger.error(f"Error submitting review: {str(e)}")
        return error_response(str(e), None, 500)


@router.get("/listing/{listing_id}")
def get_listing_reviews(
    listing_id: int,
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db_global),
):
    try:
        query = db.query(ServiceReview).filter(
            ServiceReview.service_id == listing_id,
            ServiceReview.status == "published"
        )
        total = query.count()
        avg_rating = db.query(func.avg(ServiceReview.rating)).filter(
            ServiceReview.service_id == listing_id,
            ServiceReview.status == "published"
        ).scalar() or 0.0

        reviews = query.order_by(desc(ServiceReview.created_at)).offset(skip).limit(limit).all()

        items = [build_review_dict(r) for r in reviews]
        return success_response(
            "Reviews fetched.",
            {"items": items, "total": total, "average_rating": round(float(avg_rating), 1)},
            200
        )

    except Exception as e:
        logger.error(f"Error fetching reviews for listing {listing_id}: {str(e)}")
        return error_response(str(e), None, 500)


@router.post("/{review_id}/response")
def respond_to_review(
    review_id: int,
    req: ReviewResponseCreate,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db_global),
):
    """
    Agency provider responds to a customer review (Spec 9.7).
    """
    user_id = current_user.get("id")
    try:
        review = db.query(ServiceReview).filter(ServiceReview.id == review_id).first()
        if not review:
            return error_response("Review not found.", None, 404)

        if review.agency.user_id != user_id:
            return error_response("Only the reviewed agency can respond to this review.", None, 403)

        review.provider_response = req.provider_response
        db.commit()

        logger.info(f"Provider responded to review {review_id}")
        return success_response("Provider response added successfully.", build_review_dict(review), 200)

    except Exception as e:
        db.rollback()
        logger.error(f"Error responding to review: {str(e)}")
        return error_response(str(e), None, 500)
