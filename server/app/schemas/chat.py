import uuid
from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, ConfigDict, Field
from app.db.models.chat import ChatRole, CommunityConversationKind
from app.db.models.user import UserRole


class ChatMessageRequest(BaseModel):
    session_id: Optional[uuid.UUID] = None
    message: str


class ChatMessageResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    session_id: uuid.UUID
    role: ChatRole
    content: str
    created_at: datetime


class ChatSessionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    user_id: uuid.UUID
    title: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    messages: Optional[List[ChatMessageResponse]] = None


class CommunityMessageCreate(BaseModel):
    content: str = Field(min_length=1, max_length=4000)


class CommunityMessageResponse(BaseModel):
    id: uuid.UUID
    conversation_id: uuid.UUID
    sender_id: uuid.UUID
    sender_name: str
    sender_role: UserRole
    sender_avatar_url: Optional[str] = None
    is_mine: bool
    content: str
    audio_url: Optional[str] = None
    audio_mime_type: Optional[str] = None
    audio_size_bytes: Optional[int] = None
    created_at: datetime


class CommunityConversationResponse(BaseModel):
    id: uuid.UUID
    kind: CommunityConversationKind
    title: str
    other_user_id: Optional[uuid.UUID] = None
    other_user_role: Optional[UserRole] = None
    last_message: Optional[str] = None
    last_message_at: Optional[datetime] = None
    expires_at: datetime
    is_shared_room: bool = False


class CommunityStudentOption(BaseModel):
    id: uuid.UUID
    full_name: str
    avatar_url: Optional[str] = None
