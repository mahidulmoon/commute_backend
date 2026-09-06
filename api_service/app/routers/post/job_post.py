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
def get_my_job_posts(user_data = Depends(get_agent_user), db: Session = Depends(get_db_global)):
    try:
        job = (
            db.query(JobPost)
            .filter(
                JobPost.owner_id == user_data.get("id"),
            )
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

@router.put("/update_job_post/{job_id}")
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