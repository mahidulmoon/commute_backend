from sqlalchemy import Column, Integer, String, Date, ForeignKey, Text
from app.database import Base


class CompleteProfileModel(Base):
    __tablename__ = "complete_profiles"

    id = Column(Integer, primary_key=True, index=True)

    # Relationship with User
    user_id = Column(
        Integer,
        ForeignKey("users.user_id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
        index=True,
    )

    # Personal Information
    address = Column(Text, nullable=True)
    local_area = Column(String(255), nullable=True)
    dob = Column(Date, nullable=True)
    national_id = Column(String(50), nullable=True)
    student_id = Column(String(100), nullable=True)
    phone_number = Column(String(30), nullable=True)

    # Current Location
    current_city = Column(String(100), nullable=True)
    current_state = Column(String(100), nullable=True)
    current_country_name = Column(String(100), nullable=True)

    # Interests & Hobbies
    interest = Column(Text, nullable=True)
    hobbies = Column(Text, nullable=True)

    # Education
    university = Column(String(255), nullable=True)
    course = Column(String(255), nullable=True)
    level = Column(String(100), nullable=True)

    # Employment
    company = Column(String(255), nullable=True)
    position = Column(String(150), nullable=True)