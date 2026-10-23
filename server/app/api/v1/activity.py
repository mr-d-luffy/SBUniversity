from datetime import date, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user, require_role
from app.db.models.activity import UserActivityDay
from app.db.models.user import User, UserRole
from app.db.session import get_db

router = APIRouter(
    prefix="/activity",
    tags=["Activity"],
    dependencies=[Depends(require_role([UserRole.STUDENT, UserRole.TEACHER]))],
)


class TimeHeartbeat(BaseModel):
    activity_date: date
    seconds: int = Field(ge=1, le=60)


def current_streak(rows: list[UserActivityDay], today: date) -> tuple[int, date | None]:
    by_date = {row.activity_date: row for row in rows if row.active_seconds >= 60}
    streak_end = today if today in by_date else today - timedelta(days=1)
    if streak_end not in by_date:
        return 0, None
    count = 0
    cursor = streak_end
    while cursor in by_date:
        count += 1
        cursor -= timedelta(days=1)
    return count, streak_end


async def load_activity(db: AsyncSession, user_id, today: date, days: int) -> dict:
    rows = list((await db.scalars(
        select(UserActivityDay)
        .where(
            UserActivityDay.user_id == user_id,
            UserActivityDay.activity_date <= today,
            UserActivityDay.activity_date >= today - timedelta(days=365),
        )
        .order_by(UserActivityDay.activity_date.desc())
    )).all())
    by_date = {row.activity_date: row for row in rows}
    streak, streak_end = current_streak(rows, today)
    streak_start = streak_end - timedelta(days=streak - 1) if streak_end else None
    collected = bool(streak_start and by_date[streak_start].streak_badge_collected)
    first_day = today - timedelta(days=days - 1)
    daily = []
    for offset in range(days):
        day = first_day + timedelta(days=offset)
        row = by_date.get(day)
        daily.append({
            "date": day.isoformat(),
            "seconds": row.active_seconds if row else 0,
            "active": bool(row and row.active_seconds >= 60),
        })
    return {
        "days": daily,
        "streak_days": streak,
        "streak_badge_collected": collected,
        "can_collect_badge": streak >= 3 and not collected,
        "today_seconds": by_date[today].active_seconds if today in by_date else 0,
    }


@router.get("")
async def get_activity(
    days: int = Query(default=7, ge=7, le=30),
    today: date | None = Query(default=None),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await load_activity(db, current_user.id, today or date.today(), days)


@router.post("/time", status_code=status.HTTP_204_NO_CONTENT)
async def record_time(
    payload: TimeHeartbeat,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if payload.activity_date > date.today() + timedelta(days=1) or payload.activity_date < date.today() - timedelta(days=1):
        raise HTTPException(status_code=422, detail="Activity date is outside the allowed local date range.")

    values = {
        "user_id": current_user.id,
        "activity_date": payload.activity_date,
        "active_seconds": payload.seconds,
    }
    dialect = db.bind.dialect.name if db.bind is not None else ""
    if dialect == "postgresql":
        stmt = pg_insert(UserActivityDay).values(**values)
        stmt = stmt.on_conflict_do_update(
            index_elements=[UserActivityDay.user_id, UserActivityDay.activity_date],
            set_={
                "active_seconds": UserActivityDay.active_seconds + payload.seconds,
                "updated_at": func.now(),
            },
        )
        await db.execute(stmt)
    elif dialect == "sqlite":
        stmt = sqlite_insert(UserActivityDay).values(**values)
        stmt = stmt.on_conflict_do_update(
            index_elements=[UserActivityDay.user_id, UserActivityDay.activity_date],
            set_={
                "active_seconds": UserActivityDay.active_seconds + payload.seconds,
                "updated_at": func.now(),
            },
        )
        await db.execute(stmt)
    else:
        row = await db.get(UserActivityDay, (current_user.id, payload.activity_date))
        if row:
            row.active_seconds += payload.seconds
        else:
            db.add(UserActivityDay(**values))
    await db.commit()


@router.post("/collect")
async def collect_streak_badge(
    today: date | None = Query(default=None),
    days: int = Query(default=30, ge=7, le=30),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    today = today or date.today()
    if today > date.today() + timedelta(days=1) or today < date.today() - timedelta(days=1):
        raise HTTPException(status_code=422, detail="Activity date is outside the allowed local date range.")
    data = await load_activity(db, current_user.id, today, days)
    if data["streak_days"] < 3:
        raise HTTPException(status_code=409, detail="A three-day activity streak is required.")
    rows = list((await db.scalars(
        select(UserActivityDay).where(
            UserActivityDay.user_id == current_user.id,
            UserActivityDay.activity_date <= today,
            UserActivityDay.activity_date >= today - timedelta(days=365),
            UserActivityDay.active_seconds >= 60,
        ).order_by(UserActivityDay.activity_date.desc())
    )).all())
    _, streak_end = current_streak(rows, today)
    if streak_end:
        streak_start = streak_end - timedelta(days=data["streak_days"] - 1)
        row = next(row for row in rows if row.activity_date == streak_start)
        row.streak_badge_collected = True
        await db.commit()
    return await load_activity(db, current_user.id, today, days)
