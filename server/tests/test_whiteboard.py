from datetime import datetime, timedelta, timezone
from uuid import UUID

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Course, Enrollment, EnrollmentStatus
from app.db.models.whiteboard import WhiteboardMessage
from app.repositories.whiteboard_repository import WhiteboardRepository


def auth(user_id: str) -> dict[str, str]:
    role = {
        "u_admin": "admin",
        "u_teacher": "teacher",
        "u_student1": "student",
        "u_student2": "student",
    }[user_id]
    return {"Authorization": f"Bearer dev-token-{role}-{user_id}"}


async def create_course(db_session: AsyncSession) -> Course:
    course = Course(
        code="WB-101",
        title="Foundations of Whiteboarding",
        teacher_id=db_session.test_teacher.id,
        is_published=True,
    )
    db_session.add(course)
    await db_session.flush()
    db_session.add(
        Enrollment(
            student_id=db_session.test_student1.id,
            course_id=course.id,
            status=EnrollmentStatus.ACTIVE,
        )
    )
    await db_session.commit()
    await db_session.refresh(course)
    return course


@pytest.mark.asyncio
async def test_teacher_controls_board_and_enrolled_students_are_read_only(
    client: AsyncClient,
    db_session: AsyncSession,
):
    course = await create_course(db_session)

    listed = await client.get("/whiteboard/courses", headers=auth("u_teacher"))
    assert listed.status_code == 200
    assert listed.json() == [{
        "id": str(course.id),
        "code": course.code,
        "title": course.title,
        "is_live": False,
    }]

    not_enrolled = await client.get(
        "/whiteboard/courses", headers=auth("u_student2")
    )
    assert not_enrolled.status_code == 200
    assert not_enrolled.json() == []

    started = await client.post(
        f"/whiteboard/courses/{course.id}/sessions",
        headers=auth("u_teacher"),
    )
    assert started.status_code == 201
    session_id = started.json()["id"]
    assert started.json()["created_by"] == str(db_session.test_teacher.id)

    joined = await client.post(
        f"/whiteboard/courses/{course.id}/join",
        headers=auth("u_student1"),
    )
    assert joined.status_code == 200
    assert joined.json()["id"] == session_id

    un_enrolled_join = await client.post(
        f"/whiteboard/courses/{course.id}/join",
        headers=auth("u_student2"),
    )
    assert un_enrolled_join.status_code == 404

    student_session = await client.get(
        f"/whiteboard/courses/{course.id}/session",
        headers=auth("u_student1"),
    )
    assert student_session.status_code == 200
    assert student_session.json()["is_active"] is True

    stroke_data = {
        "tool": "pen",
        "color": "#173f38",
        "width": 4,
        "points": [{"x": 0.1, "y": 0.2}, {"x": 0.7, "y": 0.8}],
    }
    forbidden_stroke = await client.post(
        f"/whiteboard/sessions/{session_id}/strokes",
        headers=auth("u_student1"),
        json=stroke_data,
    )
    assert forbidden_stroke.status_code == 403

    created_stroke = await client.post(
        f"/whiteboard/sessions/{session_id}/strokes",
        headers=auth("u_teacher"),
        json=stroke_data,
    )
    assert created_stroke.status_code == 201
    assert created_stroke.json()["points"] == stroke_data["points"]

    synchronized = await client.get(
        f"/whiteboard/courses/{course.id}/session",
        headers=auth("u_student1"),
    )
    assert len(synchronized.json()["strokes"]) == 1
    assert synchronized.json()["strokes"][0]["tool"] == "pen"

    clear_forbidden = await client.delete(
        f"/whiteboard/sessions/{session_id}/strokes",
        headers=auth("u_student1"),
    )
    assert clear_forbidden.status_code == 403
    cleared = await client.delete(
        f"/whiteboard/sessions/{session_id}/strokes",
        headers=auth("u_teacher"),
    )
    assert cleared.status_code == 204

    ended = await client.post(
        f"/whiteboard/sessions/{session_id}/end",
        headers=auth("u_teacher"),
    )
    assert ended.status_code == 204
    no_live_session = await client.get(
        f"/whiteboard/courses/{course.id}/session",
        headers=auth("u_student1"),
    )
    assert no_live_session.status_code == 200
    assert no_live_session.json() is None


@pytest.mark.asyncio
async def test_live_chat_is_class_scoped_and_messages_expire_after_ten_minutes(
    client: AsyncClient,
    db_session: AsyncSession,
):
    course = await create_course(db_session)
    started = await client.post(
        f"/whiteboard/courses/{course.id}/sessions",
        headers=auth("u_teacher"),
    )
    session_id = started.json()["id"]

    posted = await client.post(
        f"/whiteboard/sessions/{session_id}/messages",
        headers=auth("u_student1"),
        json={"content": "Could you explain this step?"},
    )
    assert posted.status_code == 201
    message = posted.json()
    created_at = datetime.fromisoformat(message["created_at"].replace("Z", "+00:00"))
    expires_at = datetime.fromisoformat(message["expires_at"].replace("Z", "+00:00"))
    assert expires_at - created_at == timedelta(minutes=10)
    assert message["is_mine"] is True

    teacher_chat = await client.get(
        f"/whiteboard/sessions/{session_id}/messages",
        headers=auth("u_teacher"),
    )
    assert teacher_chat.status_code == 200
    assert teacher_chat.json()[0]["sender_name"] == "Student One"
    assert teacher_chat.json()[0]["is_mine"] is False

    teacher_message = await client.post(
        f"/whiteboard/sessions/{session_id}/messages",
        headers=auth("u_teacher"),
        json={"content": "I’ll go over that now."},
    )
    assert teacher_message.status_code == 201
    assert teacher_message.json()["is_mine"] is True

    not_member = await client.get(
        f"/whiteboard/sessions/{session_id}/messages",
        headers=auth("u_student2"),
    )
    assert not_member.status_code == 403

    admin_chat = await client.get(
        f"/whiteboard/sessions/{session_id}/messages",
        headers=auth("u_admin"),
    )
    assert admin_chat.status_code == 403

    stored = await db_session.scalar(
        select(WhiteboardMessage).where(WhiteboardMessage.id == UUID(message["id"]))
    )
    assert stored is not None
    expired_at = datetime.now(timezone.utc) - timedelta(seconds=1)
    stored.created_at = expired_at - timedelta(minutes=10)
    stored.expires_at = expired_at
    await db_session.commit()

    messages = await client.get(
        f"/whiteboard/sessions/{session_id}/messages",
        headers=auth("u_student1"),
    )
    assert messages.status_code == 200
    assert len(messages.json()) == 1
    assert messages.json()[0]["content"] == "I’ll go over that now."
    assert await db_session.scalar(
        select(WhiteboardMessage.id).where(
            WhiteboardMessage.id == UUID(message["id"])
        )
    ) == UUID(message["id"])
    assert await WhiteboardRepository(db_session).delete_expired_messages() == 1
    assert await db_session.scalar(
        select(WhiteboardMessage.id).where(
            WhiteboardMessage.id == UUID(message["id"])
        )
    ) is None


@pytest.mark.asyncio
async def test_admin_can_create_and_control_a_board_students_can_join(
    client: AsyncClient,
    db_session: AsyncSession,
):
    course = await create_course(db_session)

    student_start = await client.post(
        f"/whiteboard/courses/{course.id}/sessions",
        headers=auth("u_student1"),
    )
    assert student_start.status_code == 403

    admin_start = await client.post(
        f"/whiteboard/courses/{course.id}/sessions",
        headers=auth("u_admin"),
    )
    assert admin_start.status_code == 201
    session_id = admin_start.json()["id"]
    assert admin_start.json()["created_by"] == str(db_session.test_admin.id)

    admin_stroke = await client.post(
        f"/whiteboard/sessions/{session_id}/strokes",
        headers=auth("u_admin"),
        json={
            "tool": "line",
            "color": "#173f38",
            "width": 4,
            "points": [{"x": 0.1, "y": 0.2}, {"x": 0.7, "y": 0.8}],
        },
    )
    assert admin_stroke.status_code == 201

    teacher_stroke = await client.post(
        f"/whiteboard/sessions/{session_id}/strokes",
        headers=auth("u_teacher"),
        json={
            "tool": "line",
            "color": "#173f38",
            "width": 4,
            "points": [{"x": 0.1, "y": 0.2}, {"x": 0.7, "y": 0.8}],
        },
    )
    assert teacher_stroke.status_code == 201

    student_join = await client.post(
        f"/whiteboard/courses/{course.id}/join",
        headers=auth("u_student1"),
    )
    assert student_join.status_code == 200
    assert len(student_join.json()["strokes"]) == 2

    wrong_course = await client.get(
        f"/whiteboard/courses/{course.id}/session",
        headers=auth("u_student2"),
    )
    assert wrong_course.status_code == 404

    student_join_wrong_course = await client.post(
        f"/whiteboard/courses/{course.id}/join",
        headers=auth("u_student2"),
    )
    assert student_join_wrong_course.status_code == 404


@pytest.mark.asyncio
async def test_board_sync_sends_only_new_strokes_until_clear_requires_snapshot(
    client: AsyncClient,
    db_session: AsyncSession,
):
    course = await create_course(db_session)
    started = await client.post(
        f"/whiteboard/courses/{course.id}/sessions",
        headers=auth("u_teacher"),
    )
    session_id = started.json()["id"]

    initial = await client.get(
        f"/whiteboard/courses/{course.id}/session",
        headers=auth("u_student1"),
    )
    initial_state = initial.json()
    assert initial_state["strokes_are_snapshot"] is True
    assert initial_state["strokes"] == []

    unchanged = await client.get(
        f"/whiteboard/courses/{course.id}/session",
        params={"board_generation": initial_state["board_generation"]},
        headers=auth("u_student1"),
    )
    assert unchanged.status_code == 200
    assert unchanged.json()["strokes_are_snapshot"] is True
    assert unchanged.json()["strokes"] == []

    stroke_data = {
        "tool": "pen",
        "color": "#173f38",
        "width": 4,
        "points": [{"x": 0.1, "y": 0.2}, {"x": 0.7, "y": 0.8}],
    }
    created = await client.post(
        f"/whiteboard/sessions/{session_id}/strokes",
        headers=auth("u_teacher"),
        json=stroke_data,
    )
    assert created.status_code == 201
    stroke_id = created.json()["id"]

    new_stroke = await client.get(
        f"/whiteboard/courses/{course.id}/session",
        params={
            "board_generation": initial_state["board_generation"],
        },
        headers=auth("u_student1"),
    )
    assert new_stroke.json()["strokes_are_snapshot"] is True
    assert len(new_stroke.json()["strokes"]) == 1

    second_created = await client.post(
        f"/whiteboard/sessions/{session_id}/strokes",
        headers=auth("u_teacher"),
        json=stroke_data,
    )
    assert second_created.status_code == 201
    delta = await client.get(
        f"/whiteboard/courses/{course.id}/session",
        params={
            "board_generation": new_stroke.json()["board_generation"],
            "after_stroke_id": stroke_id,
        },
        headers=auth("u_student1"),
    )
    assert delta.status_code == 200
    assert delta.json()["strokes_are_snapshot"] is False
    assert [stroke["id"] for stroke in delta.json()["strokes"]] == [
        second_created.json()["id"]
    ]

    await client.delete(
        f"/whiteboard/sessions/{session_id}/strokes",
        headers=auth("u_teacher"),
    )
    after_clear = await client.get(
        f"/whiteboard/courses/{course.id}/session",
        params={
            "board_generation": new_stroke.json()["board_generation"],
            "after_stroke_id": stroke_id,
        },
        headers=auth("u_student1"),
    )
    assert after_clear.status_code == 200
    assert after_clear.json()["board_generation"] == initial_state["board_generation"] + 1
    assert after_clear.json()["strokes_are_snapshot"] is True
    assert after_clear.json()["strokes"] == []


@pytest.mark.asyncio
async def test_whiteboard_rejects_invalid_stroke_and_blank_chat(
    client: AsyncClient,
    db_session: AsyncSession,
):
    course = await create_course(db_session)
    started = await client.post(
        f"/whiteboard/courses/{course.id}/sessions",
        headers=auth("u_teacher"),
    )
    session_id = started.json()["id"]

    invalid_stroke = await client.post(
        f"/whiteboard/sessions/{session_id}/strokes",
        headers=auth("u_teacher"),
        json={
            "tool": "pen",
            "color": "green",
            "width": 4,
            "points": [{"x": 0.1, "y": 0.2}, {"x": 0.7, "y": 0.8}],
        },
    )
    assert invalid_stroke.status_code == 422

    blank_message = await client.post(
        f"/whiteboard/sessions/{session_id}/messages",
        headers=auth("u_student1"),
        json={"content": "  "},
    )
    assert blank_message.status_code == 422
