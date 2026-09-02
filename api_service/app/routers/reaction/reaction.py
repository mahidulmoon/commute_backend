from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db_global
from app.models.posts import PostModel
from app.models.reactions import ReactionModel
from app.schema.reactionschema import (
    ReactionCreate,
    ReactionResponse,
)
from app.utils.auth_validation import get_current_user
from app.utils.response import success_response, error_response


router = APIRouter(
    prefix="/reactions",
    tags=["Reactions"],
)

ALLOWED_REACTIONS = {
    "like",
    "love",
    "haha",
    "wow",
    "sad",
    "angry",
}


@router.post("/add_reaction")
def add_reaction(
    data: ReactionCreate,
    user_data=Depends(get_current_user),
    db: Session = Depends(get_db_global),
):
    try:
        user_id = user_data.get("id")

        reaction_type = data.reaction_type.strip().lower()

        if reaction_type not in ALLOWED_REACTIONS:
            return error_response(
                "Invalid reaction type.",
                {
                    "allowed_reactions": list(ALLOWED_REACTIONS)
                },
                400,
            )

        # Check post
        post = (
            db.query(PostModel)
            .filter(
                PostModel.id == data.post_id,
                PostModel.is_deleted.is_(False),
            )
            .first()
        )

        if not post:
            return error_response(
                "Post not found.",
                None,
                404,
            )

        # Check existing reaction
        reaction = (
            db.query(ReactionModel)
            .filter(
                ReactionModel.post_id == data.post_id,
                ReactionModel.user_id == user_id,
            )
            .first()
        )

        if reaction:

            # User clicked a different reaction
            reaction.reaction_type = reaction_type

            db.commit()
            db.refresh(reaction)

            response = (
                ReactionResponse
                .model_validate(reaction)
                .model_dump()
            )

            return success_response(
                "Reaction updated successfully.",
                response,
                200,
            )

        # No existing reaction
        reaction = ReactionModel(
            post_id=data.post_id,
            user_id=user_id,
            reaction_type=reaction_type,
        )

        db.add(reaction)
        db.commit()
        db.refresh(reaction)

        # response = (
        #     ReactionResponse
        #     .model_validate(reaction)
        #     .model_dump()
        # )

        return success_response(
            "Reaction added successfully.",
            None,
            201,
        )

    except Exception as e:
        db.rollback()

        return error_response(
            str(e),
            None,
            400,
        )