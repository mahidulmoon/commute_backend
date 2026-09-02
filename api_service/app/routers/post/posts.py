from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from app.utils.auth_validation import get_current_user
from app.utils.response import success_response, error_response
from app.database import get_db_global
from sqlalchemy.orm import Session
from app.schema.posts import *
from app.models.posts import PostModel
from fastapi.encoders import jsonable_encoder



router = APIRouter()



@router.post("/create_post")
def create_post(post_data : PostCreate, user_data = Depends(get_current_user),db: Session = Depends(get_db_global)):
    try:
        post = PostModel(
            user_id=user_data.get("id"),
            content=post_data.content,
        )

        db.add(post)
        db.commit()
        db.refresh(post)
        return success_response("Post creation successful.",None,201)
    except Exception as e:
        return error_response(str(e),None,400)


@router.get("/get_my_post",response_model=MyPostsResponse)
def get_my_post(user_data = Depends(get_current_user),db: Session = Depends(get_db_global)):
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
            )
            .all()
        )

        post_response = {
            "items": jsonable_encoder(posts),
            "total": len(posts),
        }
        return success_response("Post fetched successfully.",post_response,200)
    except Exception as e:
        return error_response(str(e),None,400)