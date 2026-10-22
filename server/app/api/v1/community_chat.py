import uuid
from typing import List
from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.deps import get_current_user, require_role
from app.core.rate_limit import RateLimiter
from app.core.uploads import read_audio_upload
from app.db.models.user import User, UserRole
from app.db.session import get_db
from app.repositories.community_chat_repository import CommunityChatRepository
from app.schemas.chat import (
    CommunityConversationResponse,
    CommunityMessageCreate,
    CommunityMessageResponse,
    CommunityStudentOption,
)
from app.services.community_chat_service import CommunityChatService

router = APIRouter(prefix="/community-chat", tags=["Community Chat"])
MAX_AUDIO_BYTES = 25 * 1024 * 1024


def get_service(db: AsyncSession) -> CommunityChatService:
    return CommunityChatService(CommunityChatRepository(db))


@router.get("/conversations", response_model=List[CommunityConversationResponse])
async def list_conversations(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await get_service(db).list_conversations(current_user)


@router.get("/students", response_model=List[CommunityStudentOption])
async def list_students(
    search: str = Query(default="", max_length=100),
    current_user: User = Depends(require_role(UserRole.STUDENT)),
    db: AsyncSession = Depends(get_db),
):
    return await get_service(db).list_students(current_user, search)


@router.post(
    "/direct/{student_id}",
    response_model=CommunityConversationResponse,
    dependencies=[Depends(RateLimiter(requests_limit=20, window_seconds=60))],
)
async def start_direct_chat(
    student_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await get_service(db).start_peer_direct(current_user, student_id)


@router.post(
    "/staff/{staff_role}",
    response_model=CommunityConversationResponse,
    dependencies=[Depends(RateLimiter(requests_limit=10, window_seconds=60))],
)
async def start_staff_chat(
    staff_role: UserRole,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await get_service(db).start_staff_support(current_user, staff_role)


@router.get(
    "/conversations/{conversation_id}/messages",
    response_model=List[CommunityMessageResponse],
)
async def list_messages(
    conversation_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await get_service(db).list_messages(current_user, conversation_id)


@router.post(
    "/conversations/{conversation_id}/messages",
    response_model=CommunityMessageResponse,
    dependencies=[Depends(RateLimiter(requests_limit=30, window_seconds=60))],
)
async def send_message(
    conversation_id: uuid.UUID,
    body: CommunityMessageCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await get_service(db).send_message(
        current_user, conversation_id, body.content
    )


@router.post(
    "/conversations/{conversation_id}/audio",
    response_model=CommunityMessageResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(RateLimiter(requests_limit=10, window_seconds=60))],
)
async def send_audio_message(
    conversation_id: uuid.UUID,
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    contents, media_type, extension = await read_audio_upload(file, MAX_AUDIO_BYTES)
    return await get_service(db).send_audio(
        current_user, conversation_id, contents, media_type, extension
    )


@router.get("/messages/{message_id}/audio")
async def get_audio_message(
    message_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    contents, media_type = await get_service(db).get_audio(current_user, message_id)
    return Response(
        content=contents,
        media_type=media_type,
        headers={
            "Cache-Control": "private, no-store",
            "X-Content-Type-Options": "nosniff",
        },
    )
