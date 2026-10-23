import re
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user
from app.db.models.security_event import SecurityRequestEvent
from app.db.models.user import User, UserRole
from app.db.session import get_db

router = APIRouter(prefix="/security", tags=["Security Telemetry"])
_UUID_SEGMENT = re.compile(r"/[0-9a-fA-F]{8}-[0-9a-fA-F-]{27,}")
_NUMBER_SEGMENT = re.compile(r"/\d+(?=/|$)")


class NavigationEvent(BaseModel):
    path: str = Field(min_length=1, max_length=500)


@router.post("/navigation", status_code=204)
async def record_navigation(
    payload: NavigationEvent,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if current_user.role not in {UserRole.STUDENT, UserRole.TEACHER}:
        raise HTTPException(status_code=403, detail="Student or teacher account required")
    path = payload.path.split("?", 1)[0].split("#", 1)[0]
    if not path.startswith("/") or path.startswith("//"):
        raise HTTPException(status_code=422, detail="A same-site route path is required")
    path = _NUMBER_SEGMENT.sub("/:id", _UUID_SEGMENT.sub("/:id", path))[:240]
    recent = await db.scalar(
        select(SecurityRequestEvent.id).where(
            SecurityRequestEvent.actor_id == current_user.id,
            SecurityRequestEvent.method == "NAV",
            SecurityRequestEvent.path == path,
            SecurityRequestEvent.created_at >= datetime.now(timezone.utc) - timedelta(seconds=5),
        ).limit(1)
    )
    if not recent:
        db.add(
            SecurityRequestEvent(
                actor_id=current_user.id,
                path=path,
                method="NAV",
                status_code=200,
                duration_ms=0,
            )
        )
        await db.commit()
