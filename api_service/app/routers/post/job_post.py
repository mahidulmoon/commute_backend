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

router = APIRouter(prefix="/job_post",tags=["Job post"],)


@router.post("/create_job_post")
def create_job_post(data: JobPostCreate, db: Session = Depends(get_db_global),user_data = Depends(get_agent_user)):
    try:

        job = JobPost(
            owner_id=user_data.get("id"),
            title=data.title,
            description=data.description,
            location=data.location,
            employment_type=data.employment_type,
            salary=data.salary,
            status=JobStatus.DRAFT,
        )

        db.add(job)
        db.commit()
        db.refresh(job)

        return success_response("Post creation successful.",None,201)

    except Exception as e:
        return error_response(str(e),None,500)

@router.get("/get_job_post_by_id")
def get_job_post_by_id(job_id: int, user_data = Depends(get_agent_user), db: Session = Depends(get_db_global)):

    job = (
        db.query(JobPost)
        .filter(
            JobPost.id == job_id,
            JobPost.owner_id == user_data.get("id"),
        )
        .first()
    )

    if not job:
        return error_response("Job not found",None,400)


    return success_response("Job fetch successful.",jsonable_encoder(job),200)

@router.get("/get_my_job_posts")
def get_my_job_posts(user_data = Depends(get_agent_user), db: Session = Depends(get_db_global)):

    job = (
        db.query(JobPost)
        .filter(
            JobPost.owner_id == user_data.get("id"),
        )
        .all()
    )

    if not job:
        return error_response("Job not found",None,400)


    return success_response("Job fetch successful.",jsonable_encoder(job),200)


@router.get("/publish_job")
def publish_job(job_id: int, db: Session = Depends(get_db_global),user_data = Depends(get_agent_user)):

    job = (
        db.query(JobPost)
        .filter(
            JobPost.id == job_id,
            JobPost.owner_id == user_data.get("id"),
        )
        .first()
    )

    if job.status != JobStatus.DRAFT:

        return error_response("Only draft jobs can be published",None,400)

    job.status = JobStatus.PUBLISHED
    job.published_at = datetime.now(timezone.utc)

    db.commit()
    db.refresh(job)

    return success_response("Job Successfully Published",None,200)

@router.get("/close_job")
def close_job(job_id: int, db: Session = Depends(get_db_global),user_data = Depends(get_agent_user)):

    job = (
        db.query(JobPost)
        .filter(
            JobPost.id == job_id,
            JobPost.owner_id == user_data.get("id"),
        )
        .first()
    )

    if job.status != JobStatus.PUBLISHED:

        return error_response("Only draft jobs can be closeed",None,400)

    job.status = JobStatus.CLOSED
    job.closed_at = datetime.now(timezone.utc)

    db.commit()
    db.refresh(job)

    return success_response("Job Successfully closeed",None,200)

@router.get("/archive_job")
def archive_job(job_id: int, db: Session = Depends(get_db_global),user_data = Depends(get_agent_user)):

    job = (
        db.query(JobPost)
        .filter(
            JobPost.id == job_id,
            JobPost.owner_id == user_data.get("id"),
        )
        .first()
    )

    if job.status != JobStatus.CLOSED:

        return error_response("Only draft jobs can be archived",None,400)

    job.status = JobStatus.ARCHIVED
    job.archived_at = datetime.now(timezone.utc)

    db.commit()
    db.refresh(job)

    return success_response("Job Successfully archived",None,200)