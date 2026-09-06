from fastapi import APIRouter
from fastapi.responses import JSONResponse
from app.logger import logger

router = APIRouter()



@router.get("/test_url")
def chat_with_ai():
    logger.info("Test endpoint /test_url hit.")
    return {"message": "Hello from AI!"}