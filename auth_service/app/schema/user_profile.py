from datetime import date
from typing import Optional

from pydantic import BaseModel, ConfigDict


class CompleteProfileSchema(BaseModel):
    # Postcode is required for group allocation
    postcode: str

    address: Optional[str] = None
    local_area: Optional[str] = None
    dob: Optional[date] = None
    national_id: Optional[str] = None
    student_id: Optional[str] = None
    phone_number: Optional[str] = None

    current_city: Optional[str] = None
    current_state: Optional[str] = None
    current_country_name: Optional[str] = None

    interest: Optional[str] = None
    hobbies: Optional[str] = None

    university: Optional[str] = None
    course: Optional[str] = None
    level: Optional[str] = None

    company: Optional[str] = None
    position: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)