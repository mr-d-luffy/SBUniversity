import pytest
from httpx import AsyncClient
from app.db.models.user import UserRole


@pytest.mark.asyncio
async def test_unauthenticated_request_rejected(client: AsyncClient):
    resp = await client.get("/me")
    assert resp.status_code == 401
    data = resp.json()
    assert "error" in data
    assert data["error"]["code"] == "UNAUTHORIZED"


@pytest.mark.asyncio
async def test_get_me_student(client: AsyncClient):
    resp = await client.get("/me", headers={"Authorization": "Bearer dev-token-student-u_student1"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["email"] == "student1@sbuniversity.edu"
    assert data["role"] == "student"


@pytest.mark.asyncio
async def test_student_id_card_includes_admin_managed_academic_details(client: AsyncClient, db_session):
    from app.db.models.user import UserVerificationStatus

    profile = db_session.test_student1.student_profile
    profile.academic_term = "2026-2027 / Semester 3"
    profile.verification_status = UserVerificationStatus.VERIFIED
    await db_session.commit()

    response = await client.get(
        "/student/id-card",
        headers={"Authorization": "Bearer dev-token-student-u_student1"},
    )

    assert response.status_code == 200
    assert response.json()["academic_term"] == "2026-2027 / Semester 3"
    assert response.json()["verification_status"] == "verified"


@pytest.mark.asyncio
async def test_database_role_is_authoritative_over_stale_token_metadata(
    client: AsyncClient,
    db_session,
):
    db_session.test_student1.role = UserRole.TEACHER
    await db_session.commit()

    response = await client.get(
        "/me",
        headers={"Authorization": "Bearer dev-token-student-u_student1"},
    )

    assert response.status_code == 200
    assert response.json()["role"] == "teacher"


@pytest.mark.asyncio
async def test_role_change_fails_without_clerk_sync_and_keeps_database_role(
    client: AsyncClient,
    db_session,
    monkeypatch: pytest.MonkeyPatch,
):
    from app.core.config import settings

    class ClerkResponse:
        status_code = 500

    class ClerkClient:
        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, traceback):
            return None

        async def patch(self, url: str, headers: dict[str, str], json: dict[str, str]):
            return ClerkResponse()

    monkeypatch.setattr(settings, "CLERK_SECRET_KEY", "test-secret")
    monkeypatch.setattr(
        "app.services.user_service.httpx.AsyncClient",
        lambda timeout: ClerkClient(),
    )

    response = await client.patch(
        f"/admin/users/{db_session.test_student1.id}/role",
        json={"role": "teacher"},
        headers={"Authorization": "Bearer dev-token-admin-u_admin"},
    )

    assert response.status_code == 502
    assert db_session.test_student1.role == UserRole.STUDENT


@pytest.mark.asyncio
async def test_first_login_provisions_student_profile_without_lazy_load(client: AsyncClient):
    resp = await client.get(
        "/me",
        headers={"Authorization": "Bearer dev-token-student-first_login_regression"},
    )

    assert resp.status_code == 200
    data = resp.json()
    assert data["clerk_user_id"] == "first_login_regression"
    assert data["role"] == "student"
    assert data["student_profile"] is not None
    assert data["student_profile"]["student_code"]


@pytest.mark.asyncio
async def test_first_login_student_code_uses_highest_existing_code(client: AsyncClient, db_session):
    db_session.test_student2.student_profile.student_code = "SBU-2026-0012"
    await db_session.commit()

    resp = await client.get(
        "/me",
        headers={"Authorization": "Bearer dev-token-student-student_code_gap"},
    )

    assert resp.status_code == 200
    assert resp.json()["student_profile"]["student_code"] == "SBU-2026-0013"


@pytest.mark.asyncio
async def test_student_cannot_access_admin_routes(client: AsyncClient):
    resp = await client.get("/admin/users", headers={"Authorization": "Bearer dev-token-student-u_student1"})
    assert resp.status_code == 403
    data = resp.json()
    assert data["error"]["code"] == "FORBIDDEN"


@pytest.mark.asyncio
async def test_admin_can_access_admin_routes(client: AsyncClient):
    resp = await client.get("/admin/users", headers={"Authorization": "Bearer dev-token-admin-u_admin"})
    assert resp.status_code == 200
    data = resp.json()
    assert "items" in data
    assert len(data["items"]) >= 4


@pytest.mark.asyncio
async def test_admin_change_role_and_student_profile(client: AsyncClient):
    # Find student user
    users_resp = await client.get("/admin/users", headers={"Authorization": "Bearer dev-token-admin-u_admin"})
    student = next(u for u in users_resp.json()["items"] if u["role"] == "student")
    student_id = student["id"]

    # Change role to teacher
    resp1 = await client.patch(
        f"/admin/users/{student_id}/role",
        json={"role": "teacher"},
        headers={"Authorization": "Bearer dev-token-admin-u_admin"},
    )
    assert resp1.status_code == 200
    assert resp1.json()["role"] == "teacher"
    assert resp1.json()["teacher_profile"] is not None
    assert resp1.json()["teacher_profile"]["employee_code"]

    # Change role back to student
    resp2 = await client.patch(
        f"/admin/users/{student_id}/role",
        json={"role": "student"},
        headers={"Authorization": "Bearer dev-token-admin-u_admin"},
    )
    assert resp2.status_code == 200
    data = resp2.json()
    assert data["role"] == "student"
    assert data["student_profile"] is not None


@pytest.mark.asyncio
async def test_update_student_profile(client: AsyncClient):
    resp = await client.patch(
        "/me",
        json={"phone": "+91 99999 88888"},
        headers={"Authorization": "Bearer dev-token-student-u_student1"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["student_profile"] is not None
    assert data["student_profile"]["phone"] == "+91 99999 88888"
