from datetime import datetime

from pydantic import BaseModel, ConfigDict


class CommentCreate(BaseModel):
    post_id: int
    content: str
    parent_id: int | None = None


class CommentResponse(BaseModel):
    id: int
    post_id: int
    user_id: int
    parent_id: int | None
    content: str
    is_deleted: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)