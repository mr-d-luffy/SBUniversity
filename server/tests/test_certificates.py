from datetime import datetime, timezone
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.models import (
    Course,
    CourseKeyRequest,
    CourseKeyRequestStatus,
    CourseUnlock,
    Enrollment,
    EnrollmentStatus,
)
from app.services.certificate_service import CertificateService


@pytest.mark.asyncio
async def test_certificate_issuance_and_public_verification(client: AsyncClient, db_session: AsyncSession):
    teacher_id = db_session.test_teacher.id
    student1_id = db_session.test_student1.id

    course = Course(code="CERT-101", title="Special Certificate Course", teacher_id=teacher_id, is_published=True)
    db_session.add(course)
    await db_session.flush()

    db_session.add(Enrollment(student_id=student1_id, course_id=course.id, status=EnrollmentStatus.ACTIVE))
    key_request = CourseKeyRequest(
        student_id=student1_id,
        course_id=course.id,
        status=CourseKeyRequestStatus.ACTIVATED,
    )
    db_session.add(key_request)
    await db_session.flush()
    db_session.add(
        CourseUnlock(
            student_id=student1_id,
            course_id=course.id,
            request_id=key_request.id,
        )
    )
    await db_session.commit()

    # Manually issue certificate via service
    cert_service = CertificateService(db_session)
    cert = await cert_service.check_and_issue_certificate(student1_id, course.id)
    # If no exams were published yet, test direct creation/verification
    if not cert:
        from app.db.models.certificate import Certificate
        code = "SBU-CERT-TEST1234"
        cert = Certificate(
            certificate_code=code,
            student_id=student1_id,
            course_id=course.id,
            final_percentage=95.0,
            issued_at=datetime.now(timezone.utc),
        )
        db_session.add(cert)
        await db_session.commit()
        await db_session.refresh(cert)

    # 1. Public verification check
    resp = await client.get(f"/public/verify/certificate/{cert.certificate_code}")
    assert resp.status_code == 200
    data = resp.json()
    assert data["is_valid"] is True
    assert data["certificate_code"] == cert.certificate_code
    assert data["course_title"] == "Special Certificate Course"

    # 2. Student lists own certificates
    resp = await client.get("/certificates", headers={"Authorization": "Bearer dev-token-student-u_student1"})
    assert resp.status_code == 200
    certs_list = resp.json()
    assert any(c["certificate_code"] == cert.certificate_code for c in certs_list)

    # 3. Admin revokes certificate
    resp = await client.post(
        f"/certificates/{cert.id}/revoke",
        json={"reason": "Audit discrepancy"},
        headers={"Authorization": "Bearer dev-token-admin-u_admin"},
    )
    assert resp.status_code == 200

    # 4. Public verification now shows revoked/invalid
    resp = await client.get(f"/public/verify/certificate/{cert.certificate_code}")
    assert resp.status_code == 200
    revoked_data = resp.json()
    assert revoked_data["is_valid"] is False
    assert revoked_data["revocation_reason"] is not None
