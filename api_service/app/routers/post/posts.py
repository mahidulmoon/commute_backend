from fastapi import APIRouter, Depends, Query
from fastapi.responses import JSONResponse
from app.utils.auth_validation import get_current_user
from app.utils.response import success_response, error_response
from app.database import get_db_global
from sqlalchemy.orm import Session
from app.schema.postschema import *
from app.models.posts import PostModel
from fastapi.encoders import jsonable_encoder
from sqlalchemy import select, and_
from typing import Optional
from app.logger import logger

router = APIRouter()



@router.post("/create_post")
def create_post(post_data : PostCreate, user_data = Depends(get_current_user),db: Session = Depends(get_db_global)):
    try:
        post = PostModel(
            user_id=user_data.get("id"),
            content=post_data.content,
            group_id = post_data.group_id
        )

        db.add(post)
        db.commit()
        db.refresh(post)
        logger.info(f"Post created successfully with id {post.id} by user {user_data.get('id')}.")
        return success_response("Post creation successful.",None,201)
    except Exception as e:
        db.rollback()
        logger.error(f"Error creating post for user {user_data.get('id')}: {str(e)}")
        return error_response(str(e),None,400)


@router.get("/get_my_post",response_model=MyPostsResponse)
def get_my_post(
    skip: int = Query(default=0, ge=0, description="Number of records to skip"),
    limit: int = Query(default=10, ge=1, le=100, description="Max number of records to return"),
    user_data = Depends(get_current_user),db: Session = Depends(get_db_global)
    ):
    try:
        posts = (
            db.query(PostModel)
            .filter(
                PostModel.user_id == user_data.get("id"),
                PostModel.is_deleted.is_(False),
            )
            .order_by(
                PostModel.created_at.desc(),
                PostModel.id.desc(),
            ).offset(skip).limit(limit)
            .all()
        )

        post_response = {
            "items": jsonable_encoder(posts),
            "total": len(posts),
        }
        return success_response("Post fetched successfully.",post_response,200)
    except Exception as e:
        logger.error(f"Error fetching posts for user {user_data.get('id')}: {str(e)}")
        return error_response(str(e),None,400)

@router.get("/get_my_post_by_group",response_model=MyPostsResponse)
def get_my_post_by_group(
    skip: int = Query(default=0, ge=0, description="Number of records to skip"),
    limit: int = Query(default=10, ge=1, le=100, description="Max number of records to return"),
    user_data = Depends(get_current_user),db: Session = Depends(get_db_global)
    ):
    try:
        if not user_data.get("group_id"):
            logger.warning("Group is not assigned for this user yet.")
            return error_response("Group is not assigned for this user yet.",None,400)
        
        posts = (
            db.query(PostModel)
            .filter(
                PostModel.group_id == user_data.get("group_id"),
                PostModel.is_deleted.is_(False),
            )
            .order_by(
                PostModel.created_at.desc(),
                PostModel.id.desc(),
            ).offset(skip).limit(limit)
            .all()
        )

        post_response = {
            "items": jsonable_encoder(posts),
            "total": len(posts),
        }
        return success_response("Post fetched successfully.",post_response,200)
    except Exception as e:
        logger.error(f"Error fetching posts for user {user_data.get('id')}: {str(e)}")
        return error_response(str(e),None,400)


# --- Search Endpoint ---
@router.get("/search", response_model=MyPostsResponse)
def search_posts(
    q: Optional[str] = Query(default=None, description="Search term for post content"),
    skip: int = Query(default=0, ge=0, description="Number of records to skip"),
    limit: int = Query(default=10, ge=1, le=100, description="Max number of records to return"),
    db: Session = Depends(get_db_global)  # Replace with your actual DB session dependency
):
    try:
        # 1. Base query ordering by latest posts first
        stmt = select(PostModel).order_by(PostModel.created_at.desc())
        
        # 2. Dynamic filters list
        filters = []
        
            
        # Text search on 'content' (case-insensitive)
        if q:
            filters.append(PostModel.content.ilike(f"%{q}%"))
            
            
        # 3. Apply filters, pagination, and execute
        if filters:
            stmt = stmt.where(and_(*filters))
            
        stmt = stmt.offset(skip).limit(limit)
        
        results = db.scalars(stmt).all()

        post_response = {
            "items": jsonable_encoder(results),
            "total": len(results),
        }
        return success_response("Post fetched successfully.",post_response,200)
    except Exception as e:
        logger.error(f"Error searching posts with query '{q}': {str(e)}")
        return error_response(str(e),None,400)