import asyncio
import json
from typing import List
from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.deps import require_role
from app.core.logging import logger
from app.db.models.user import UserRole
from app.db.session import get_db
from app.schemas.analytics import OverviewAnalyticsResponse, StudentAnalyticsItem, TeacherAnalyticsItem
from app.services.analytics_service import AnalyticsService

router = APIRouter(prefix="/analytics", tags=["Admin Analytics"], dependencies=[Depends(require_role(UserRole.ADMIN))])


@router.get("/overview", response_model=OverviewAnalyticsResponse)
async def get_overview(db: AsyncSession = Depends(get_db)):
    service = AnalyticsService(db)
    return await service.get_overview_analytics()


@router.get("/teachers", response_model=List[TeacherAnalyticsItem])
async def get_teachers(db: AsyncSession = Depends(get_db)):
    service = AnalyticsService(db)
    return await service.get_teacher_analytics()


@router.get("/students", response_model=List[StudentAnalyticsItem])
async def get_students(db: AsyncSession = Depends(get_db)):
    service = AnalyticsService(db)
    return await service.get_student_analytics()


@router.get("/stream")
async def stream_live_analytics(db: AsyncSession = Depends(get_db)):
    """SSE live analytics stream."""
    async def event_generator():
        service = AnalyticsService(db)
        while True:
            try:
                overview = await service.get_overview_analytics()
                yield f"data: {json.dumps(overview.model_dump())}\n\n"
                await asyncio.sleep(5)
            except asyncio.CancelledError:
                break
            except Exception as exc:
                logger.error("Admin analytics stream failed: %s", exc)
                await asyncio.sleep(5)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
