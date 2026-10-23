from datetime import date, datetime
from typing import Optional
from uuid import UUID

from sqlalchemy import Boolean, CheckConstraint, Date, DateTime, ForeignKey, Index, Integer, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class UserActivityDay(Base):
    """Daily foreground time for a signed-in student or teacher."""

    __tablename__ = "user_activity_days"
    __table_args__ = (
        CheckConstraint("active_seconds >= 0", name="ck_user_activity_days_active_seconds_nonnegative"),
        Index("ix_user_activity_days_date", "activity_date"),
    )

    user_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    activity_date: Mapped[date] = mapped_column(Date, primary_key=True)
    active_seconds: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    streak_badge_collected: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default="false"
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )
