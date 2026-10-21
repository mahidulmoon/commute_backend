from sqlalchemy import Column, BigInteger, String, Integer, Boolean
from app.models.base import BaseModel


class UploadFileModel(BaseModel):
    __tablename__ = "uploaded_files"

    user_id = Column(BigInteger, nullable=False, index=True)
    original_filename = Column(String(255), nullable=False)
    stored_filename = Column(String(255), nullable=False)
    file_path = Column(String(500), nullable=False)
    file_url = Column(String(500), nullable=False)
    file_size = Column(Integer, nullable=False)  # bytes
    content_type = Column(String(100), nullable=False)
    category = Column(String(50), nullable=False, index=True)
    is_deleted = Column(Boolean, default=False, nullable=False)
