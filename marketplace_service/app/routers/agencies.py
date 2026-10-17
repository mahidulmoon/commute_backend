import re
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import desc

from app.database import get_db_global
from app.models.agency import AgencyProfile
from app.models.listing import ServiceListing
from app.models.enquiry import ServiceEnquiry
from app.schema.agency_schema import (
    AgencyOnboardingRequest,
    AgencyUpdateRequest,
    AgencyResponse,
    AgencyDashboardResponse,
)
from app.utils.auth_validation import get_current_user
from app.utils.response import success_response, error_response
from app.logger import logger

router = APIRouter(prefix="/agencies", tags=["Agencies"])


def slugify(text: str) -> str:
    text = text.lower().strip()
    text = re.sub(r"[^\w\s-]", "", text)
    return re.sub(r"[-\s]+", "-", text)


def calculate_profile_completion(agency: AgencyProfile) -> int:
    score = 0
    total_weights = 100
    if agency.business_name: score += 15
    if agency.short_summary: score += 15
    if agency.full_description: score += 10
    if agency.logo_url: score += 10
    if agency.category_ids: score += 15
    if agency.service_areas and (agency.service_areas.get("cities") or agency.service_areas.get("postcodes") or agency.service_areas.get("remote_online")): score += 15
    if agency.contact_email or agency.contact_phone: score += 10
    if agency.website or agency.opening_hours: score += 5
    if agency.qualifications: score += 5
    return min(score, 100)


@router.post("/onboard")
def onboard_agency(
    req: AgencyOnboardingRequest,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db_global),
):
    """
    Onboard and create an Agency / Provider profile (Spec 9.1).
    Starts in 'pending' status awaiting administrative verification.
    """
    user_id = current_user.get("id")

    try:
        existing = db.query(AgencyProfile).filter(AgencyProfile.user_id == user_id).first()
        if existing:
            return error_response("An agency profile already exists for this user account.", None, 400)

        base_slug = slugify(req.business_name)
        slug = base_slug
        counter = 1
        while db.query(AgencyProfile).filter(AgencyProfile.slug == slug).first():
            slug = f"{base_slug}-{counter}"
            counter += 1

        agency = AgencyProfile(
            user_id=user_id,
            business_name=req.business_name,
            slug=slug,
            logo_url=req.logo_url,
            short_summary=req.short_summary,
            full_description=req.full_description,
            category_ids=req.category_ids,
            service_areas=req.service_areas.model_dump(),
            contact_email=req.contact_email or current_user.get("email"),
            contact_phone=req.contact_phone,
            contact_methods=req.contact_methods.model_dump() if req.contact_methods else {"allow_enquiry": True},
            website=req.website,
            opening_hours=req.opening_hours or {},
            languages=req.languages or ["English"],
            qualifications=req.qualifications or [],
            status="pending",
            is_active=True,
        )

        db.add(agency)
        db.commit()
        db.refresh(agency)

        logger.info(f"Agency profile created: '{agency.business_name}' id={agency.id} by user {user_id}")
        return success_response(
            "Agency profile submitted successfully. It is now pending review.",
            {
                "id": agency.id,
                "business_name": agency.business_name,
                "slug": agency.slug,
                "status": agency.status,
            },
            201
        )

    except Exception as e:
        db.rollback()
        logger.error(f"Error onboarding agency for user {user_id}: {str(e)}")
        return error_response(str(e), None, 500)


@router.get("/me")
def get_my_agency_profile(
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db_global),
):
    user_id = current_user.get("id")
    try:
        agency = db.query(AgencyProfile).filter(AgencyProfile.user_id == user_id).first()
        if not agency:
            return error_response("No agency profile found for this user.", None, 404)

        data = {
            "id": agency.id,
            "user_id": agency.user_id,
            "business_name": agency.business_name,
            "slug": agency.slug,
            "logo_url": agency.logo_url,
            "short_summary": agency.short_summary,
            "full_description": agency.full_description,
            "category_ids": agency.category_ids,
            "service_areas": agency.service_areas,
            "contact_email": agency.contact_email,
            "contact_phone": agency.contact_phone,
            "contact_methods": agency.contact_methods,
            "website": agency.website,
            "opening_hours": agency.opening_hours,
            "languages": agency.languages,
            "qualifications": agency.qualifications,
            "status": agency.status,
            "is_active": agency.is_active,
            "completion_percentage": calculate_profile_completion(agency),
            "created_at": agency.created_at.isoformat() if agency.created_at else None,
            "updated_at": agency.updated_at.isoformat() if agency.updated_at else None,
        }
        return success_response("Agency profile fetched.", data, 200)

    except Exception as e:
        logger.error(f"Error fetching agency profile for user {user_id}: {str(e)}")
        return error_response(str(e), None, 500)


@router.put("/me")
def update_my_agency_profile(
    req: AgencyUpdateRequest,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db_global),
):
    user_id = current_user.get("id")
    try:
        agency = db.query(AgencyProfile).filter(AgencyProfile.user_id == user_id).first()
        if not agency:
            return error_response("No agency profile found for this user.", None, 404)

        if req.business_name is not None:
            agency.business_name = req.business_name
        if req.logo_url is not None:
            agency.logo_url = req.logo_url
        if req.short_summary is not None:
            agency.short_summary = req.short_summary
        if req.full_description is not None:
            agency.full_description = req.full_description
        if req.category_ids is not None:
            agency.category_ids = req.category_ids
        if req.service_areas is not None:
            agency.service_areas = req.service_areas.model_dump()
        if req.contact_email is not None:
            agency.contact_email = req.contact_email
        if req.contact_phone is not None:
            agency.contact_phone = req.contact_phone
        if req.contact_methods is not None:
            agency.contact_methods = req.contact_methods.model_dump()
        if req.website is not None:
            agency.website = req.website
        if req.opening_hours is not None:
            agency.opening_hours = req.opening_hours
        if req.languages is not None:
            agency.languages = req.languages
        if req.qualifications is not None:
            agency.qualifications = req.qualifications

        db.commit()
        db.refresh(agency)
        logger.info(f"Agency profile updated for id={agency.id}")
        return success_response("Agency profile updated successfully.", {"id": agency.id, "business_name": agency.business_name}, 200)

    except Exception as e:
        db.rollback()
        logger.error(f"Error updating agency profile: {str(e)}")
        return error_response(str(e), None, 500)


@router.get("/me/dashboard")
def get_agency_dashboard(
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db_global),
):
    """
    Agency Dashboard (Spec 9.8):
    - Profile completion & verification status
    - Listings breakdown: total, published, draft, paused, archived
    - Enquiries pipeline: new, in progress, completed
    - Recent enquiries
    """
    user_id = current_user.get("id")
    try:
        agency = db.query(AgencyProfile).filter(AgencyProfile.user_id == user_id).first()
        if not agency:
            return error_response("No agency profile found for this user. Please complete onboarding first.", None, 404)

        # Listings breakdown
        listings = db.query(ServiceListing).filter(ServiceListing.agency_id == agency.id).all()
        total_listings = len(listings)
        published_listings = sum(1 for l in listings if l.status == "published")
        draft_listings = sum(1 for l in listings if l.status == "draft")
        paused_listings = sum(1 for l in listings if l.status == "paused")
        archived_listings = sum(1 for l in listings if l.status in ["archived", "closed"])

        # Enquiries breakdown
        enquiries = db.query(ServiceEnquiry).filter(ServiceEnquiry.agency_id == agency.id).order_by(desc(ServiceEnquiry.created_at)).all()
        total_enquiries = len(enquiries)
        new_enquiries = sum(1 for e in enquiries if e.status == "submitted")
        in_progress_enquiries = sum(1 for e in enquiries if e.status in ["viewed", "provider_responded", "quote_provided", "accepted"])
        completed_enquiries = sum(1 for e in enquiries if e.status == "completed")

        recent = [
            {
                "id": e.id,
                "service_id": e.service_id,
                "service_title": e.service.title if e.service else None,
                "customer_id": e.customer_id,
                "location": e.location,
                "status": e.status,
                "quote_amount": float(e.quote_amount) if e.quote_amount else None,
                "created_at": e.created_at.isoformat(),
            }
            for e in enquiries[:5]
        ]

        dashboard_data = {
            "agency_id": agency.id,
            "business_name": agency.business_name,
            "profile_completion_percentage": calculate_profile_completion(agency),
            "status": agency.status,
            "is_verified": agency.status == "verified",
            "total_listings": total_listings,
            "published_listings": published_listings,
            "draft_listings": draft_listings,
            "paused_listings": paused_listings,
            "archived_listings": archived_listings,
            "total_enquiries": total_enquiries,
            "new_enquiries": new_enquiries,
            "in_progress_enquiries": in_progress_enquiries,
            "completed_enquiries": completed_enquiries,
            "recent_enquiries": recent,
        }
        return success_response("Agency dashboard data fetched successfully.", dashboard_data, 200)

    except Exception as e:
        logger.error(f"Error fetching agency dashboard: {str(e)}")
        return error_response(str(e), None, 500)


@router.get("/{agency_id_or_slug}")
def get_public_agency_profile(
    agency_id_or_slug: str,
    db: Session = Depends(get_db_global),
):
    """
    Public view of an agency / provider profile.
    Hides private contact details unless explicitly permitted (Spec 9.1).
    """
    try:
        if agency_id_or_slug.isdigit():
            agency = db.query(AgencyProfile).filter(AgencyProfile.id == int(agency_id_or_slug)).first()
        else:
            agency = db.query(AgencyProfile).filter(AgencyProfile.slug == agency_id_or_slug).first()

        if not agency or not agency.is_active or agency.status in ["rejected", "suspended"]:
            return error_response("Provider profile not found or inactive.", None, 404)

        contact_methods = agency.contact_methods or {}
        public_email = agency.contact_email if contact_methods.get("show_email_publicly") else None
        public_phone = agency.contact_phone if contact_methods.get("show_phone_publicly") else None

        data = {
            "id": agency.id,
            "business_name": agency.business_name,
            "slug": agency.slug,
            "logo_url": agency.logo_url,
            "short_summary": agency.short_summary,
            "full_description": agency.full_description,
            "category_ids": agency.category_ids,
            "service_areas": agency.service_areas,
            "contact_email": public_email,
            "contact_phone": public_phone,
            "allow_enquiry": contact_methods.get("allow_enquiry", True),
            "website": agency.website,
            "opening_hours": agency.opening_hours,
            "languages": agency.languages,
            "qualifications": agency.qualifications,
            "status": agency.status,
            "is_verified": agency.status == "verified",
        }
        return success_response("Provider profile fetched.", data, 200)

    except Exception as e:
        logger.error(f"Error fetching public agency profile: {str(e)}")
        return error_response(str(e), None, 500)
