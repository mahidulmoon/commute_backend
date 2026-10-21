from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from fastapi.responses import JSONResponse
from pydantic import BaseModel as PydanticBaseModel
from app.database import SessionLocal
from app.utils import response
from app.models.country import Country
from fastapi.encoders import jsonable_encoder
from app.routers.auth.auth_validation import get_current_user
from app.schema.user_profile import CompleteProfileSchema
from app.database import get_db_global
from app.logger import logger
from app.models.user_profile import CompleteProfileModel
from app.models.wo_user import User
from app.producer_push.rabbitmq import producer
import json


class UpdateProfilePicSchema(PydanticBaseModel):
    profile_pic_url: str


router = APIRouter()

@router.get("/get_my_profile_data")
def get_user_profile_info(request_user = Depends(get_current_user), db: Session = Depends(get_db_global)):
    try:
        profile_data = db.query(CompleteProfileModel).filter(
            CompleteProfileModel.user_id == request_user.user_id
            ).first()

        return response.success_response("data successfully fetched.",jsonable_encoder(profile_data),200)
    except Exception as e:
        logger.error(str(e))

        return response.error_response(
            str(e),
            None,
            400,
        )



@router.post("/complete_your_profile")
def complete_user_profile_submission(
    userinput: CompleteProfileSchema,
    request_user=Depends(get_current_user),
    db: Session = Depends(get_db_global),
):
    try:
        producer_msg = {
            "user_id" : request_user.user_id,
            "raw_data" : userinput.model_dump(mode="json"),
            "task" : "post_profile_submission"
        }
        # producer.publish_message(json.dumps(producer_msg))
        producer.publish_message(producer_msg)
        logger.info("producer publish successful.")

        profile = CompleteProfileModel(
            user_id=request_user.user_id,

            address=userinput.address,
            local_area=userinput.local_area,
            dob=userinput.dob,
            national_id=userinput.national_id,
            student_id=userinput.student_id,
            phone_number=userinput.phone_number,

            current_city=userinput.current_city,
            current_state=userinput.current_state,
            current_country_name=userinput.current_country_name,

            interest=userinput.interest,
            hobbies=userinput.hobbies,

            university=userinput.university,
            course=userinput.course,
            level=userinput.level,

            company=userinput.company,
            position=userinput.position,
        )

        db.add(profile)

        # ----------------------------------------------------------------
        # Mirror postcode to the users table so the group engine can read
        # it directly from the User record when allocating groups.
        # ----------------------------------------------------------------
        user_record = db.query(User).filter(
            User.user_id == request_user.user_id
        ).first()

        if user_record:
            user_record.postcode = userinput.postcode
            logger.info(
                f"Postcode '{userinput.postcode}' saved to users table "
                f"for user_id={request_user.user_id}"
            )
        else:
            logger.warning(
                f"User record not found for user_id={request_user.user_id} "
                "while trying to update postcode."
            )

        db.commit()
        db.refresh(profile)

        return response.success_response(
            "data saved successfully",
            None,
            201,
        )

    except Exception as e:
        db.rollback()
        logger.error(str(e))

        return response.error_response(
            str(e),
            None,
            400,
        )


# ---------------------------------------------------------------------------
# PUT /update_profile_pic
# Receives the URL returned by upload_service and stores it in users.profile_pic
# ---------------------------------------------------------------------------
@router.put("/update_profile_pic")
def update_profile_pic(
    payload: UpdateProfilePicSchema,
    request_user=Depends(get_current_user),
    db: Session = Depends(get_db_global),
):
    try:
        user_record = db.query(User).filter(
            User.user_id == request_user.user_id
        ).first()

        if not user_record:
            return response.error_response("User not found.", None, 404)

        user_record.profile_pic = payload.profile_pic_url
        db.commit()

        logger.info(
            f"profile_pic updated for user_id={request_user.user_id}: {payload.profile_pic_url}"
        )

        return response.success_response(
            "Profile picture updated successfully.",
            {"profile_pic": payload.profile_pic_url},
            200,
        )

    except Exception as e:
        db.rollback()
        logger.error(str(e))
        return response.error_response(str(e), None, 400)
