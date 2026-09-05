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
