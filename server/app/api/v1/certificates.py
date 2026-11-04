import uuid
from typing import List
from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.deps import get_current_user, require_role
from app.db.models.user import User, UserRole
from app.db.session import get_db
from app.repositories.certificate_repository import CertificateRepository
from app.schemas.certificate import CertificateResponse, RevokeCertificateRequest
from app.services.certificate_service import CertificateService
from app.services.course_access_service import is_course_unlocked, unlocked_course_ids

router = APIRouter(prefix="/certificates", tags=["Certificates"])


@router.get("", response_model=List[CertificateResponse])
async def list_certificates(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    repo = CertificateRepository(db)
    if current_user.role == UserRole.STUDENT:
        certs, _ = await repo.list_certificates(student_id=current_user.id, include_revoked=True)
        unlocked_ids = await unlocked_course_ids(db, current_user.id)
        certs = [certificate for certificate in certs if certificate.course_id in unlocked_ids]
    else:
        certs, _ = await repo.list_certificates()

    res = []
    for c in certs:
        resp = CertificateResponse.model_validate(c)
        resp.course_title = c.course.title if c.course else "Course"
        resp.student_name = c.student.full_name if c.student else "Student"
        res.append(resp)
    return res


@router.get("/{certificate_id}", response_model=CertificateResponse)
async def get_certificate(
    certificate_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    repo = CertificateRepository(db)
    cert = await repo.get_by_id(certificate_id)
    if not cert:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Certificate not found")

    if current_user.role == UserRole.STUDENT and cert.student_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
    if current_user.role == UserRole.STUDENT and not await is_course_unlocked(
        db, current_user.id, cert.course_id
    ):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Certificate not found")

    resp = CertificateResponse.model_validate(cert)
    resp.course_title = cert.course.title if cert.course else "Course"
    resp.student_name = cert.student.full_name if cert.student else "Student"
    return resp


@router.get("/{certificate_id}/pdf")
async def download_certificate_pdf(
    certificate_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    repo = CertificateRepository(db)
    cert = await repo.get_by_id(certificate_id)
    if not cert:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Certificate not found")

    if current_user.role == UserRole.STUDENT and cert.student_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
    if current_user.role == UserRole.STUDENT and not await is_course_unlocked(
        db, current_user.id, cert.course_id
    ):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Certificate not found")

    service = CertificateService(db)
    pdf_bytes = await service.get_or_generate_certificate_pdf(certificate_id)

    filename = f"certificate-{cert.certificate_code}.pdf"
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.post("/{certificate_id}/revoke", response_model=CertificateResponse)
async def revoke_certificate(
    certificate_id: uuid.UUID,
    body: RevokeCertificateRequest,
    current_user: User = Depends(require_role(UserRole.ADMIN)),
    db: AsyncSession = Depends(get_db),
):
    service = CertificateService(db)
    cert = await service.revoke_certificate(certificate_id, current_user, body.reason)
    return cert
