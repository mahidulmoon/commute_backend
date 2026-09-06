from pydantic import BaseModel, EmailStr, ConfigDict
from datetime import datetime
from typing import Optional



class RegisterUser(BaseModel):
    username: str
    email: EmailStr
    password: str
    first_name: str
    last_name: str
    address: str
    phone_number: str
    city: str
    state: str
    country_name: str

    class Config:
        orm_mode = True
        from_attributes=True

class LoginUserInput(BaseModel):
    email: EmailStr
    password: str

    class Config:
        orm_mode = True
        from_attributes=True


class ForgetPass1Input(BaseModel):
    email: EmailStr

    class Config:
        orm_mode = True
        from_attributes=True

class ForgetPass2Input(BaseModel):
    email: EmailStr
    otp: str
    password: str

    class Config:
        orm_mode = True
        from_attributes=True



class GetUser(BaseModel):
    user_id: int
    username: str
    email: str

    first_name: Optional[str] = None
    last_name: Optional[str] = None
    address: Optional[str] = None
    phone_number: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    country_name: Optional[str] = None

    type: str
    date_joined: Optional[datetime] = None
    is_active: Optional[bool] = None

    postcode: Optional[str] = None
    country_livein: Optional[str] = None
    website: Optional[str] = None
    language: Optional[str] = None

    status_type: Optional[str] = None
    profile_pic: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class UpdateUserStatusInput(BaseModel):
    user_id: int
    is_active: bool

    model_config = ConfigDict(from_attributes=True)