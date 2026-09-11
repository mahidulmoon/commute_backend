import math
from fastapi import APIRouter, Depends, Query
from fastapi.responses import JSONResponse
from app.utils.auth_validation import get_current_user, get_agent_user
from app.utils.response import success_response, error_response
from app.database import get_db_global
from sqlalchemy.orm import Session
from app.schema.jobpostschema import *
from app.models.job_post import JobPost
from fastapi.encoders import jsonable_encoder
from sqlalchemy import select, and_
from typing import Optional
from datetime import datetime, timezone, timedelta
from app.logger import logger

router = APIRouter(prefix="/job_post",tags=["Job post"],)


def calculate_haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    Calculate the great circle distance between two points
    on the earth (specified in decimal degrees).
    Returns distance in kilometers.
    """
    R = 6371.0  # Earth radius in kilometers

    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)

    a = (
        math.sin(delta_phi / 2.0) ** 2
        + math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2.0) ** 2
    )
    a = min(1.0, max(0.0, a))
    c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))

    return R * c


@router.post("/create_job_post")
def create_job_post(data: JobPostCreate, db: Session = Depends(get_db_global),user_data = Depends(get_agent_user)):
    try:

        job = JobPost(
            owner_id=user_data.get("id"),
            title=data.title,
            description=data.description,
            location=data.location,
            latitude=data.latitude,
            longitude=data.longitude,
            employment_type=data.employment_type,
            salary=data.salary,
            status=JobStatus.DRAFT,
        )

        db.add(job)
        db.commit()
        db.refresh(job)

        logger.info(f"Job post created successfully with id {job.id} by agent user {user_data.get('id')}.")
        return success_response("Post creation successful.",None,201)

    except Exception as e:
        db.rollback()
        logger.error(f"Error creating job post for agent user {user_data.get('id')}: {str(e)}")
        return error_response(str(e),None,500)

@router.get("/get_job_post_by_id")
def get_job_post_by_id(job_id: int, user_data = Depends(get_agent_user), db: Session = Depends(get_db_global)):
    try:
        job = (
            db.query(JobPost)
            .filter(
                JobPost.id == job_id,
                JobPost.owner_id == user_data.get("id"),
            )
            .first()
        )

        if not job:
            logger.warning(f"Job post {job_id} not found for agent user {user_data.get('id')}.")
            return error_response("Job not found",None,400)


        return success_response("Job fetch successful.",jsonable_encoder(job),200)
    except Exception as e:
        logger.error(f"Error fetching job post {job_id} for agent user {user_data.get('id')}: {str(e)}")
        return error_response(str(e),None,500)

@router.get("/get_my_job_posts")
def get_my_job_posts(
    skip: int = Query(default=0, ge=0, description="Number of records to skip"),
    limit: int = Query(default=10, ge=1, le=100, description="Max number of records to return"),
    user_data = Depends(get_agent_user), db: Session = Depends(get_db_global)):
    try:
        job = (
            db.query(JobPost)
            .filter(
                JobPost.owner_id == user_data.get("id"),
            ).offset(skip).limit(limit)
            .all()
        )

        if not job:
            logger.warning(f"No job posts found for agent user {user_data.get('id')}.")
            return error_response("Job not found",None,400)


        return success_response("Job fetch successful.",jsonable_encoder(job),200)
    except Exception as e:
        logger.error(f"Error fetching job posts for agent user {user_data.get('id')}: {str(e)}")
        return error_response(str(e),None,500)


@router.get("/publish_job")
def publish_job(job_id: int, db: Session = Depends(get_db_global),user_data = Depends(get_agent_user)):
    try:
        job = (
            db.query(JobPost)
            .filter(
                JobPost.id == job_id,
                JobPost.owner_id == user_data.get("id"),
            )
            .first()
        )

        if not job:
            logger.warning(f"Publish job failed: Job post {job_id} not found for agent user {user_data.get('id')}.")
            return error_response("Job not found",None,404)

        if job.status != JobStatus.DRAFT:
            logger.warning(f"Publish job failed: Job post {job_id} is in status '{job.status}', only draft jobs can be published.")
            return error_response("Only draft jobs can be published",None,400)

        job.status = JobStatus.PUBLISHED
        job.published_at = datetime.now(timezone.utc)

        db.commit()
        db.refresh(job)

        logger.info(f"Job post {job_id} successfully published by agent user {user_data.get('id')}.")
        return success_response("Job Successfully Published",None,200)
    except Exception as e:
        db.rollback()
        logger.error(f"Error publishing job post {job_id}: {str(e)}")
        return error_response(str(e),None,500)

@router.get("/close_job")
def close_job(job_id: int, db: Session = Depends(get_db_global),user_data = Depends(get_agent_user)):
    try:
        job = (
            db.query(JobPost)
            .filter(
                JobPost.id == job_id,
                JobPost.owner_id == user_data.get("id"),
            )
            .first()
        )

        if not job:
            logger.warning(f"Close job failed: Job post {job_id} not found for agent user {user_data.get('id')}.")
            return error_response("Job not found",None,404)

        if job.status != JobStatus.PUBLISHED:
            logger.warning(f"Close job failed: Job post {job_id} is in status '{job.status}', only published jobs can be closed.")
            return error_response("Only published jobs can be closed",None,400)

        job.status = JobStatus.CLOSED
        job.closed_at = datetime.now(timezone.utc)

        db.commit()
        db.refresh(job)

        logger.info(f"Job post {job_id} successfully closed by agent user {user_data.get('id')}.")
        return success_response("Job Successfully closed",None,200)
    except Exception as e:
        db.rollback()
        logger.error(f"Error closing job post {job_id}: {str(e)}")
        return error_response(str(e),None,500)

@router.get("/archive_job")
def archive_job(job_id: int, db: Session = Depends(get_db_global),user_data = Depends(get_agent_user)):
    try:
        job = (
            db.query(JobPost)
            .filter(
                JobPost.id == job_id,
                JobPost.owner_id == user_data.get("id"),
            )
            .first()
        )

        if not job:
            logger.warning(f"Archive job failed: Job post {job_id} not found for agent user {user_data.get('id')}.")
            return error_response("Job not found",None,404)

        if job.status != JobStatus.CLOSED:
            logger.warning(f"Archive job failed: Job post {job_id} is in status '{job.status}', only closed jobs can be archived.")
            return error_response("Only closed jobs can be archived",None,400)

        job.status = JobStatus.ARCHIVED
        job.archived_at = datetime.now(timezone.utc)

        db.commit()
        db.refresh(job)

        logger.info(f"Job post {job_id} successfully archived by agent user {user_data.get('id')}.")
        return success_response("Job Successfully archived",None,200)
    except Exception as e:
        db.rollback()
        logger.error(f"Error archiving job post {job_id}: {str(e)}")
        return error_response(str(e),None,500)

@router.put("/update_job_post/{job_id}/")
def update_job_post(
    job_id: int,
    data: JobPostCreate,
    db: Session = Depends(get_db_global),
    user_data=Depends(get_agent_user)
):
    try:
        job = db.query(JobPost).filter(
            JobPost.id == job_id,
            JobPost.owner_id == user_data.get("id")
        ).first()

        if not job:
            logger.warning(f"Update job failed: Job post {job_id} not found or user {user_data.get('id')} is not the owner.")
            return error_response(
                "Job post not found or you are not the owner.",
                None,
                404
            )

        job.title = data.title
        job.description = data.description
        job.location = data.location
        if data.latitude is not None:
            job.latitude = data.latitude
        if data.longitude is not None:
            job.longitude = data.longitude
        job.employment_type = data.employment_type
        job.salary = data.salary

        db.commit()
        db.refresh(job)

        logger.info(f"Job post {job_id} successfully updated by agent user {user_data.get('id')}.")
        return success_response(
            "Job post updated successfully.",
            None,
            200
        )

    except Exception as e:
        db.rollback()
        logger.error(f"Error updating job post {job_id}: {str(e)}")
        return error_response(str(e), None, 500)


@router.get("/get_nearby_jobs")
def get_jobs_by_distance(
    longitude: float = Query(..., description="User's current longitude (-180 to 180)"),
    latitude: Optional[float] = Query(None, description="User's current latitude (-90 to 90)"),
    lattitude: Optional[float] = Query(None, description="User's current latitude (alias)"),
    distance: float = Query(..., gt=0, description="Search distance radius in kilometers"),
    status: Optional[str] = Query(default="published", description="Job status filter (default: 'published', pass 'all' for all statuses)"),
    skip: int = Query(default=0, ge=0, description="Number of records to skip"),
    limit: int = Query(default=20, ge=1, le=100, description="Max number of records to return"),
    db: Session = Depends(get_db_global),
    user_data = Depends(get_current_user),
):
    try:
        user_lat = latitude if latitude is not None else lattitude

        if user_lat is None:
            return error_response(
                "Latitude must be provided (either 'latitude' or 'lattitude').",
                None,
                400,
            )

        if not (-90.0 <= user_lat <= 90.0):
            return error_response(
                "Latitude must be between -90 and 90 degrees.",
                None,
                400,
            )

        if not (-180.0 <= longitude <= 180.0):
            return error_response(
                "Longitude must be between -180 and 180 degrees.",
                None,
                400,
            )

        # Approximate bounding box to filter candidates at the database level:
        # 1 deg latitude ≈ 111.045 km
        lat_delta = distance / 111.045
        cos_lat = max(abs(math.cos(math.radians(user_lat))), 0.0001)
        lon_delta = distance / (111.045 * cos_lat)

        min_lat = user_lat - lat_delta
        max_lat = user_lat + lat_delta
        min_lon = longitude - lon_delta
        max_lon = longitude + lon_delta

        query = db.query(JobPost).filter(
            JobPost.latitude.isnot(None),
            JobPost.longitude.isnot(None),
            JobPost.latitude.between(min_lat, max_lat),
            JobPost.longitude.between(min_lon, max_lon),
        )

        if status and status.lower() != "all":
            query = query.filter(JobPost.status == status.lower())

        candidates = query.all()

        matched_jobs = []
        for job in candidates:
            dist_km = calculate_haversine_distance(
                user_lat, longitude, job.latitude, job.longitude
            )
            if dist_km <= distance:
                job_dict = jsonable_encoder(job)
                job_dict["distance_km"] = round(dist_km, 2)
                matched_jobs.append(job_dict)

        # Sort closest first
        matched_jobs.sort(key=lambda x: x["distance_km"])
        total_matched = len(matched_jobs)

        paginated_jobs = matched_jobs[skip : skip + limit]

        response_data = {
            "items": paginated_jobs,
            "total": total_matched,
            "user_location": {
                "latitude": user_lat,
                "longitude": longitude,
            },
            "search_radius_km": distance,
        }

        logger.info(
            f"Distance search by user {user_data.get('id') if user_data else 'unknown'}: "
            f"found {total_matched} jobs within {distance}km of ({user_lat}, {longitude})."
        )
        return success_response("Jobs fetched successfully.", response_data, 200)

    except Exception as e:
        logger.error(f"Error fetching jobs by distance: {str(e)}")
        return error_response(str(e), None, 500)