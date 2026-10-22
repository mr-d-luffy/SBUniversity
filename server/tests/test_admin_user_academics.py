import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Department, UserVerificationStatus

ADMIN_AUTH = {"Authorization": "Bearer dev-token-admin-u_admin"}


@pytest.mark.asyncio
async def test_admin_updates_student_department_term_and_verification(
    client: AsyncClient,
    db_session: AsyncSession,
):
    department = Department(code="CSE", name="Computer Science")
    db_session.add(department)
    await db_session.commit()

    response = await client.patch(
        f"/admin/users/{db_session.test_student1.id}/academic-details",
        json={
            "department_id": str(department.id),
            "academic_term": "2026-2027 / Semester 3",
            "verification_status": "verified",
        },
        headers=ADMIN_AUTH,
    )

    assert response.status_code == 200, response.text
    profile = response.json()["student_profile"]
    assert profile["department_id"] == str(department.id)
    assert profile["academic_term"] == "2026-2027 / Semester 3"
    assert profile["verification_status"] == UserVerificationStatus.VERIFIED.value

    departments = await client.get("/admin/users/departments", headers=ADMIN_AUTH)
    assert departments.status_code == 200
    assert departments.json() == [
        {"id": str(department.id), "code": "CSE", "name": "Computer Science"}
    ]

    created_department = await client.post(
        "/admin/users/departments",
        json={"code": "BIO", "name": "Biology"},
        headers=ADMIN_AUTH,
    )
    assert created_department.status_code == 201
    assert created_department.json()["code"] == "BIO"

    assign_created_department = await client.patch(
        f"/admin/users/{db_session.test_student1.id}/academic-details",
        json={"department_id": created_department.json()["id"]},
        headers=ADMIN_AUTH,
    )
    assert assign_created_department.status_code == 200
    assert assign_created_department.json()["student_profile"]["department_id"] == created_department.json()["id"]

    duplicate_department = await client.post(
        "/admin/users/departments",
        json={"code": "BIO", "name": "Biology"},
        headers=ADMIN_AUTH,
    )
    assert duplicate_department.status_code == 409

    conflicting_code = await client.post(
        "/admin/users/departments",
        json={"code": "BIO", "name": "Another Department"},
        headers=ADMIN_AUTH,
    )
    assert conflicting_code.status_code == 409


@pytest.mark.asyncio
async def test_admin_can_update_teacher_department_and_verification(
    client: AsyncClient,
    db_session: AsyncSession,
):
    department = Department(code="MATH", name="Mathematics")
    db_session.add(department)
    await db_session.commit()

    response = await client.patch(
        f"/admin/users/{db_session.test_teacher.id}/academic-details",
        json={"department_id": str(department.id), "verification_status": "verified"},
        headers=ADMIN_AUTH,
    )
    assert response.status_code == 200
    assert response.json()["teacher_profile"]["department_id"] == str(department.id)
    assert response.json()["teacher_profile"]["verification_status"] == "verified"

    invalid_response = await client.patch(
        f"/admin/users/{db_session.test_teacher.id}/academic-details",
        json={"academic_term": "2026 Semester 3"},
        headers=ADMIN_AUTH,
    )
    assert invalid_response.status_code == 400


@pytest.mark.asyncio
async def test_admin_academic_update_repairs_missing_teacher_profile(
    client: AsyncClient,
    db_session: AsyncSession,
):
    db_session.test_teacher.teacher_profile = None
    await db_session.commit()

    response = await client.patch(
        f"/admin/users/{db_session.test_teacher.id}/academic-details",
        json={"verification_status": "verified"},
        headers=ADMIN_AUTH,
    )

    assert response.status_code == 200, response.text
    profile = response.json()["teacher_profile"]
    assert profile["employee_code"].startswith("T-")
    assert profile["verification_status"] == "verified"


@pytest.mark.asyncio
async def test_role_changed_to_teacher_can_be_edited(
    client: AsyncClient,
    db_session: AsyncSession,
):
    response = await client.patch(
        f"/admin/users/{db_session.test_student1.id}/role",
        json={"role": "teacher"},
        headers=ADMIN_AUTH,
    )
    assert response.status_code == 200
    assert response.json()["teacher_profile"] is not None

    academic_response = await client.patch(
        f"/admin/users/{db_session.test_student1.id}/academic-details",
        json={"verification_status": "verified"},
        headers=ADMIN_AUTH,
    )
    assert academic_response.status_code == 200
    assert academic_response.json()["teacher_profile"]["verification_status"] == "verified"
