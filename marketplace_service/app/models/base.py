from sqlalchemy import Column, BigInteger, DateTime
from sqlalchemy.sql import func
from app.database import Base


class BaseModel(Base):
    __abstract__ = True
    id = Column(BigInteger, primary_key=True, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
