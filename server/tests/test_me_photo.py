import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession


@pytest.mark.asyncio
async def test_student_can_load_stored_avatar(
    client: AsyncClient,
    db_session: AsyncSession,
    monkeypatch: pytest.MonkeyPatch,
):
    db_session.test_student1.avatar_url = "avatars/student.jpg"
    await db_session.commit()

    async def download_file(path: str) -> bytes | None:
        assert path == "avatars/student.jpg"
        return b"image-bytes"

    monkeypatch.setattr("app.api.v1.me.StorageService.download_file", download_file)

    response = await client.get(
        "/me/photo",
        headers={"Authorization": "Bearer dev-token-student-u_student1"},
    )

    assert response.status_code == 200
    assert response.headers["content-type"] == "image/jpeg"
    assert response.headers["cache-control"] == "private, no-store"
    assert response.content == b"image-bytes"


@pytest.mark.asyncio
async def test_student_photo_not_found_when_no_avatar(
    client: AsyncClient,
    db_session: AsyncSession,
):
    response = await client.get(
        "/me/photo",
        headers={"Authorization": "Bearer dev-token-student-u_student1"},
    )

    assert response.status_code == 404
