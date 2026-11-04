import asyncio
import uuid
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.deps import get_current_user
from app.core.redis import get_redis_client
from app.db.models.user import User, UserRole
from app.db.session import get_db
from app.schemas.ranking import LeaderboardResponse, MyRankResponse
from app.services.ranking_service import RankingService
from app.services.course_access_service import is_course_unlocked

router = APIRouter(prefix="/ranking", tags=["Ranking"])


@router.get("/top", response_model=LeaderboardResponse)
async def get_top_ranking(
    scope: str = Query("overall", pattern="^(overall|course)$"),
    course_id: Optional[uuid.UUID] = None,
    limit: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if (scope == "course") != (course_id is not None):
        raise HTTPException(
            status_code=422,
            detail="course_id must be provided only when scope is 'course'",
        )
    if (
        current_user.role == UserRole.STUDENT
        and course_id is not None
        and not await is_course_unlocked(db, current_user.id, course_id)
    ):
        raise HTTPException(status_code=404, detail="Course not found")
    service = RankingService(db)
    return await service.get_top_students(scope=scope, course_id=course_id, limit=limit)


@router.get("/me", response_model=MyRankResponse)
async def get_my_rank(
    scope: str = Query("overall", pattern="^(overall|course)$"),
    course_id: Optional[uuid.UUID] = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if (scope == "course") != (course_id is not None):
        raise HTTPException(
            status_code=422,
            detail="course_id must be provided only when scope is 'course'",
        )
    if (
        current_user.role == UserRole.STUDENT
        and course_id is not None
        and not await is_course_unlocked(db, current_user.id, course_id)
    ):
        raise HTTPException(status_code=404, detail="Course not found")
    service = RankingService(db)
    return await service.get_student_rank(current_user.id, scope=scope, course_id=course_id)


@router.get("/stream")
async def stream_ranking_updates(
    current_user: User = Depends(get_current_user),
):
    """
    Server-Sent Events (SSE) stream for live leaderboard updates.
    """
    async def event_generator():
        redis = await get_redis_client()
        pubsub = redis.pubsub()
        await pubsub.subscribe("lb:updates")
        try:
            # Send initial ping
            yield "event: ping\ndata: {}\n\n"
            async for msg in pubsub.listen():
                if msg and msg.get("type") == "message":
                    data = msg.get("data")
                    yield f"event: update\ndata: {data}\n\n"
        except asyncio.CancelledError:
            pass
        finally:
            await pubsub.close()

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
