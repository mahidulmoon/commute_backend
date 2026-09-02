from datetime import datetime

from pydantic import BaseModel, Field, ConfigDict


class PostCreate(BaseModel):
    content: str = Field(
        ...,
        min_length=1,
        max_length=10000,
    )


class PostResponse(BaseModel):
    id: int
    user_id: int
    content: str
    is_deleted: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class MyPostsResponse(BaseModel):
    items: list[PostResponse]
    total: int