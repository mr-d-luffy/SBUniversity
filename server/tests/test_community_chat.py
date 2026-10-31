import uuid
from base64 import b64encode
from datetime import datetime, timedelta, timezone

import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import (
    CommunityConversation,
    CommunityMessage,
)
from app.services.storage_service import StorageService

ENCRYPTED_CONTENT = "e2ee:v1:AAAA"


def chat_public_key() -> str:
    key = rsa.generate_private_key(public_exponent=65537, key_size=3072)
    encoded = key.public_key().public_bytes(
        serialization.Encoding.DER,
        serialization.PublicFormat.SubjectPublicKeyInfo,
    )
    return b64encode(encoded).decode("ascii")


def auth(user_id: str) -> dict[str, str]:
    return {"Authorization": f"Bearer dev-token-{user_id}"}


@pytest.mark.asyncio
async def test_students_can_use_room_and_private_direct_chat(
    client: AsyncClient,
    db_session: AsyncSession,
):
    student_one = auth("student-u_student1")
    student_two = auth("student-u_student2")

    room_list = await client.get("/community-chat/conversations", headers=student_one)
    assert room_list.status_code == 200
    room = next(item for item in room_list.json() if item["is_shared_room"])

    sent_room_message = await client.post(
        f"/community-chat/conversations/{room['id']}/messages",
        json={"content": ENCRYPTED_CONTENT},
        headers=student_one,
    )
    assert sent_room_message.status_code == 200

    room_messages = await client.get(
        f"/community-chat/conversations/{room['id']}/messages",
        headers=student_two,
    )
    assert room_messages.status_code == 200
    assert room_messages.json()[0]["content"] == ENCRYPTED_CONTENT
    assert room_messages.json()[0]["sender_name"] == db_session.test_student1.full_name

    direct = await client.post(
        f"/community-chat/direct/{db_session.test_student2.id}",
        headers=student_one,
    )
    assert direct.status_code == 200
    direct_id = direct.json()["id"]

    duplicate = await client.post(
        f"/community-chat/direct/{db_session.test_student1.id}",
        headers=student_two,
    )
    assert duplicate.status_code == 200
    assert duplicate.json()["id"] == direct_id

    direct_message = await client.post(
        f"/community-chat/conversations/{direct_id}/messages",
        json={"content": ENCRYPTED_CONTENT},
        headers=student_one,
    )
    assert direct_message.status_code == 200
    visible_to_recipient = await client.get(
        f"/community-chat/conversations/{direct_id}/messages",
        headers=student_two,
    )
    assert visible_to_recipient.status_code == 200
    assert visible_to_recipient.json()[0]["content"] == ENCRYPTED_CONTENT

    forbidden = await client.get(
        f"/community-chat/conversations/{direct_id}/messages",
        headers=auth("teacher-u_teacher"),
    )
    assert forbidden.status_code == 404

    duplicate_message = await client.post(
        f"/community-chat/conversations/{direct_id}/messages",
        json={"content": "   "},
        headers=student_one,
    )
    assert duplicate_message.status_code == 422
    plaintext_message = await client.post(
        f"/community-chat/conversations/{direct_id}/messages",
        json={"content": "This must never be stored as plaintext."},
        headers=student_one,
    )
    assert plaintext_message.status_code == 422


@pytest.mark.asyncio
async def test_chat_key_envelopes_are_scoped_to_conversation_participants(
    client: AsyncClient,
    db_session: AsyncSession,
):
    student_one = auth("student-u_student1")
    student_two = auth("student-u_student2")
    direct = await client.post(
        f"/community-chat/direct/{db_session.test_student2.id}",
        headers=student_one,
    )
    conversation_id = direct.json()["id"]
    first_device_id = str(uuid.uuid4())
    second_device_id = str(uuid.uuid4())
    invalid_registration = await client.post(
        "/community-chat/devices",
        json={"device_id": str(uuid.uuid4()), "public_key": "A" * 64},
        headers=student_one,
    )
    assert invalid_registration.status_code == 422
    for device_id, headers in ((first_device_id, student_one), (second_device_id, student_two)):
        registration = await client.post(
            "/community-chat/devices",
            json={"device_id": device_id, "public_key": chat_public_key()},
            headers=headers,
        )
        assert registration.status_code == 201

    directory = await client.get(
        f"/community-chat/conversations/{conversation_id}/devices",
        headers=student_one,
    )
    assert {device["device_id"] for device in directory.json()} == {
        first_device_id,
        second_device_id,
    }

    key_id = str(uuid.uuid4())
    envelope = [{
        "key_id": key_id,
        "device_id": second_device_id,
        "wrapped_key": "B" * 64,
    }]
    stored = await client.post(
        f"/community-chat/conversations/{conversation_id}/keys"
        f"?sender_device_id={first_device_id}",
        json=envelope,
        headers=student_one,
    )
    assert stored.status_code == 204
    duplicate_store = await client.post(
        f"/community-chat/conversations/{conversation_id}/keys"
        f"?sender_device_id={first_device_id}",
        json=[{**envelope[0], "wrapped_key": "D" * 64}],
        headers=student_one,
    )
    assert duplicate_store.status_code == 204
    recipient_keys = await client.get(
        f"/community-chat/conversations/{conversation_id}/keys",
        headers=student_two,
    )
    assert recipient_keys.status_code == 200
    assert recipient_keys.json()[0]["key_id"] == key_id
    assert recipient_keys.json()[0]["wrapped_key"] == "B" * 64

    outsider = await client.get(
        f"/community-chat/conversations/{conversation_id}/keys",
        headers=auth("teacher-u_teacher"),
    )
    assert outsider.status_code == 404
    rejected_recipient = await client.post(
        f"/community-chat/conversations/{conversation_id}/keys"
        f"?sender_device_id={first_device_id}",
        json=[{
            "key_id": str(uuid.uuid4()),
            "device_id": str(uuid.uuid4()),
            "wrapped_key": "C" * 64,
        }],
        headers=student_one,
    )
    assert rejected_recipient.status_code == 403


@pytest.mark.asyncio
async def test_voice_messages_require_encrypted_payloads(
    client: AsyncClient,
    db_session: AsyncSession,
    monkeypatch: pytest.MonkeyPatch,
):
    headers = auth("student-u_student1")
    direct = await client.post(
        f"/community-chat/direct/{db_session.test_student2.id}",
        headers=headers,
    )
    conversation_id = direct.json()["id"]
    stored_audio: dict[str, bytes] = {}

    async def upload(path: str, content: bytes, content_type: str) -> str:
        assert content_type == "application/octet-stream"
        stored_audio[path] = content
        return path

    async def download(path: str) -> bytes | None:
        return stored_audio.get(path)

    monkeypatch.setattr(StorageService, "upload_file", upload)
    monkeypatch.setattr(StorageService, "download_file", download)

    clear_audio = await client.post(
        f"/community-chat/conversations/{conversation_id}/audio?media_type=audio/webm",
        headers=headers,
        files={"file": ("voice.webm", b"clear audio", "audio/webm")},
    )
    assert clear_audio.status_code == 415

    key_id = str(uuid.uuid4()).encode("ascii")
    encrypted_audio = b"SBU-E2EE-v1!" + (b"\x00" * 12) + key_id + (b"\x00" * 16)
    uploaded = await client.post(
        f"/community-chat/conversations/{conversation_id}/audio?media_type=audio/webm",
        headers=headers,
        files={
            "file": (
                "voice.enc",
                encrypted_audio,
                "application/octet-stream",
            )
        },
    )
    assert uploaded.status_code == 201
    message = uploaded.json()
    assert message["audio_size_bytes"] == len(encrypted_audio)
    assert message["audio_mime_type"] == "audio/webm"
    assert stored_audio

    playback = await client.get(message["audio_url"], headers=headers)
    assert playback.status_code == 200
    assert playback.content == encrypted_audio
    assert playback.headers["content-type"] == "application/octet-stream"


@pytest.mark.asyncio
async def test_staff_buttons_create_role_scoped_support_inboxes(
    client: AsyncClient,
    db_session: AsyncSession,
):
    student = auth("student-u_student1")
    admin = auth("admin-u_admin")
    teacher = auth("teacher-u_teacher")

    admin_thread = await client.post(
        "/community-chat/staff/admin",
        headers=student,
    )
    teacher_thread = await client.post(
        "/community-chat/staff/teacher",
        headers=student,
    )
    assert admin_thread.status_code == 200
    assert teacher_thread.status_code == 200
    assert admin_thread.json()["kind"] == "admin_support"
    assert teacher_thread.json()["kind"] == "teacher_support"
    assert admin_thread.json()["id"] != teacher_thread.json()["id"]

    wrong_staff_role = await client.get(
        f"/community-chat/conversations/{admin_thread.json()['id']}/messages",
        headers=teacher,
    )
    assert wrong_staff_role.status_code == 404

    message = await client.post(
        f"/community-chat/conversations/{admin_thread.json()['id']}/messages",
        json={"content": ENCRYPTED_CONTENT},
        headers=student,
    )
    assert message.status_code == 200

    admin_inbox = await client.get("/community-chat/conversations", headers=admin)
    teacher_inbox = await client.get("/community-chat/conversations", headers=teacher)
    assert admin_thread.json()["id"] in {item["id"] for item in admin_inbox.json()}
    assert admin_thread.json()["id"] not in {item["id"] for item in teacher_inbox.json()}

    admin_reply = await client.post(
        f"/community-chat/conversations/{admin_thread.json()['id']}/messages",
        json={"content": ENCRYPTED_CONTENT},
        headers=admin,
    )
    assert admin_reply.status_code == 200
    assert admin_reply.json()["sender_role"] == "admin"

    student_messages = await client.get(
        f"/community-chat/conversations/{admin_thread.json()['id']}/messages",
        headers=student,
    )
    assert len(student_messages.json()) == 2
    assert student_messages.json()[1]["content"] == ENCRYPTED_CONTENT


@pytest.mark.asyncio
async def test_expired_conversations_and_messages_are_deleted(
    client: AsyncClient,
    db_session: AsyncSession,
):
    created = await client.post(
        f"/community-chat/direct/{db_session.test_student2.id}",
        headers=auth("student-u_student1"),
    )
    assert created.status_code == 200
    conversation_id = uuid.UUID(created.json()["id"])

    message = await client.post(
        f"/community-chat/conversations/{conversation_id}/messages",
        json={"content": ENCRYPTED_CONTENT},
        headers=auth("student-u_student1"),
    )
    assert message.status_code == 200

    conversation = await db_session.get(CommunityConversation, conversation_id)
    assert conversation is not None
    expires_at = conversation.expires_at
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    assert expires_at > datetime.now(timezone.utc)
    conversation.expires_at = datetime.now(timezone.utc) - timedelta(seconds=1)
    await db_session.commit()

    messages = await client.get(
        f"/community-chat/conversations/{conversation_id}/messages",
        headers=auth("student-u_student1"),
    )
    assert messages.status_code == 404
    db_session.expire_all()
    assert await db_session.get(CommunityConversation, conversation_id) is None
    stored_messages = (
        await db_session.execute(
            select(CommunityMessage).where(
                CommunityMessage.conversation_id == conversation_id
            )
        )
    ).scalars().all()
    assert stored_messages == []


@pytest.mark.asyncio
async def test_students_directory_only_returns_other_active_students(
    client: AsyncClient,
    db_session: AsyncSession,
):
    response = await client.get(
        "/community-chat/students",
        headers=auth("student-u_student1"),
    )
    assert response.status_code == 200
    assert {item["id"] for item in response.json()} == {
        str(db_session.test_student2.id)
    }

    staff_response = await client.get(
        "/community-chat/students",
        headers=auth("teacher-u_teacher"),
    )
    assert staff_response.status_code == 403
