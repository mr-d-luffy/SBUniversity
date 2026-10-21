import uuid
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user
from app.core.rate_limit import RateLimiter
from app.db.models.user import User
from app.db.session import get_db
from app.repositories.whiteboard_repository import WhiteboardRepository
from app.schemas.whiteboard import (
    WhiteboardCourseResponse,
    WhiteboardMessageCreate,
    WhiteboardMessageResponse,
    WhiteboardSessionResponse,
    WhiteboardStrokeCreate,
    WhiteboardStrokeResponse,
)
from app.services.whiteboard_service import WhiteboardService

router = APIRouter(prefix="/whiteboard", tags=["Live Whiteboard"])
def get_service(db: AsyncSession) -> WhiteboardService:
    return WhiteboardService(WhiteboardRepository(db))


@router.get("/courses", response_model=List[WhiteboardCourseResponse])
async def list_courses(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await get_service(db).list_courses(current_user)


@router.get(
    "/courses/{course_id}/session",
    response_model=Optional[WhiteboardSessionResponse],
)
async def get_course_session(
    course_id: uuid.UUID,
    board_generation: Optional[int] = Query(default=None, ge=0),
    after_stroke_id: Optional[uuid.UUID] = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await get_service(db).get_course_session(
        current_user, course_id, board_generation, after_stroke_id
    )


@router.post(
    "/courses/{course_id}/sessions",
    response_model=WhiteboardSessionResponse,
    status_code=status.HTTP_201_CREATED,
)
async def start_session(
    course_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await get_service(db).start_session(current_user, course_id)


@router.post(
    "/courses/{course_id}/join",
    response_model=WhiteboardSessionResponse,
)
async def join_session(
    course_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await get_service(db).join_session(current_user, course_id)


@router.post(
    "/sessions/{session_id}/strokes",
    response_model=WhiteboardStrokeResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_stroke(
    session_id: uuid.UUID,
    data: WhiteboardStrokeCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await get_service(db).add_stroke(current_user, session_id, data)


@router.delete("/sessions/{session_id}/strokes", status_code=status.HTTP_204_NO_CONTENT)
async def clear_strokes(
    session_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await get_service(db).clear_strokes(current_user, session_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post(
    "/sessions/{session_id}/undo",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def undo_stroke(
    session_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    undone = await get_service(db).undo_stroke(current_user, session_id)
    if not undone:
        raise HTTPException(status_code=404, detail="There is no stroke to undo")
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/sessions/{session_id}/end", status_code=status.HTTP_204_NO_CONTENT)
async def end_session(
    session_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await get_service(db).end_session(current_user, session_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get(
    "/sessions/{session_id}/messages",
    response_model=List[WhiteboardMessageResponse],
)
async def list_messages(
    session_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await get_service(db).list_messages(current_user, session_id)


@router.post(
    "/sessions/{session_id}/messages",
    response_model=WhiteboardMessageResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(RateLimiter(requests_limit=30, window_seconds=60))],
)
async def send_message(
    session_id: uuid.UUID,
    data: WhiteboardMessageCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await get_service(db).send_message(
        current_user, session_id, data.content
    )
