import uuid
from typing import List

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user, require_role
from app.core.rate_limit import RateLimiter
from app.db.models.user import User, UserRole
from app.db.session import get_db
from app.repositories.community_chat_repository import CommunityChatRepository
from app.schemas.chat import (
    CommunityChatDeviceRegister,
    CommunityChatDeviceResponse,
    CommunityConversationResponse,
    CommunityKeyEnvelopeCreate,
    CommunityKeyEnvelopeResponse,
    CommunityMessageCreate,
    CommunityMessageResponse,
    CommunityStudentOption,
)
from app.services.community_chat_service import CommunityChatService

router = APIRouter(prefix="/community-chat", tags=["Community Chat"])
MAX_AUDIO_BYTES = 25 * 1024 * 1024
MAX_ENCRYPTED_AUDIO_BYTES = MAX_AUDIO_BYTES + 128


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
    "/devices",
    response_model=CommunityChatDeviceResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(RateLimiter(requests_limit=10, window_seconds=60))],
)
async def register_chat_device(
    body: CommunityChatDeviceRegister,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await get_service(db).register_device(
        current_user, body.device_id, body.public_key
    )


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


@router.get(
    "/conversations/{conversation_id}/devices",
    response_model=List[CommunityChatDeviceResponse],
)
async def list_chat_devices(
    conversation_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await get_service(db).list_conversation_devices(
        current_user, conversation_id
    )


@router.get(
    "/conversations/{conversation_id}/keys",
    response_model=List[CommunityKeyEnvelopeResponse],
)
async def list_chat_keys(
    conversation_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await get_service(db).list_key_envelopes(
        current_user, conversation_id
    )


@router.post(
    "/conversations/{conversation_id}/keys",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(RateLimiter(requests_limit=60, window_seconds=60))],
)
async def save_chat_keys(
    conversation_id: uuid.UUID,
    sender_device_id: uuid.UUID = Query(...),
    envelopes: List[CommunityKeyEnvelopeCreate] = ...,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await get_service(db).save_key_envelopes(
        current_user, conversation_id, sender_device_id, envelopes
    )
    return Response(status_code=status.HTTP_204_NO_CONTENT)


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
    media_type: str = Query(..., pattern=r"^audio/(webm|ogg|mp4)$"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if file.content_type != "application/octet-stream":
        raise HTTPException(status_code=415, detail="Audio must be encrypted before upload.")
    contents = await file.read(MAX_ENCRYPTED_AUDIO_BYTES + 1)
    await file.close()
    if not contents:
        raise HTTPException(status_code=400, detail="Audio recording is empty")
    if len(contents) > MAX_ENCRYPTED_AUDIO_BYTES:
        raise HTTPException(status_code=413, detail="Audio exceeds the size limit.")
    if not contents.startswith(b"SBU-E2EE-v1!"):
        raise HTTPException(status_code=415, detail="Audio payload is not encrypted.")
    return await get_service(db).send_audio(
        current_user, conversation_id, contents, media_type, "enc"
    )


@router.get("/messages/{message_id}/audio")
async def get_audio_message(
    message_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    contents, _media_type = await get_service(db).get_audio(current_user, message_id)
    return Response(
        content=contents,
        media_type="application/octet-stream",
        headers={
            "Cache-Control": "private, no-store",
            "X-Content-Type-Options": "nosniff",
        },
    )
