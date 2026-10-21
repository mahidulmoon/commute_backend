from pydantic import BaseModel as PydanticBaseModel
from typing import List, Optional
from datetime import datetime


class FileUploadResponse(PydanticBaseModel):
    id: int
    file_url: str
    original_filename: str
    file_size: int
    content_type: str
    category: str
    created_at: datetime

    class Config:
        from_attributes = True


class MultipleUploadResponse(PydanticBaseModel):
    files: List[FileUploadResponse]
    total: int


class FileListResponse(PydanticBaseModel):
    items: List[FileUploadResponse]
    total: int
    page: int
    page_size: int
