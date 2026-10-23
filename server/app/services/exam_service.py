import random
import uuid
from datetime import datetime, timedelta, timezone
from typing import List, Optional
from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.logging import logger
from app.db.models.course import Course, Enrollment, EnrollmentStatus
from app.db.models.exam import (
    AttemptAnswer,
    AttemptStatus,
    Exam,
    ExamAttempt,
    ExamStatus,
    Question,
    QuestionOption,
)
from app.db.models.result import Result
from app.db.models.task import Task, TaskCompletion, TaskStatus, TaskType, TaskVerification
from app.db.models.user import User, UserRole
from app.repositories.course_repository import CourseRepository
from app.repositories.exam_repository import ExamRepository
from app.repositories.result_repository import ResultRepository
from app.repositories.task_repository import TaskRepository
from app.repositories.user_repository import UserRepository
from app.schemas.exam import (
    ExamCreate,
    ExamPublishRequest,
    ExamResponse,
    ExamUpdate,
    IntegrityReviewResponse,
    QuestionCreate,
    QuestionOptionResponse,
    QuestionResponse,
    StartAttemptResponse,
    SubmitAttemptResponse,
)
from app.services.certificate_service import CertificateService
from app.services.pdf_service import PDFService
from app.services.ranking_service import RankingService
from app.services.storage_service import StorageService
from app.services.task_service import TaskService


def compute_grade(percentage: float) -> str:
    if percentage >= 90:
        return "A+"
    elif percentage >= 80:
        return "A"
    elif percentage >= 70:
        return "B"
    elif percentage >= 60:
        return "C"
    elif percentage >= 50:
        return "D"
    return "F"


def ensure_utc(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt


class ExamService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.exam_repo = ExamRepository(db)
        self.course_repo = CourseRepository(db)
        self.user_repo = UserRepository(db)
        self.result_repo = ResultRepository(db)
        self.task_repo = TaskRepository(db)
        self.task_service = TaskService(db)
        self.ranking_service = RankingService(db)
        self.cert_service = CertificateService(db)

    async def create_exam(self, data: ExamCreate, creator: User) -> Exam:
        course = await self.course_repo.get_by_id(data.course_id)
        if not course:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Course not found")
        if creator.role == UserRole.TEACHER and not await self.course_repo.is_teacher_assigned(
            course.id, creator.id
        ):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Cannot create exams for another teacher's course")

        if data.end_at <= data.start_at:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="end_at must be strictly after start_at")

        if data.publish_immediately and not data.questions:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cannot publish exam without questions")

        total_marks = sum(question.marks for question in data.questions)
        if data.pass_marks > total_marks:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="pass_marks cannot be greater than the total marks",
            )
        if not data.questions and data.pass_marks > 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Add questions before setting pass_marks",
            )

        for question in data.questions:
            correct_count = sum(1 for option in question.options if option.is_correct)
            if correct_count != 1:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Question must have exactly one correct option (found {correct_count})",
                )

        exam = Exam(
            course_id=data.course_id,
            created_by=creator.id,
            title=data.title,
            instructions=data.instructions,
            duration_minutes=data.duration_minutes,
            total_marks=total_marks,
            pass_marks=data.pass_marks,
            negative_marking=data.negative_marking,
            max_attempts=data.max_attempts,
            shuffle_questions=data.shuffle_questions,
            show_review=data.show_review,
            start_at=data.start_at,
            end_at=data.end_at,
            status=ExamStatus.PUBLISHED if data.publish_immediately else ExamStatus.DRAFT,
        )
        self.db.add(exam)
        await self.db.flush()

        for question_data in data.questions:
            question = Question(
                exam_id=exam.id,
                text=question_data.text,
                marks=question_data.marks,
                position=question_data.position,
                explanation=question_data.explanation,
            )
            self.db.add(question)
            self.db.add_all(
                [
                    QuestionOption(
                        question=question,
                        text=option.text,
                        is_correct=option.is_correct,
                        position=option.position,
                    )
                    for option in question_data.options
                ]
            )

        if data.publish_immediately:
            await self._set_exam_task(exam, creator, data.task_points)

        await self.db.commit()
        await self.db.refresh(exam)
        return exam

    async def update_exam(self, exam_id: uuid.UUID, data: ExamUpdate, user: User) -> Exam:
        exam = await self.exam_repo.get_by_id(exam_id)
        if not exam:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Exam not found")
        if exam.status == ExamStatus.CLOSED:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cannot edit a closed exam")

        course = await self.course_repo.get_by_id(exam.course_id)
        if user.role == UserRole.TEACHER and course and not await self.course_repo.is_teacher_assigned(
            course.id, user.id
        ):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Cannot edit exams for another teacher's course")

        if data.course_id is not None and data.course_id != exam.course_id:
            new_course = await self.course_repo.get_by_id(data.course_id)
            if not new_course:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Course not found")
            if user.role == UserRole.TEACHER and not await self.course_repo.is_teacher_assigned(
                new_course.id, user.id
            ):
                raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Cannot move exam to another teacher's course")
            course = new_course

        if data.questions is not None:
            attempt_count = await self.db.scalar(
                select(func.count(ExamAttempt.id)).where(ExamAttempt.exam_id == exam.id)
            )
            if attempt_count:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="Cannot edit exam questions after students have started attempts",
                )

            question_positions = [question.position for question in data.questions]
            if len(question_positions) != len(set(question_positions)):
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Question positions must be unique")
            for question in data.questions:
                option_positions = [option.position for option in question.options]
                if len(option_positions) != len(set(option_positions)):
                    raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Option positions must be unique")
                correct_count = sum(1 for option in question.options if option.is_correct)
                if correct_count != 1:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"Question must have exactly one correct option (found {correct_count})",
                    )

        changes = data.model_dump(exclude_unset=True, exclude={"questions", "task_points"})
        for field, val in changes.items():
            setattr(exam, field, val)

        if exam.end_at <= exam.start_at:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="end_at must be strictly after start_at")

        if data.questions is not None:
            exam.total_marks = sum(question.marks for question in data.questions)
            exam.questions.clear()
            await self.db.flush()
            for question_data in data.questions:
                exam.questions.append(
                    Question(
                        text=question_data.text,
                        marks=question_data.marks,
                        position=question_data.position,
                        explanation=question_data.explanation,
                        options=[
                            QuestionOption(
                                text=option.text,
                                is_correct=option.is_correct,
                                position=option.position,
                            )
                            for option in question_data.options
                        ],
                    )
                )

        if exam.pass_marks > exam.total_marks:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="pass_marks cannot be greater than the total marks",
            )

        if data.task_points is not None:
            task = await self.task_repo.get_by_exam_id(exam.id)
            if data.task_points > 0:
                await self._set_exam_task(exam, user, data.task_points)
            elif task:
                task.status = TaskStatus.ARCHIVED

        if data.course_id is not None:
            task = await self.task_repo.get_by_exam_id(exam.id)
            if task:
                task.course_id = data.course_id

        return await self.exam_repo.update(exam)

    async def add_question(self, exam_id: uuid.UUID, data: QuestionCreate, user: User) -> Question:
        exam = await self.exam_repo.get_by_id(exam_id)
        if not exam:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Exam not found")
        if exam.status != ExamStatus.DRAFT:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Questions can only be added to draft exams")

        course = await self.course_repo.get_by_id(exam.course_id)
        if user.role == UserRole.TEACHER and course and not await self.course_repo.is_teacher_assigned(
            course.id, user.id
        ):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

        # Validate exactly one correct option
        correct_count = sum(1 for opt in data.options if opt.is_correct)
        if correct_count != 1:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Question must have exactly one correct option (found {correct_count})",
            )

        q = Question(
            exam_id=exam_id,
            text=data.text,
            marks=data.marks,
            position=data.position,
            explanation=data.explanation,
        )
        self.db.add(q)
        await self.db.flush()

        for opt in data.options:
            qo = QuestionOption(
                question_id=q.id,
                text=opt.text,
                is_correct=opt.is_correct,
                position=opt.position,
            )
            self.db.add(qo)

        # Update exam total marks
        exam.total_marks = float(exam.total_marks) + float(data.marks)
        await self.db.commit()

        stmt = select(Question).options(selectinload(Question.options)).where(Question.id == q.id)
        res = await self.db.execute(stmt)
        return res.scalar_one()

    async def publish_exam(self, exam_id: uuid.UUID, data: ExamPublishRequest, user: User) -> Exam:
        exam = await self.exam_repo.get_by_id(exam_id)
        if not exam:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Exam not found")

        course = await self.course_repo.get_by_id(exam.course_id)
        if user.role == UserRole.TEACHER and course and not await self.course_repo.is_teacher_assigned(
            course.id, user.id
        ):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

        if not exam.questions:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cannot publish exam without questions")

        exam.status = ExamStatus.PUBLISHED

        await self._set_exam_task(exam, user, data.task_points)

        await self.db.commit()
        await self.db.refresh(exam)
        return exam

    async def _set_exam_task(self, exam: Exam, user: User, task_points: int) -> None:
        if task_points <= 0:
            return

        existing_task = await self.task_repo.get_by_exam_id(exam.id)
        if existing_task:
            existing_task.points = task_points
            existing_task.status = TaskStatus.ACTIVE
            return

        self.db.add(
            Task(
                course_id=exam.course_id,
                created_by=user.id,
                type=TaskType.EXAM,
                exam_id=exam.id,
                title=f"Pass {exam.title}",
                description=f"Earn {task_points} Task Points by achieving a passing score on {exam.title}.",
                points=task_points,
                verification=TaskVerification.AUTO,
                due_at=exam.end_at,
                status=TaskStatus.ACTIVE,
            )
        )

    async def close_exam(self, exam_id: uuid.UUID, user: User) -> Exam:
        exam = await self.exam_repo.get_by_id(exam_id)
        if not exam:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Exam not found")
        if exam.status != ExamStatus.PUBLISHED:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Only published exams can be closed")

        course = await self.course_repo.get_by_id(exam.course_id)
        if user.role == UserRole.TEACHER and course and not await self.course_repo.is_teacher_assigned(
            course.id, user.id
        ):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

        exam.status = ExamStatus.CLOSED
        return await self.exam_repo.update(exam)

    async def delete_exam(self, exam_id: uuid.UUID, user: User) -> None:
        exam = await self.exam_repo.get_by_id(exam_id)
        if not exam:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Exam not found")

        course = await self.course_repo.get_by_id(exam.course_id)
        if user.role == UserRole.TEACHER and course and not await self.course_repo.is_teacher_assigned(
            course.id, user.id
        ):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

        attempt_count = await self.db.scalar(
            select(func.count(ExamAttempt.id)).where(ExamAttempt.exam_id == exam.id)
        )
        if attempt_count:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Cannot delete an exam with student attempts",
            )

        task = await self.task_repo.get_by_exam_id(exam.id)
        if task:
            completion_count = await self.db.scalar(
                select(func.count(TaskCompletion.id)).where(TaskCompletion.task_id == task.id)
            )
            if completion_count:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="Cannot delete an exam with recorded task completions",
                )
            await self.db.delete(task)

        await self.db.delete(exam)
        await self.db.commit()

    async def start_attempt(self, exam_id: uuid.UUID, student: User) -> StartAttemptResponse:
        exam = await self.exam_repo.get_by_id(exam_id)
        if not exam:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Exam not found")

        now = datetime.now(timezone.utc)
        exam_start = ensure_utc(exam.start_at)
        exam_end = ensure_utc(exam.end_at)
        reexam_approvals = await self.exam_repo.count_reexam_approvals(exam.id, student.id)
        has_reexam_approval = reexam_approvals > 0
        if exam.status != ExamStatus.PUBLISHED and not has_reexam_approval:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Exam is not published")
        if now < exam_start and not has_reexam_approval:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Exam has not started yet")
        if now > exam_end and not has_reexam_approval:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Exam has ended")

        # Check enrollment
        enrollment = await self.course_repo.get_enrollment(student.id, exam.course_id)
        if not enrollment or enrollment.status != EnrollmentStatus.ACTIVE:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You are not enrolled in this course")

        # Check if active in-progress attempt already exists
        active = await self.exam_repo.get_active_attempt_for_student(student.id)
        if active:
            if active.exam_id == exam_id:
                # Return existing active attempt
                questions_safe = self._build_safe_questions(active.exam.questions, active.exam.shuffle_questions)
                return StartAttemptResponse(
                    attempt_id=active.id,
                    exam_id=active.exam_id,
                    exam_title=active.exam.title,
                    attempt_no=active.attempt_no,
                    started_at=active.started_at,
                    expires_at=active.expires_at,
                    questions=questions_safe,
                    reexam_available=False,
                )
            else:
                raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="You have another active exam attempt in progress")

        # Check max attempts
        attempt_count = await self.exam_repo.count_attempts(exam.id, student.id)
        if attempt_count >= exam.max_attempts + reexam_approvals:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Maximum attempt limit ({exam.max_attempts}) reached")

        expires_at = now + timedelta(minutes=exam.duration_minutes)
        if now <= exam_end and not has_reexam_approval:
            expires_at = min(expires_at, exam_end)
        attempt = ExamAttempt(
            exam_id=exam.id,
            student_id=student.id,
            attempt_no=attempt_count + 1,
            status=AttemptStatus.IN_PROGRESS,
            started_at=now,
            expires_at=expires_at,
        )
        saved_attempt = await self.exam_repo.create_attempt(attempt)

        questions_safe = self._build_safe_questions(exam.questions, exam.shuffle_questions)
        return StartAttemptResponse(
            attempt_id=saved_attempt.id,
            exam_id=saved_attempt.exam_id,
            exam_title=exam.title,
            attempt_no=saved_attempt.attempt_no,
            started_at=saved_attempt.started_at,
            expires_at=saved_attempt.expires_at,
            questions=questions_safe,
            reexam_available=has_reexam_approval,
        )

    async def list_integrity_reviews(self, reviewer: User) -> List[IntegrityReviewResponse]:
        attempts = await self.exam_repo.list_pending_integrity_reviews()
        reviews: List[IntegrityReviewResponse] = []
        for attempt in attempts:
            course = attempt.exam.course
            if reviewer.role == UserRole.TEACHER and not await self.course_repo.is_teacher_assigned(course.id, reviewer.id):
                continue
            reviews.append(IntegrityReviewResponse(
                attempt_id=attempt.id,
                exam_id=attempt.exam_id,
                exam_title=attempt.exam.title,
                course_title=course.title,
                student_id=attempt.student_id,
                student_name=attempt.student.full_name,
                attempt_no=attempt.attempt_no,
                reason=attempt.integrity_violation_reason or "unknown",
                flagged_at=attempt.integrity_flagged_at or attempt.submitted_at or attempt.started_at,
            ))
        return reviews

    async def approve_reexam(self, attempt_id: uuid.UUID, reviewer: User) -> None:
        attempt = await self.exam_repo.get_attempt(attempt_id)
        if not attempt or not attempt.integrity_violation:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Integrity review not found")
        if reviewer.role == UserRole.TEACHER and not await self.course_repo.is_teacher_assigned(attempt.exam.course_id, reviewer.id):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You are not assigned to this exam's course")
        if attempt.reexam_approved_at:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="A re-exam is already approved for this attempt")

        attempt.reexam_approved_at = datetime.now(timezone.utc)
        attempt.reexam_approved_by_id = reviewer.id
        await self.exam_repo.update_attempt(attempt)

    async def flag_integrity_violation(self, attempt_id: uuid.UUID, student_id: uuid.UUID, reason: str) -> SubmitAttemptResponse:
        attempt = await self.exam_repo.get_attempt(attempt_id)
        if not attempt or attempt.student_id != student_id:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Attempt not found")
        if attempt.status != AttemptStatus.IN_PROGRESS:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="This exam attempt is already submitted")

        attempt.integrity_violation = True
        attempt.integrity_violation_reason = reason
        attempt.integrity_flagged_at = datetime.now(timezone.utc)
        await self.db.flush()
        return await self.submit_attempt(attempt_id, student_id, is_auto=True)

    def _build_safe_questions(self, questions: List[Question], shuffle: bool) -> List[QuestionResponse]:
        q_list = list(questions)
        if shuffle:
            random.seed(42)  # Deterministic shuffle for question order
            random.shuffle(q_list)

        result: List[QuestionResponse] = []
        for q in q_list:
            opts = [
                QuestionOptionResponse(
                    id=o.id,
                    text=o.text,
                    position=o.position,
                    is_correct=None,  # NEVER LEAK PRE-SUBMISSION!
                )
                for o in q.options
            ]
            result.append(
                QuestionResponse(
                    id=q.id,
                    text=q.text,
                    marks=float(q.marks),
                    position=q.position,
                    explanation=None,  # Hidden pre-submission
                    options=opts,
                )
            )
        return result

    async def autosave_answer(
        self,
        attempt_id: uuid.UUID,
        question_id: uuid.UUID,
        selected_option_id: Optional[uuid.UUID],
        student_id: uuid.UUID,
    ):
        attempt = await self.exam_repo.get_attempt(attempt_id)
        if not attempt or attempt.student_id != student_id:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Attempt not found")

        now = datetime.now(timezone.utc)
        if attempt.status != AttemptStatus.IN_PROGRESS or now > ensure_utc(attempt.expires_at):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Attempt is already expired or submitted")

        await self.exam_repo.upsert_answer(attempt_id, question_id, selected_option_id)
        return {"saved": True, "server_time": now}

    async def submit_attempt(self, attempt_id: uuid.UUID, student_id: uuid.UUID, is_auto: bool = False) -> SubmitAttemptResponse:
        attempt = await self.exam_repo.get_attempt(attempt_id)
        if not attempt or attempt.student_id != student_id:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Attempt not found")

        # Idempotent return if already submitted
        if attempt.status in (AttemptStatus.SUBMITTED, AttemptStatus.AUTO_SUBMITTED):
            existing_result = await self.result_repo.get_by_attempt_id(attempt_id)
            if existing_result:
                return SubmitAttemptResponse(
                    result_id=existing_result.id,
                    attempt_id=existing_result.attempt_id,
                    exam_id=existing_result.exam_id,
                    score=float(existing_result.score),
                    total_marks=float(existing_result.total_marks),
                    percentage=float(existing_result.percentage),
                    passed=existing_result.passed,
                    grade=existing_result.grade,
                    rank_in_exam=existing_result.rank_in_exam,
                    task_points_awarded=0,
                )

        now = datetime.now(timezone.utc)
        attempt.status = AttemptStatus.AUTO_SUBMITTED if is_auto else AttemptStatus.SUBMITTED
        attempt.submitted_at = now

        # Grading logic
        answers_map = {ans.question_id: ans.selected_option_id for ans in attempt.answers}
        total_score = 0.0
        exam = attempt.exam

        for q in exam.questions:
            selected_opt_id = answers_map.get(q.id)
            if selected_opt_id:
                correct_opt = next((o for o in q.options if o.is_correct), None)
                if correct_opt and selected_opt_id == correct_opt.id:
                    total_score += float(q.marks)
                else:
                    total_score -= float(exam.negative_marking)

        total_score = 0.0 if attempt.integrity_violation else max(0.0, total_score)
        total_marks = float(exam.total_marks) or 1.0
        percentage = round((total_score / total_marks) * 100.0, 2)
        passed = not attempt.integrity_violation and total_score >= float(exam.pass_marks)
        grade = compute_grade(percentage)
        time_taken = int((now - ensure_utc(attempt.started_at)).total_seconds())

        # Informational per-exam rank
        exam_rank = await self.result_repo.calculate_exam_rank(exam.id, total_score, time_taken)

        result_row = Result(
            attempt_id=attempt.id,
            exam_id=exam.id,
            student_id=student_id,
            score=round(total_score, 2),
            total_marks=round(total_marks, 2),
            percentage=percentage,
            grade=grade,
            passed=passed,
            time_taken_sec=time_taken,
            rank_in_exam=exam_rank,
        )
        self.db.add(result_row)
        await self.db.flush()

        # Transactional task point awarding if student passed and exam task exists!
        task_points_awarded = 0
        if passed:
            task_points_awarded = await self.task_service.complete_exam_task_if_passed(exam.id, student_id)

        # Update course progress on enrollment
        stmt_pub = select(func.count(Exam.id)).where(Exam.course_id == exam.course_id, Exam.status == ExamStatus.PUBLISHED)
        pub_count_res = await self.db.execute(stmt_pub)
        total_pub = pub_count_res.scalar() or 1

        passed_count = await self.result_repo.count_passed_exams_for_student_in_course(student_id, exam.course_id)
        if passed:
            passed_count += 1

        enrollment = await self.course_repo.get_enrollment(student_id, exam.course_id)
        if enrollment:
            enrollment.progress_percent = min(100.0, round((passed_count / total_pub) * 100.0, 2))

        await self.db.commit()
        await self.db.refresh(result_row)

        # After commit:
        # 1. Refresh live ranking (Task Points)
        if task_points_awarded > 0:
            await self.ranking_service.refresh_student(student_id)

        # 2. Check if student completed course -> auto-issue Certificate
        if passed:
            try:
                await self.cert_service.check_and_issue_certificate(student_id, exam.course_id)
            except Exception as e:
                logger.error("Certificate check failed: %s", e)

        # 3. Generate Result PDF in background
        user = await self.user_repo.get_by_id(student_id)
        student_name = user.full_name if user else "Student"
        student_code = user.student_profile.student_code if user and user.student_profile else "SBU-0000"
        course = await self.course_repo.get_by_id(exam.course_id)
        course_title = course.title if course else "Course"

        try:
            pdf_bytes = PDFService.render_result_pdf(
                student_name=student_name,
                student_code=student_code,
                exam_title=exam.title,
                course_title=course_title,
                score=result_row.score,
                total_marks=result_row.total_marks,
                percentage=result_row.percentage,
                grade=result_row.grade,
                passed=result_row.passed,
                time_taken_sec=result_row.time_taken_sec,
                rank_in_exam=result_row.rank_in_exam or 1,
                submitted_at=result_row.created_at,
            )
            pdf_path = f"results/template-v2/{result_row.id}.pdf"
            saved_path = await StorageService.upload_file(pdf_path, pdf_bytes)
            result_row.pdf_path = saved_path
            await self.result_repo.update(result_row)
        except Exception as e:
            logger.error("Failed to generate Result PDF: %s", e)

        return SubmitAttemptResponse(
            result_id=result_row.id,
            attempt_id=result_row.attempt_id,
            exam_id=result_row.exam_id,
            score=float(result_row.score),
            total_marks=float(result_row.total_marks),
            percentage=float(result_row.percentage),
            passed=result_row.passed,
            grade=result_row.grade,
            rank_in_exam=result_row.rank_in_exam,
            task_points_awarded=task_points_awarded,
        )

    async def get_or_generate_result_pdf(self, result_id: uuid.UUID, user: User) -> bytes:
        result = await self.result_repo.get_by_id(result_id)
        if not result:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Result not found")

        # Security check: student can only view own, teacher of course, or admin
        if user.role == UserRole.STUDENT and result.student_id != user.id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
        if user.role == UserRole.TEACHER and not await self.course_repo.is_teacher_assigned(
            result.exam.course_id, user.id
        ):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

        # Regenerate previously cached PDFs once so every download uses the new
        # supplied result-sheet template.
        if result.pdf_path and result.pdf_path.startswith("results/template-v2/"):
            cached = await StorageService.download_file(result.pdf_path)
            if cached:
                return cached

        # Generate on demand
        student = result.student
        student_name = student.full_name if student else "Student"
        student_code = student.student_profile.student_code if student and student.student_profile else "SBU-0000"
        exam = result.exam
        course = exam.course

        pdf_bytes = PDFService.render_result_pdf(
            student_name=student_name,
            student_code=student_code,
            exam_title=exam.title,
            course_title=course.title,
            score=result.score,
            total_marks=result.total_marks,
            percentage=result.percentage,
            grade=result.grade,
            passed=result.passed,
            time_taken_sec=result.time_taken_sec,
            rank_in_exam=result.rank_in_exam or 1,
            submitted_at=result.created_at,
        )
        pdf_path = f"results/template-v2/{result.id}.pdf"
        saved = await StorageService.upload_file(pdf_path, pdf_bytes)
        result.pdf_path = saved
        await self.result_repo.update(result)
        return pdf_bytes
