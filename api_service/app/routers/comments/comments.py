from fastapi import APIRouter, Depends

from sqlalchemy.orm import Session

from app.database import get_db_global
from app.models.comments import CommentModel
from app.models.posts import PostModel
from app.schema.commentschema import (
    CommentCreate,
    CommentResponse,
)
from app.utils.auth_validation import get_current_user
from app.utils.response import success_response, error_response
from app.utils.notification_client import send_notification
from app.logger import logger


router = APIRouter(
    prefix="/comments",
    tags=["Comments"],
)

@router.post("/create_comment")
def create_comment(
    data: CommentCreate,
    user_data=Depends(get_current_user),
    db: Session = Depends(get_db_global),
):
    try:
        user_id = user_data.get("id")

        # Check post exists
        post = (
            db.query(PostModel)
            .filter(
                PostModel.id == data.post_id,
                PostModel.is_deleted.is_(False),
            )
            .first()
        )

        if not post:
            logger.warning(f"Comment creation failed: Post {data.post_id} not found.")
            return error_response(
                "Post not found.",
                None,
                404,
            )

        # If this is a reply, check parent comment
        if data.parent_id is not None:

            parent_comment = (
                db.query(CommentModel)
                .filter(
                    CommentModel.id == data.parent_id,
                    CommentModel.post_id == data.post_id,
                    CommentModel.is_deleted.is_(False),
                )
                .first()
            )

            if not parent_comment:
                logger.warning(
                    f"Comment creation failed: Parent comment {data.parent_id} not found on post {data.post_id}."
                )
                return error_response(
                    "Parent comment not found.",
                    None,
                    404,
                )

        comment = CommentModel(
            post_id=data.post_id,
            user_id=user_id,
            parent_id=data.parent_id,
            content=data.content,
        )

        db.add(comment)
        db.commit()
        db.refresh(comment)

        logger.info(
            f"Comment {comment.id} created successfully on post {data.post_id} by user {user_id}."
        )

        # Notify post owner if commenter is someone else
        if post.user_id != user_id:
            actor_name = user_data.get("username") or f"User {user_id}"
            comment_snippet = data.content[:60] + "..." if len(data.content) > 60 else data.content
            send_notification(
                recipient_id=post.user_id,
                actor_id=user_id,
                notif_type="post_comment",
                title="New Comment on Your Post",
                body=f"{actor_name} commented: \"{comment_snippet}\"",
                link=f"/posts/{data.post_id}",
                data={"post_id": data.post_id, "comment_id": comment.id},
            )

        return success_response(
            "Comment created successfully.",
            None,
            201,
        )

    except Exception as e:
        db.rollback()
        logger.error(
            f"Error creating comment on post {data.post_id} by user {user_data.get('id') if user_data else 'unknown'}: {str(e)}"
        )

        return error_response(
            str(e),
            None,
            400,
        )

