from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from app.utils.auth_validation import get_current_user

router = APIRouter()



@router.post("/create_post")
def create_post(user_id = Depends(get_current_user)):
    return {"message": "post creation success"}