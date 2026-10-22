from datetime import datetime, timezone
import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.models import PlannerEntry, PlannerEntryKind
from app.services.storage_service import StorageService


def auth(user_id: str) -> dict[str, str]:
    return {"Authorization": f"Bearer dev-token-{user_id}"}


@pytest.mark.asyncio
async def test_planner_entries_are_private_for_every_role(
    client: AsyncClient,
    db_session: AsyncSession,
):
    for user_id in ("student-u_student1", "teacher-u_teacher", "admin-u_admin"):
        response = await client.post(
            "/planner/entries",
            headers=auth(user_id),
            json={
                "kind": "learning_plan",
                "title": f"Plan for {user_id}",
                "content": "Read chapter one",
            },
        )
        assert response.status_code == 201
        assert response.json()["kind"] == "learning_plan"
        assert response.json()["is_completed"] is False

    student_entries = await client.get(
        "/planner/entries", headers=auth("student-u_student1")
    )
    teacher_entries = await client.get(
        "/planner/entries", headers=auth("teacher-u_teacher")
    )
    admin_entries = await client.get(
        "/planner/entries", headers=auth("admin-u_admin")
    )
    assert len(student_entries.json()) == 1
    assert len(teacher_entries.json()) == 1
    assert len(admin_entries.json()) == 1

    student_entry_id = student_entries.json()[0]["id"]
    forbidden_update = await client.patch(
        f"/planner/entries/{student_entry_id}",
        headers=auth("teacher-u_teacher"),
        json={"title": "Trying to change another user's plan"},
    )
    forbidden_delete = await client.delete(
        f"/planner/entries/{student_entry_id}",
        headers=auth("admin-u_admin"),
    )
    assert forbidden_update.status_code == 404
    assert forbidden_delete.status_code == 404

    completed = await client.patch(
        f"/planner/entries/{student_entry_id}",
        headers=auth("student-u_student1"),
        json={"is_completed": True},
    )
    assert completed.status_code == 200
    assert completed.json()["is_completed"] is True

    db_entries = (await db_session.execute(select(PlannerEntry))).scalars().all()
    assert len(db_entries) == 3


@pytest.mark.asyncio
async def test_sticky_note_and_event_fields_are_validated_and_persisted(
    client: AsyncClient,
):
    headers = auth("student-u_student1")
    sticky = await client.post(
        "/planner/entries",
        headers=headers,
        json={
            "kind": "sticky_note",
            "title": "Remember",
            "content": "Review the lecture notes",
            "color": "#fce7f3",
            "shape": "cloud",
            "emoji": "💡",
        },
    )
    assert sticky.status_code == 201
    assert sticky.json()["color"] == "#fce7f3"
    assert sticky.json()["shape"] == "cloud"
    assert sticky.json()["emoji"] == "💡"

    event_without_date = await client.post(
        "/planner/entries",
        headers=headers,
        json={"kind": "event", "title": "Study session"},
    )
    assert event_without_date.status_code == 422

    event = await client.post(
        "/planner/entries",
        headers=headers,
        json={
            "kind": "event",
            "title": "Study session",
            "due_at": datetime(2026, 10, 20, 10, 0, tzinfo=timezone.utc).isoformat(),
        },
    )
    assert event.status_code == 201
    assert event.json()["due_at"] is not None

    invalid_color = await client.post(
        "/planner/entries",
        headers=headers,
        json={"kind": "sticky_note", "title": "Bad color", "color": "green"},
    )
    assert invalid_color.status_code == 422


@pytest.mark.asyncio
async def test_voice_notes_are_private_and_audio_is_authenticated(
    client: AsyncClient,
    monkeypatch: pytest.MonkeyPatch,
):
    objects: dict[str, bytes] = {}
    audio_bytes = b"\x1a\x45\xdf\xa3test-audio-data"

    async def upload(path: str, content: bytes, content_type: str) -> str:
        objects[path] = content
        return path

    async def download(path: str):
        return objects.get(path)

    async def delete(path: str) -> None:
        objects.pop(path, None)

    monkeypatch.setattr(StorageService, "upload_file", upload)
    monkeypatch.setattr(StorageService, "download_file", download)
    monkeypatch.setattr(StorageService, "delete_file", delete)

    created = await client.post(
        "/planner/entries/voice-note?title=Lecture%20thought",
        headers=auth("student-u_student1"),
        files={"file": ("thought.webm", audio_bytes, "audio/webm")},
    )
    assert created.status_code == 201
    note = created.json()
    assert note["kind"] == PlannerEntryKind.VOICE_NOTE.value
    assert note["audio_size_bytes"] == len(audio_bytes)

    playback = await client.get(
        note["audio_url"], headers=auth("student-u_student1")
    )
    assert playback.status_code == 200
    assert playback.content == audio_bytes
    assert playback.headers["content-type"] == "audio/webm"

    forbidden = await client.get(
        note["audio_url"], headers=auth("teacher-u_teacher")
    )
    assert forbidden.status_code == 404

    deleted = await client.delete(
        f"/planner/entries/{note['id']}", headers=auth("student-u_student1")
    )
    assert deleted.status_code == 204
    assert objects == {}

    unsupported = await client.post(
        "/planner/entries/voice-note",
        headers=auth("student-u_student1"),
        files={"file": ("document.txt", b"not audio", "text/plain")},
    )
    assert unsupported.status_code == 415

    empty_title = await client.post(
        "/planner/entries/voice-note?title=%20%20",
        headers=auth("student-u_student1"),
        files={"file": ("thought.webm", audio_bytes, "audio/webm")},
    )
    assert empty_title.status_code == 422
    assert len(objects) == 0
