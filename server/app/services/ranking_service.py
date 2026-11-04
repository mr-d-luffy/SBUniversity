import json
import uuid
from datetime import datetime, timezone
from typing import List, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import logger
from app.core.redis import get_redis_client
from app.db.models.user import UserStatus
from app.repositories.task_repository import TaskRepository
from app.repositories.user_repository import UserRepository
from app.schemas.ranking import LeaderboardResponse, MyRankResponse, RankedStudentItem

REDIS_KEY_LB_OVERALL = "lb:overall"
REDIS_CHANNEL_LB_UPDATES = "lb:updates"


def compute_leaderboard_score(points: int, last_completed_at: Optional[datetime]) -> float:
    """
    Score formula: points + (1 - epoch_seconds / 1e10)
    Points are positive integers. The fraction breaks ties:
    Earlier completion timestamp yields a higher fraction.
    """
    if points <= 0:
        return 0.0
    epoch = last_completed_at.timestamp() if last_completed_at else 0.0
    tie_break_fraction = max(0.0, min(0.999999, 1.0 - (epoch / 1e10)))
    return float(points) + tie_break_fraction


class RankingService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.task_repo = TaskRepository(db)
        self.user_repo = UserRepository(db)

    async def refresh_student(self, student_id: uuid.UUID) -> None:
        """
        Recomputes student points from DB and sets score absolutely in Redis.
        Broadcasts live update event over Redis pub/sub.
        """
        user = await self.user_repo.get_by_id(student_id)
        redis = await get_redis_client()

        # If user is not active, remove from leaderboard
        if not user or user.status != UserStatus.ACTIVE:
            await redis.zrem(REDIS_KEY_LB_OVERALL, str(student_id))
            await redis.publish(REDIS_CHANNEL_LB_UPDATES, json.dumps({"action": "remove", "student_id": str(student_id)}))
            return

        total_points, tasks_completed, last_completed_at = await self.task_repo.get_student_points_summary(student_id)

        if total_points <= 0:
            await redis.zrem(REDIS_KEY_LB_OVERALL, str(student_id))
        else:
            score = compute_leaderboard_score(total_points, last_completed_at)
            await redis.zadd(REDIS_KEY_LB_OVERALL, {str(student_id): score})

        # Broadcast update for live SSE listeners
        payload = {
            "action": "update",
            "student_id": str(student_id),
            "points": total_points,
            "tasks_completed": tasks_completed,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        await redis.publish(REDIS_CHANNEL_LB_UPDATES, json.dumps(payload))
        logger.info("Refreshed ranking for student %s: points=%d", student_id, total_points)

    async def get_top_students(
        self,
        scope: str = "overall",
        course_id: Optional[uuid.UUID] = None,
        limit: int = 4,
    ) -> LeaderboardResponse:
        if scope == "course" and course_id:
            db_top = await self.task_repo.get_top_students_sql(
                course_id=course_id,
                limit=limit,
            )
            items = [
                RankedStudentItem(
                    rank=rank,
                    student_id=student_id,
                    name=name,
                    avatar_url=avatar,
                    points=int(points),
                    tasks_completed=int(tasks_completed),
                )
                for rank, (
                    student_id,
                    name,
                    avatar,
                    points,
                    tasks_completed,
                    _,
                ) in enumerate(db_top, start=1)
            ]
            return LeaderboardResponse(
                updated_at=datetime.now(timezone.utc),
                scope=scope,
                course_id=course_id,
                items=items,
            )

        redis = await get_redis_client()
        key = REDIS_KEY_LB_OVERALL

        # Fetch top members from Redis
        try:
            top_member_ids = await redis.zrevrange(key, 0, limit - 1)
        except Exception as e:
            logger.warning("Redis leaderboard fetch failed: %s; falling back to DB", e)
            top_member_ids = []

        items: List[RankedStudentItem] = []

        if top_member_ids:
            member_ids = []
            for m_id in top_member_ids:
                try:
                    member_ids.append(uuid.UUID(str(m_id)))
                except ValueError:
                    logger.warning(
                        "Skipping invalid student ID in leaderboard: %s", m_id
                    )

            summaries = await self.task_repo.get_student_points_summaries(member_ids)
            for rank_idx, m_id in enumerate(top_member_ids, start=1):
                try:
                    student_id = uuid.UUID(str(m_id))
                except ValueError:
                    continue
                summary = summaries.get(student_id)
                if summary:
                    name, avatar, points, tasks_completed = summary
                    if points > 0:
                        items.append(
                            RankedStudentItem(
                                rank=rank_idx,
                                student_id=student_id,
                                name=name,
                                avatar_url=avatar,
                                points=points,
                                tasks_completed=tasks_completed,
                            )
                        )

        # If Redis was empty or cold, fall back to SQL and seed Redis
        if not items:
            db_top = await self.task_repo.get_top_students_sql(
                course_id=course_id, limit=limit
            )
            redis_scores = {}
            for rank_idx, (s_id, name, avatar, pts, cnt, last_comp) in enumerate(db_top, start=1):
                items.append(
                    RankedStudentItem(
                        rank=rank_idx,
                        student_id=s_id,
                        name=name,
                        avatar_url=avatar,
                        points=int(pts),
                        tasks_completed=int(cnt),
                    )
                )
                redis_scores[str(s_id)] = compute_leaderboard_score(int(pts), last_comp)
            if redis_scores:
                try:
                    await redis.zadd(key, redis_scores)
                except Exception as e:
                    logger.warning("Redis leaderboard seed failed: %s", e)

        return LeaderboardResponse(
            updated_at=datetime.now(timezone.utc),
            scope=scope,
            course_id=course_id,
            items=items,
        )

    async def get_student_rank(
        self,
        student_id: uuid.UUID,
        scope: str = "overall",
        course_id: Optional[uuid.UUID] = None,
    ) -> MyRankResponse:
        if scope == "course" and course_id:
            ranking = await self.task_repo.get_student_ranking_summary(
                student_id, course_id
            )
            if ranking is None:
                return MyRankResponse(
                    student_id=student_id,
                    rank=None,
                    points=0,
                    tasks_completed=0,
                )
            rank, points, tasks_completed = ranking
            return MyRankResponse(
                student_id=student_id,
                rank=rank,
                points=points,
                tasks_completed=tasks_completed,
            )

        redis = await get_redis_client()
        key = REDIS_KEY_LB_OVERALL if scope == "overall" or not course_id else f"lb:course:{course_id}"

        total_pts, tasks_cnt, _ = await self.task_repo.get_student_points_summary(student_id)
        if total_pts <= 0:
            return MyRankResponse(student_id=student_id, rank=None, points=0, tasks_completed=0)

        rank_val = None
        try:
            zrank = await redis.zrevrank(key, str(student_id))
            if zrank is not None:
                rank_val = zrank + 1
        except Exception as exc:
            logger.warning("Redis student-rank lookup failed: %s", exc)

        return MyRankResponse(
            student_id=student_id,
            rank=rank_val,
            points=total_pts,
            tasks_completed=tasks_cnt,
        )

    async def rebuild_all_scores(self) -> int:
        """Cold-start rebuild or nightly reconciliation of Redis leaderboard."""
        db_top = await self.task_repo.get_top_students_sql(limit=5000)
        redis = await get_redis_client()
        redis_scores = {}
        for s_id, _, _, pts, _, last_comp in db_top:
            redis_scores[str(s_id)] = compute_leaderboard_score(int(pts), last_comp)
        if redis_scores:
            await redis.zadd(REDIS_KEY_LB_OVERALL, redis_scores)
        count = len(redis_scores)
        logger.info("Rebuilt Redis leaderboard for %d students", count)
        return count
