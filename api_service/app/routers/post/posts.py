from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from app.utils.auth_validation import get_current_user
from app.utils.response import success_response, error_response

router = APIRouter()



@router.post("/create_post")
def create_post(user_id = Depends(get_current_user)):
    return success_response("Post creation successful.",None,201)