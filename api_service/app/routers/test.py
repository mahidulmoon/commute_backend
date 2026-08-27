from fastapi import APIRouter
from fastapi.responses import JSONResponse

router = APIRouter()



@router.get("/test_url")
def chat_with_ai():
    return {"message": "Hello from AI!"}