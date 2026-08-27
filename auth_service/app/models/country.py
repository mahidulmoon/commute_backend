from sqlalchemy import Column, Integer, String, DateTime, Boolean, ForeignKey, Text, Float, JSON, Enum
from sqlalchemy.sql import func
from ..database import Base

class Country(Base):
    __tablename__ = 'countries'

    id = Column(Integer, primary_key=True, index=True)

    country_name = Column(String(50), nullable=True)
    country_code = Column(String(50), nullable=True)
    country_dial_code = Column(String(50), nullable=True)