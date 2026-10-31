import uuid

from fastapi import HTTPException

from app.db.models.course import Course
from app.db.models.user import User, UserRole
from app.db.models.whiteboard import (
    WhiteboardMessage,
    WhiteboardSession,
    WhiteboardStroke,
)
from app.repositories.whiteboard_repository import WhiteboardRepository
from app.schemas.whiteboard import (
    WhiteboardCourseResponse,
    WhiteboardMessageResponse,
    WhiteboardSessionResponse,
    WhiteboardStrokeCreate,
    WhiteboardStrokeResponse,
)

MAX_SESSION_STROKES = 2000


class WhiteboardService:
    def __init__(self, repository: WhiteboardRepository):
        self.repo = repository

    async def list_courses(self, user: User) -> list[WhiteboardCourseResponse]:
        courses = await self.repo.list_courses(user)
        return [
            WhiteboardCourseResponse(
                id=course.id,
                code=course.code,
                title=course.title,
                is_live=is_live,
            )
            for course, is_live in courses
        ]

    async def get_course_session(
        self,
        user: User,
        course_id: uuid.UUID,
        board_generation: int | None = None,
        after_stroke_id: uuid.UUID | None = None,
    ) -> WhiteboardSessionResponse | None:
        course = await self._get_accessible_course(user, course_id)
        session = await self.repo.get_active_session(course.id)
        if session is None:
            return None
        strokes, is_snapshot = await self.repo.get_session_strokes(
            session, board_generation, after_stroke_id
        )
        return self._session_response(session, strokes, is_snapshot)

    async def start_session(
        self, user: User, course_id: uuid.UUID
    ) -> WhiteboardSessionResponse:
        course = await self._get_controller_course(user, course_id)
        session = await self.repo.start_session(course, user)
        return self._session_response(session)

    async def join_session(
        self, user: User, course_id: uuid.UUID
    ) -> WhiteboardSessionResponse:
        if user.role != UserRole.STUDENT:
            raise HTTPException(
                status_code=403, detail="Only enrolled students can join as students"
            )
        course = await self._get_accessible_course(user, course_id)
        session = await self.repo.get_active_session(course.id)
        if session is None:
            raise HTTPException(status_code=404, detail="There is no live class to join")
        loaded_session = await self.repo.get_session(session.id)
        if loaded_session is None:
            raise HTTPException(status_code=404, detail="There is no live class to join")
        return self._session_response(loaded_session)

    async def end_session(self, user: User, session_id: uuid.UUID) -> None:
        session = await self._get_teacher_session(user, session_id)
        await self.repo.end_session(session)

    async def add_stroke(
        self, user: User, session_id: uuid.UUID, data: WhiteboardStrokeCreate
    ) -> WhiteboardStrokeResponse:
        session = await self._get_teacher_session(user, session_id)
        if await self.repo.count_strokes(session.id) >= MAX_SESSION_STROKES:
            raise HTTPException(
                status_code=409,
                detail="This board has reached its stroke limit. Clear the board to continue.",
            )
        stroke = await self.repo.create_stroke(
            session.id,
            user.id,
            data.tool,
            data.color,
            data.width,
            [point.model_dump() for point in data.points],
        )
        return WhiteboardStrokeResponse.model_validate(stroke)

    async def clear_strokes(self, user: User, session_id: uuid.UUID) -> None:
        session = await self._get_teacher_session(user, session_id)
        await self.repo.delete_strokes(session.id)

    async def undo_stroke(self, user: User, session_id: uuid.UUID) -> bool:
        session = await self._get_teacher_session(user, session_id)
        return await self.repo.delete_last_stroke(session.id)

    async def list_messages(
        self, user: User, session_id: uuid.UUID
    ) -> list[WhiteboardMessageResponse]:
        session = await self._get_active_accessible_session(user, session_id)
        rows = await self.repo.list_messages(session.id)
        return [
            self._message_response(message, sender, user.id)
            for message, sender in rows
        ]

    async def send_message(
        self, user: User, session_id: uuid.UUID, content: str
    ) -> WhiteboardMessageResponse:
        session = await self._get_active_accessible_session(user, session_id)
        message, sender = await self.repo.create_message(
            session.id, user.id, content.strip()
        )
        return self._message_response(message, sender, user.id)

    async def _get_accessible_course(
        self, user: User, course_id: uuid.UUID
    ) -> Course:
        course = await self.repo.get_course(course_id)
        if course is None or not await self.repo.can_access_course(user, course):
            raise HTTPException(status_code=404, detail="Course not found")
        return course

    async def _get_controller_course(self, user: User, course_id: uuid.UUID) -> Course:
        if user.role not in {UserRole.TEACHER, UserRole.ADMIN}:
            raise HTTPException(
                status_code=403,
                detail="Only teachers and admins can create a live class",
            )
        course = await self._get_accessible_course(user, course_id)
        return course

    async def _get_teacher_session(
        self, user: User, session_id: uuid.UUID
    ) -> WhiteboardSession:
        session = await self.repo.get_session(session_id)
        if session is None or not session.is_active:
            raise HTTPException(status_code=404, detail="Live whiteboard not found")
        if user.role == UserRole.ADMIN:
            return session
        course = await self.repo.get_course(session.course_id)
        if (
            user.role != UserRole.TEACHER
            or course is None
            or not await self.repo.can_access_course(user, course)
        ):
            raise HTTPException(
                status_code=403,
                detail="Only the assigned course teacher or an admin can control the board",
            )
        return session

    async def _get_active_accessible_session(
        self, user: User, session_id: uuid.UUID
    ) -> WhiteboardSession:
        session = await self.repo.get_session(session_id)
        if session is None or not session.is_active:
            raise HTTPException(status_code=404, detail="Live class not found")
        if user.role not in {UserRole.STUDENT, UserRole.TEACHER}:
            raise HTTPException(
                status_code=403,
                detail="Class chat is only available to enrolled students and the teacher",
            )
        course = await self.repo.get_course(session.course_id)
        if course is None or not await self.repo.can_access_course(user, course):
            raise HTTPException(
                status_code=403,
                detail="You are not a member of this live class",
            )
        return session

    @staticmethod
    def _session_response(
        session: WhiteboardSession,
        strokes: list[WhiteboardStroke] | None = None,
        strokes_are_snapshot: bool = True,
    ) -> WhiteboardSessionResponse:
        board_strokes = strokes if strokes is not None else session.strokes
        return WhiteboardSessionResponse(
            id=session.id,
            course_id=session.course_id,
            created_by=session.created_by,
            is_active=session.is_active,
            board_generation=session.board_generation,
            started_at=session.started_at,
            ended_at=session.ended_at,
            strokes=[
                WhiteboardStrokeResponse.model_validate(stroke)
                for stroke in board_strokes
            ],
            strokes_are_snapshot=strokes_are_snapshot,
        )

    @staticmethod
    def _message_response(
        message: WhiteboardMessage, sender: User, current_user_id: uuid.UUID
    ) -> WhiteboardMessageResponse:
        return WhiteboardMessageResponse(
            id=message.id,
            session_id=message.session_id,
            sender_id=sender.id,
            sender_name=sender.full_name,
            sender_role=sender.role,
            is_mine=sender.id == current_user_id,
            content=message.content,
            created_at=message.created_at,
            expires_at=message.expires_at,
        )
