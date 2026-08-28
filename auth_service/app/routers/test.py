from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from fastapi.responses import JSONResponse
from app.database import SessionLocal
from app.utils import response
from app.models.country import Country
from app.models.groups import Group
from app.models.grouprule import GroupRule
from app.models.usergroupmembership import UserGroupMembership
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

@router.get("/get_groups_list")
def get_groups_list(db: Session = Depends(get_db_global)):
    db_data = db.query(Group).all()
    return response.success_response("data successfully fetched",jsonable_encoder(db_data),200)

@router.get("/get_groupruls_list")
def get_grouprules_list(db: Session = Depends(get_db_global)):
    db_data = db.query(GroupRule).all()
    return response.success_response("data successfully fetched",jsonable_encoder(db_data),200)

@router.get("/get_usergroupmembership_list")
def get_usergroupmembership_list(db: Session = Depends(get_db_global)):
    db_data = db.query(UserGroupMembership).all()
    return response.success_response("data successfully fetched",jsonable_encoder(db_data),200)