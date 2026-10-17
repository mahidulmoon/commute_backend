from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field, ConfigDict


class CategoryCreate(BaseModel):
    name: str = Field(..., min_length=2, max_length=100)
    slug: Optional[str] = Field(None, max_length=120)
    description: Optional[str] = None
    icon_url: Optional[str] = None
    parent_id: Optional[int] = None
    display_order: Optional[int] = 0
    is_active: Optional[bool] = True


class CategoryUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=2, max_length=100)
    slug: Optional[str] = Field(None, max_length=120)
    description: Optional[str] = None
    icon_url: Optional[str] = None
    parent_id: Optional[int] = None
    display_order: Optional[int] = None
    is_active: Optional[bool] = None


class CategoryResponse(BaseModel):
    id: int
    name: str
    slug: str
    description: Optional[str] = None
    icon_url: Optional[str] = None
    parent_id: Optional[int] = None
    display_order: int
    is_active: bool
    created_at: datetime
    subcategories: Optional[List["CategoryResponse"]] = None

    model_config = ConfigDict(from_attributes=True)
