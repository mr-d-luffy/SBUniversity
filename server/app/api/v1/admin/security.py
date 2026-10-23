from datetime import datetime, timedelta, timezone
from fastapi import APIRouter, Depends, Query
from sqlalchemy import case, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.deps import require_role
from app.db.models.security_event import SecurityRequestEvent
from app.db.models.user import User, UserRole
from app.db.session import get_db

router = APIRouter(
    prefix="/security",
    tags=["Admin Security Monitor"],
    dependencies=[Depends(require_role(UserRole.ADMIN))],
)


@router.get("/events")
async def list_security_events(
    since_minutes: int = Query(60, ge=1, le=10080),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    since = datetime.now(timezone.utc) - timedelta(minutes=since_minutes)
    base = select(SecurityRequestEvent).where(SecurityRequestEvent.created_at >= since)
    total = await db.scalar(select(func.count()).select_from(base.subquery())) or 0
    events = (
        await db.execute(
            base.options(selectinload(SecurityRequestEvent.actor))
            .order_by(SecurityRequestEvent.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
    ).scalars().all()
    return {
        "items": [
            {
                "id": str(event.id),
                "actor_id": str(event.actor_id) if event.actor_id else None,
                "actor_name": event.actor.full_name if event.actor else "Guest / unauthenticated",
                "actor_role": event.actor.role.value if event.actor else None,
                "path": event.path,
                "method": event.method,
                "status_code": event.status_code,
                "duration_ms": event.duration_ms,
                "client_ip": event.client_ip,
                "user_agent": event.user_agent,
                "created_at": event.created_at.isoformat(),
            }
            for event in events
        ],
        "total": total,
        "page": page,
        "page_size": page_size,
    }


@router.get("/summary")
async def security_summary(
    since_minutes: int = Query(60, ge=1, le=10080),
    db: AsyncSession = Depends(get_db),
):
    since = datetime.now(timezone.utc) - timedelta(minutes=since_minutes)
    result = await db.execute(
        select(
            func.count(SecurityRequestEvent.id),
            func.count(func.distinct(SecurityRequestEvent.actor_id)),
            func.sum(case((SecurityRequestEvent.status_code >= 400, 1), else_=0)),
            func.avg(SecurityRequestEvent.duration_ms),
        ).where(SecurityRequestEvent.created_at >= since)
    )
    requests, actors, errors, avg_duration = result.one()
    return {
        "requests": requests or 0,
        "active_users": actors or 0,
        "errors": errors or 0,
        "average_duration_ms": round(float(avg_duration or 0), 1),
        "since_minutes": since_minutes,
    }
