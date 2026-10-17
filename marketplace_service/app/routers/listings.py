import re
from typing import Optional, List
from decimal import Decimal
from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import desc, asc, or_, and_, select

from app.database import get_db_global
from app.models.listing import ServiceListing
from app.models.agency import AgencyProfile
from app.models.category import ServiceCategory
from app.schema.listing_schema import (
    ListingCreate,
    ListingUpdate,
    ListingStatusUpdate,
    ListingResponse,
    ListingListResponse,
)
from app.utils.auth_validation import get_current_user
from app.utils.response import success_response, error_response
from app.utils.pricing_helper import format_pricing_display
from app.logger import logger

router = APIRouter(prefix="/listings", tags=["Listings"])


def slugify(text: str) -> str:
    text = text.lower().strip()
    text = re.sub(r"[^\w\s-]", "", text)
    return re.sub(r"[-\s]+", "-", text)


def build_listing_dict(listing: ServiceListing) -> dict:
    pricing_display = format_pricing_display(
        pricing_model=listing.pricing_model,
        price=listing.price,
        currency=listing.currency,
        unit=listing.unit,
        additional_fees=listing.additional_fees,
        inclusions=listing.included_work,
        exclusions=listing.exclusions,
    )

    return {
        "id": listing.id,
        "agency_id": listing.agency_id,
        "category_id": listing.category_id,
        "title": listing.title,
        "slug": listing.slug,
        "summary": listing.summary,
        "full_description": listing.full_description,
        "service_style": listing.service_style,
        "included_work": listing.included_work,
        "exclusions": listing.exclusions,
        "images": listing.images or [],
        "pricing_model": listing.pricing_model,
        "price": float(listing.price) if listing.price is not None else None,
        "currency": listing.currency,
        "unit": listing.unit,
        "additional_fees": listing.additional_fees or {},
        "estimated_duration": listing.estimated_duration,
        "availability": listing.availability or {},
        "service_area": listing.service_area or {},
        "qualifications_required": listing.qualifications_required,
        "cancellation_terms": listing.cancellation_terms,
        "status": listing.status,
        "views_count": listing.views_count,
        "created_at": listing.created_at.isoformat() if listing.created_at else None,
        "updated_at": listing.updated_at.isoformat() if listing.updated_at else None,
        "pricing_display": pricing_display,
        "agency_name": listing.agency.business_name if listing.agency else None,
        "agency_status": listing.agency.status if listing.agency else None,
        "category_name": listing.category.name if listing.category else None,
    }


@router.post("")
@router.post("/")
def create_listing(
    req: ListingCreate,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db_global),
):
    """
    Agency provider creates a service listing (Spec 9.3).
    Validates active category and pricing parameters.
    """
    user_id = current_user.get("id")

    try:
        agency = db.query(AgencyProfile).filter(AgencyProfile.user_id == user_id).first()
        if not agency:
            return error_response("You must register an agency profile before publishing listings.", None, 400)

        # Spec 9.3: Category must be active
        category = db.query(ServiceCategory).filter(
            ServiceCategory.id == req.category_id,
            ServiceCategory.is_active.is_(True)
        ).first()
        if not category:
            return error_response("The selected service category does not exist or is inactive.", None, 400)

        base_slug = slugify(req.title)
        slug = f"{base_slug}-{agency.id}"
        counter = 1
        while db.query(ServiceListing).filter(ServiceListing.slug == slug).first():
            slug = f"{base_slug}-{agency.id}-{counter}"
            counter += 1

        initial_status = "published" if req.publish_now and agency.status in ["verified", "published"] else "draft"

        listing = ServiceListing(
            agency_id=agency.id,
            category_id=req.category_id,
            title=req.title,
            slug=slug,
            summary=req.summary,
            full_description=req.full_description,
            service_style=req.service_style.lower(),
            included_work=req.included_work,
            exclusions=req.exclusions,
            images=req.images or [],
            pricing_model=req.pricing_model.lower(),
            price=req.price,
            currency=(req.currency or "GBP").upper(),
            unit=req.unit,
            additional_fees=req.additional_fees.model_dump() if req.additional_fees else {},
            estimated_duration=req.estimated_duration,
            availability=req.availability or {},
            service_area=req.service_area or agency.service_areas,
            qualifications_required=req.qualifications_required,
            cancellation_terms=req.cancellation_terms,
            status=initial_status,
        )

        db.add(listing)
        db.commit()
        db.refresh(listing)

        logger.info(f"Listing created: '{listing.title}' (id={listing.id}) by agency {agency.id}")
        return success_response("Service listing created successfully.", build_listing_dict(listing), 201)

    except Exception as e:
        db.rollback()
        logger.error(f"Error creating listing: {str(e)}")
        return error_response(str(e), None, 500)


@router.get("")
@router.get("/")
def search_and_browse_listings(
    q: Optional[str] = Query(None, description="Search term across title, description, summary"),
    category_id: Optional[int] = Query(None, description="Filter by category ID"),
    category_slug: Optional[str] = Query(None, description="Filter by category slug"),
    service_style: Optional[str] = Query(None, description="on-site, mobile, remote, emergency, scheduled, other"),
    pricing_model: Optional[str] = Query(None, description="fixed, from-price, hourly, daily, per-unit, package, quote_required"),
    min_price: Optional[float] = Query(None, ge=0),
    max_price: Optional[float] = Query(None, ge=0),
    location: Optional[str] = Query(None, description="Location match in service_area or agency areas"),
    verified_only: bool = Query(False, description="Filter only verified providers"),
    sort_by: str = Query("newest", description="newest, price_asc, price_desc, popular"),
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db_global),
):
    """
    Public customer search and browse for service listings (Spec 9.5).
    Includes rich filtering, sorting, and pricing display rules (Spec 9.4).
    """
    try:
        query = (
            db.query(ServiceListing)
            .join(AgencyProfile, ServiceListing.agency_id == AgencyProfile.id)
            .filter(
                ServiceListing.status == "published",
                AgencyProfile.is_active.is_(True),
                AgencyProfile.status.notin_(["rejected", "suspended"])
            )
        )

        if category_id:
            query = query.filter(ServiceListing.category_id == category_id)
        elif category_slug:
            cat = db.query(ServiceCategory).filter(ServiceCategory.slug == category_slug).first()
            if cat:
                query = query.filter(ServiceListing.category_id == cat.id)

        if service_style:
            query = query.filter(ServiceListing.service_style == service_style.lower())

        if pricing_model:
            query = query.filter(ServiceListing.pricing_model == pricing_model.lower())

        if min_price is not None:
            query = query.filter(ServiceListing.price >= min_price)

        if max_price is not None:
            query = query.filter(ServiceListing.price <= max_price)

        if verified_only:
            query = query.filter(AgencyProfile.status == "verified")

        if q:
            search_pattern = f"%{q}%"
            query = query.filter(
                or_(
                    ServiceListing.title.ilike(search_pattern),
                    ServiceListing.summary.ilike(search_pattern),
                    ServiceListing.full_description.ilike(search_pattern),
                    AgencyProfile.business_name.ilike(search_pattern),
                )
            )

        if location:
            loc_pattern = f"%{location}%"
            query = query.filter(
                or_(
                    ServiceListing.service_area.cast(str).ilike(loc_pattern),
                    AgencyProfile.service_areas.cast(str).ilike(loc_pattern),
                )
            )

        # Sorting (Spec 9.5)
        if sort_by == "price_asc":
            query = query.order_by(ServiceListing.price.asc().nulls_last())
        elif sort_by == "price_desc":
            query = query.order_by(ServiceListing.price.desc().nulls_last())
        elif sort_by == "popular":
            query = query.order_by(ServiceListing.views_count.desc(), ServiceListing.created_at.desc())
        else:  # newest
            query = query.order_by(ServiceListing.created_at.desc())

        total = query.count()
        listings = query.offset(skip).limit(limit).all()

        items = [build_listing_dict(l) for l in listings]
        return success_response("Listings fetched successfully.", {"items": items, "total": total}, 200)

    except Exception as e:
        logger.error(f"Error searching listings: {str(e)}")
        return error_response(str(e), None, 500)


@router.get("/my/listings")
def get_my_agency_listings(
    status: Optional[str] = Query(None, description="draft, published, paused, archived"),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db_global),
):
    user_id = current_user.get("id")
    try:
        agency = db.query(AgencyProfile).filter(AgencyProfile.user_id == user_id).first()
        if not agency:
            return error_response("No agency profile found.", None, 404)

        query = db.query(ServiceListing).filter(ServiceListing.agency_id == agency.id)
        if status:
            query = query.filter(ServiceListing.status == status.lower())

        total = query.count()
        listings = query.order_by(desc(ServiceListing.created_at)).offset(skip).limit(limit).all()

        items = [build_listing_dict(l) for l in listings]
        return success_response("Agency listings fetched.", {"items": items, "total": total}, 200)

    except Exception as e:
        logger.error(f"Error fetching agency listings: {str(e)}")
        return error_response(str(e), None, 500)


@router.get("/{listing_id}")
def get_listing_detail(
    listing_id: int,
    db: Session = Depends(get_db_global),
):
    """
    Public listing detail page (Spec 9.5).
    Increments view count and provides complete pricing breakdown.
    """
    try:
        listing = db.query(ServiceListing).filter(ServiceListing.id == listing_id).first()
        if not listing or listing.status not in ["published", "paused"]:
            return error_response("Service listing not found or unavailable.", None, 404)

        # Increment view count
        listing.views_count += 1
        db.commit()

        return success_response("Service detail fetched.", build_listing_dict(listing), 200)

    except Exception as e:
        db.rollback()
        logger.error(f"Error getting listing {listing_id}: {str(e)}")
        return error_response(str(e), None, 500)


@router.put("/{listing_id}")
def update_listing(
    listing_id: int,
    req: ListingUpdate,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db_global),
):
    user_id = current_user.get("id")
    try:
        agency = db.query(AgencyProfile).filter(AgencyProfile.user_id == user_id).first()
        if not agency:
            return error_response("No agency profile found.", None, 403)

        listing = db.query(ServiceListing).filter(
            ServiceListing.id == listing_id,
            ServiceListing.agency_id == agency.id
        ).first()
        if not listing:
            return error_response("Listing not found or access denied.", None, 404)

        if req.category_id is not None:
            cat = db.query(ServiceCategory).filter(ServiceCategory.id == req.category_id, ServiceCategory.is_active.is_(True)).first()
            if not cat:
                return error_response("Invalid or inactive category.", None, 400)
            listing.category_id = req.category_id

        if req.title is not None: listing.title = req.title
        if req.summary is not None: listing.summary = req.summary
        if req.full_description is not None: listing.full_description = req.full_description
        if req.service_style is not None: listing.service_style = req.service_style.lower()
        if req.included_work is not None: listing.included_work = req.included_work
        if req.exclusions is not None: listing.exclusions = req.exclusions
        if req.images is not None: listing.images = req.images
        if req.pricing_model is not None: listing.pricing_model = req.pricing_model.lower()
        if req.price is not None: listing.price = req.price
        if req.currency is not None: listing.currency = req.currency.upper()
        if req.unit is not None: listing.unit = req.unit
        if req.additional_fees is not None: listing.additional_fees = req.additional_fees.model_dump()
        if req.estimated_duration is not None: listing.estimated_duration = req.estimated_duration
        if req.availability is not None: listing.availability = req.availability
        if req.service_area is not None: listing.service_area = req.service_area
        if req.qualifications_required is not None: listing.qualifications_required = req.qualifications_required
        if req.cancellation_terms is not None: listing.cancellation_terms = req.cancellation_terms

        db.commit()
        db.refresh(listing)
        logger.info(f"Listing updated: id={listing.id} by agency {agency.id}")
        return success_response("Listing updated successfully.", build_listing_dict(listing), 200)

    except Exception as e:
        db.rollback()
        logger.error(f"Error updating listing: {str(e)}")
        return error_response(str(e), None, 500)


@router.patch("/{listing_id}/status")
def update_listing_status(
    listing_id: int,
    req: ListingStatusUpdate,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db_global),
):
    """
    Agency provider actions: publish, pause, archive, or draft (Spec 9.8).
    """
    user_id = current_user.get("id")
    try:
        agency = db.query(AgencyProfile).filter(AgencyProfile.user_id == user_id).first()
        if not agency:
            return error_response("No agency profile found.", None, 403)

        listing = db.query(ServiceListing).filter(
            ServiceListing.id == listing_id,
            ServiceListing.agency_id == agency.id
        ).first()
        if not listing:
            return error_response("Listing not found or access denied.", None, 404)

        new_status = req.status.lower()
        allowed_transitions = ["draft", "published", "paused", "archived"]
        if new_status not in allowed_transitions:
            return error_response(f"Invalid status. Must be one of: {allowed_transitions}", None, 400)

        listing.status = new_status
        db.commit()
        logger.info(f"Listing {listing.id} status changed to '{new_status}' by agency {agency.id}")
        return success_response(f"Listing status updated to '{new_status}'.", {"id": listing.id, "status": listing.status}, 200)

    except Exception as e:
        db.rollback()
        logger.error(f"Error changing listing status: {str(e)}")
        return error_response(str(e), None, 500)
