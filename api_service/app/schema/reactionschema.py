from datetime import datetime

from pydantic import BaseModel, ConfigDict


class ReactionCreate(BaseModel):
    post_id: int
    reaction_type: str


class ReactionResponse(BaseModel):
    id: int
    post_id: int
    user_id: int
    reaction_type: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)