import secrets
import uuid
from datetime import UTC, datetime

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import logger
from app.db.models.certificate import Certificate
from app.db.models.course import EnrollmentStatus
from app.db.models.exam import Exam, ExamStatus
from app.db.models.result import Result
from app.db.models.user import User, UserRole
from app.repositories.audit_repository import AuditRepository
from app.repositories.certificate_repository import CertificateRepository
from app.repositories.course_repository import CourseRepository
from app.repositories.result_repository import ResultRepository
from app.repositories.user_repository import UserRepository
from app.schemas.certificate import VerifyCertificateResponse
from app.services.pdf_service import PDFService
from app.services.storage_service import StorageService


def generate_certificate_code() -> str:
    alphabet = "23456789ABCDEFGHJKLMNPQRSTUVWXYZ"
    code = "".join(secrets.choice(alphabet) for _ in range(8))
    return f"SBU-CERT-{code}"


class CertificateService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.cert_repo = CertificateRepository(db)
        self.course_repo = CourseRepository(db)
        self.user_repo = UserRepository(db)
        self.result_repo = ResultRepository(db)
        self.audit_repo = AuditRepository(db)

    async def check_and_issue_certificate(self, student_id: uuid.UUID, course_id: uuid.UUID) -> Certificate | None:
        """
        Completion rule: all published exams of the course passed -> certificate issued.
        """
        # Check if already issued
        existing = await self.cert_repo.get_by_student_and_course(student_id, course_id)
        if existing:
            return existing

        # Count published exams for course
        stmt_exams = select(Exam).where(Exam.course_id == course_id, Exam.status == ExamStatus.PUBLISHED)
        res_exams = await self.db.execute(stmt_exams)
        published_exams = list(res_exams.scalars().all())

        if not published_exams:
            return None

        # Check passed exams
        passed_count = await self.result_repo.count_passed_exams_for_student_in_course(student_id, course_id)
        if passed_count < len(published_exams):
            return None

        # Student passed all published exams! Compute average percentage
        stmt_scores = (
            select(func.avg(Result.percentage))
            .join(Exam, Exam.id == Result.exam_id)
            .where(
                Result.student_id == student_id,
                Exam.course_id == course_id,
                Result.passed == True,
            )
        )
        avg_res = await self.db.execute(stmt_scores)
        final_pct = float(avg_res.scalar() or 100.0)

        # Generate unique code
        code = generate_certificate_code()
        now = datetime.now(UTC)

        cert = Certificate(
            certificate_code=code,
            student_id=student_id,
            course_id=course_id,
            final_percentage=round(final_pct, 2),
            issued_at=now,
        )
        self.db.add(cert)

        # Update enrollment completed_at & progress
        enrollment = await self.course_repo.get_enrollment(student_id, course_id)
        if enrollment:
            enrollment.status = EnrollmentStatus.COMPLETED
            enrollment.progress_percent = 100.00
            enrollment.completed_at = now

        await self.db.commit()
        await self.db.refresh(cert)

        # Generate PDF and upload
        user = await self.user_repo.get_by_id(student_id)
        course = await self.course_repo.get_by_id(course_id)
        student_name = user.full_name if user else "Student"
        student_code = user.student_profile.student_code if user and user.student_profile else "SBU-0000"
        course_title = course.title if course else "Course"

        try:
            pdf_bytes = PDFService.render_certificate_pdf(
                student_name=student_name,
                student_code=student_code,
                course_title=course_title,
                certificate_code=cert.certificate_code,
                final_percentage=cert.final_percentage,
                issued_at=cert.issued_at,
            )
            pdf_path = f"certificates/template-v2/{cert.certificate_code}.pdf"
            saved_path = await StorageService.upload_file(pdf_path, pdf_bytes)
            cert.pdf_path = saved_path
            await self.cert_repo.update(cert)
        except Exception as e:
            logger.error("Failed to generate certificate PDF for %s: %s", code, e)

        return cert

    async def get_or_generate_certificate_pdf(self, cert_id: uuid.UUID) -> bytes:
        cert = await self.cert_repo.get_by_id(cert_id)
        if not cert:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Certificate not found")

        # Try to load cached
        normalized_pdf_path = cert.pdf_path.replace("\\", "/") if cert.pdf_path else ""
        if "certificates/template-v2/" in normalized_pdf_path:
            cached = await StorageService.download_file(cert.pdf_path)
            if cached:
                return cached

        # Generate on demand
        user = await self.user_repo.get_by_id(cert.student_id)
        course = await self.course_repo.get_by_id(cert.course_id)
        student_name = user.full_name if user else "Student"
        student_code = user.student_profile.student_code if user and user.student_profile else "SBU-0000"
        course_title = course.title if course else "Course"

        pdf_bytes = PDFService.render_certificate_pdf(
            student_name=student_name,
            student_code=student_code,
            course_title=course_title,
            certificate_code=cert.certificate_code,
            final_percentage=cert.final_percentage,
            issued_at=cert.issued_at,
        )
        pdf_path = f"certificates/template-v2/{cert.certificate_code}.pdf"
        saved_path = await StorageService.upload_file(pdf_path, pdf_bytes)
        cert.pdf_path = saved_path
        await self.cert_repo.update(cert)
        return pdf_bytes

    async def verify_certificate(self, code: str) -> VerifyCertificateResponse:
        cert = await self.cert_repo.get_by_code(code)
        if not cert:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Certificate not found or invalid code")

        is_valid = cert.revoked_at is None
        return VerifyCertificateResponse(
            is_valid=is_valid,
            certificate_code=cert.certificate_code,
            student_name=cert.student.full_name if cert.student else "Student",
            course_title=cert.course.title if cert.course else "Course",
            final_percentage=float(cert.final_percentage),
            issued_at=cert.issued_at,
            revoked_at=cert.revoked_at,
            revocation_reason="Revoked by university administration" if not is_valid else None,
        )

    async def revoke_certificate(self, cert_id: uuid.UUID, admin: User, reason: str | None) -> Certificate:
        if admin.role != UserRole.ADMIN:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only admins can revoke certificates")

        cert = await self.cert_repo.get_by_id(cert_id)
        if not cert:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Certificate not found")

        cert.revoked_at = datetime.now(UTC)
        cert.revoked_by = admin.id

        await self.audit_repo.log(
            actor_id=admin.id,
            action="certificate.revoked",
            entity_type="certificate",
            entity_id=str(cert.id),
            metadata={"certificate_code": cert.certificate_code, "reason": reason},
        )
        return await self.cert_repo.update(cert)
