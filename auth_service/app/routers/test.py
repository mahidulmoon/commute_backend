from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from fastapi.responses import JSONResponse
from ..database import SessionLocal
from ..utils import response
from ..models.country import Country
from fastapi.encoders import jsonable_encoder
from app.database import get_db_global


router = APIRouter()


@router.get("/test_url")
def chat_with_ai():
    return {"message": "Hello from AI!"}



@router.get("/get_country_list")
def get_country_list(db: Session = Depends(get_db_global)):
    db_data = db.query(Country).all()
    return response.success_response("country successfully fetched",jsonable_encoder(db_data),200)