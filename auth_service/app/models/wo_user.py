from sqlalchemy import Column, Integer, String, DateTime, Boolean, ForeignKey, Text, Float, JSON, Enum
from sqlalchemy.sql import func
from ..database import Base

class User(Base):
    __tablename__ = 'users'

    user_id = Column(Integer, primary_key=True, index=True)

    # Auth & Identity
    username = Column(String(80), unique=True, index=True, nullable=False)
    email = Column(String(100), unique=True, index=True, nullable=False)
    password = Column(String(128), nullable=False)

    # Personal Info
    first_name = Column(String(50), nullable=True)
    last_name = Column(String(50), nullable=True)
    address = Column(String(255), nullable=True)
    phone_number = Column(String(30), nullable=True)
    city = Column(String(50), nullable=True)
    state = Column(String(50), nullable=True)
    country_name = Column(String(255), nullable=True)

    # Role / Type
    type = Column(Enum("ADMIN", "EDIT", "USER", "AGENT", "UNSPECIFIED",name="user_type_enum"), default="UNSPECIFIED", nullable=False)

    # Timestamps
    date_joined = Column(DateTime(timezone=True), server_default=func.now())

    # OTP and Password Recovery
    otp = Column(String(6), nullable=True)
    otp_expiration = Column(DateTime, nullable=True)
    password_reset_token = Column(String(50), nullable=True)
    password_reset_OTP = Column(String(50), nullable=True)

    # Status Flags
    is_active = Column(Boolean, default=True)
    otp_verified = Column(Boolean, default=False)

    postcode = Column(String(50), nullable=True)
    country_livein = Column(String(50), nullable=True)
    website = Column(String(150), nullable=True)
    language = Column(String(50), default="en", nullable=True)

    status_type = Column(Enum('active', 'suspended', 'unsuspended', 'not_available', 'terminated', name="freelancer_status_enum"), default="active")
    # Profile Image
    profile_pic = Column(String(200), nullable=True)