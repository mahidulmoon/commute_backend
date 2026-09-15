from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, ConfigDict, Field


class StartConversationRequest(BaseModel):
    target_user_id: int = Field(..., description="The user ID to start a 1-to-1 conversation with")


class SendMessageRequest(BaseModel):
    content: str = Field(..., min_length=1, description="Message text content")
    message_type: Optional[str] = Field("text", description="Type of message (text, image_url, etc.)")


class MessageResponse(BaseModel):
    id: int
    conversation_id: int
    sender_id: int
    receiver_id: int
    message_type: str
    content: str
    is_read: bool
    read_at: Optional[datetime] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ConversationResponse(BaseModel):
    id: int
    user1_id: int
    user2_id: int
    other_user_id: int
    unread_count: int = 0
    last_message: Optional[MessageResponse] = None
    last_message_at: Optional[datetime] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ConversationListResponse(BaseModel):
    items: List[ConversationResponse]
    total: int


class MessageListResponse(BaseModel):
    items: List[MessageResponse]
    total: int
    conversation_id: int


class MarkReadResponse(BaseModel):
    conversation_id: int
    messages_marked_read: int


class UnreadCountResponse(BaseModel):
    total_unread: int
