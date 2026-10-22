import uuid
from typing import List, Optional
from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.deps import get_current_user
from app.core.uploads import read_audio_upload
from app.db.models.planner import PlannerEntry, PlannerEntryKind, PlannerNoteShape
from app.db.models.user import User
from app.db.session import get_db
from app.repositories.planner_repository import PlannerRepository
from app.schemas.planner import (
    PlannerEntryCreate,
    PlannerEntryResponse,
    PlannerEntryUpdate,
)
from app.services.planner_service import PlannerService
from app.services.storage_service import StorageService

router = APIRouter(prefix="/planner", tags=["Learn Planner"])

MAX_AUDIO_BYTES = 25 * 1024 * 1024


def get_service(db: AsyncSession) -> PlannerService:
    return PlannerService(PlannerRepository(db))


@router.get("/entries", response_model=List[PlannerEntryResponse])
async def list_entries(
    kind: Optional[PlannerEntryKind] = Query(default=None),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await get_service(db).list_entries(current_user, kind)


@router.post(
    "/entries",
    response_model=PlannerEntryResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_entry(
    data: PlannerEntryCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await get_service(db).create_entry(current_user, data)


@router.patch("/entries/{entry_id}", response_model=PlannerEntryResponse)
async def update_entry(
    entry_id: uuid.UUID,
    data: PlannerEntryUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = get_service(db)
    entry = await service.get_entry(current_user, entry_id)
    updates = data.model_dump(exclude_unset=True)
    if entry.kind != PlannerEntryKind.EVENT and "due_at" in updates:
        raise HTTPException(
            status_code=422, detail="Only events can have a scheduled date"
        )
    if entry.kind == PlannerEntryKind.EVENT and updates.get("due_at", entry.due_at) is None:
        raise HTTPException(
            status_code=422, detail="Events require a scheduled date and time"
        )
    for field, value in updates.items():
        setattr(entry, field, value)
    await db.commit()
    await db.refresh(entry)
    return service._response(entry)


@router.delete("/entries/{entry_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_entry(
    entry_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = get_service(db)
    entry = await service.get_entry(current_user, entry_id)
    if entry.audio_path:
        await StorageService.delete_file(entry.audio_path)
    await service.repo.delete(entry)


@router.post(
    "/entries/voice-note",
    response_model=PlannerEntryResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_voice_note(
    file: UploadFile = File(...),
    title: str = Query(default="Voice note", min_length=1, max_length=160),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    title = title.strip()
    if not title:
        raise HTTPException(status_code=422, detail="Voice note title cannot be empty")

    contents, media_type, extension = await read_audio_upload(file, MAX_AUDIO_BYTES)

    entry_id = uuid.uuid4()
    storage_path = (
        f"planner/voice-notes/{current_user.id}/{entry_id}.{extension}"
    )
    saved_path = await StorageService.upload_file(storage_path, contents, media_type)
    entry = PlannerEntry(
        id=entry_id,
        owner_id=current_user.id,
        kind=PlannerEntryKind.VOICE_NOTE,
        title=title,
        content=None,
        color="#dbeafe",
        shape=PlannerNoteShape.ROUNDED,
        audio_path=saved_path,
        audio_mime_type=media_type,
        audio_size_bytes=len(contents),
    )
    try:
        saved_entry = await get_service(db).repo.save(entry)
    except Exception:
        await db.rollback()
        await StorageService.delete_file(saved_path)
        raise
    return get_service(db)._response(saved_entry)


@router.get("/entries/{entry_id}/audio")
async def get_voice_note_audio(
    entry_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    entry = await get_service(db).get_entry(current_user, entry_id)
    if entry.kind != PlannerEntryKind.VOICE_NOTE or not entry.audio_path:
        raise HTTPException(status_code=404, detail="Voice note not found")
    contents = await StorageService.download_file(entry.audio_path)
    if contents is None:
        raise HTTPException(status_code=404, detail="Voice note audio not found")
    return Response(
        content=contents,
        media_type=entry.audio_mime_type or "application/octet-stream",
        headers={
            "Cache-Control": "private, no-store",
            "X-Content-Type-Options": "nosniff",
        },
    )
