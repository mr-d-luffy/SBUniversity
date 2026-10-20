import asyncio
from datetime import date, datetime, timedelta, timezone
import random
import uuid
from sqlalchemy import select, text
from app.db.base import Base
from app.db.models import *
from app.db.session import AsyncSessionLocal, engine
from app.services.ranking_service import RankingService


async def seed_database():
    print("🌱 Starting SiliconBrains University database seed...")

    async with AsyncSessionLocal() as session:
        # Check if already seeded
        res = await session.execute(text("SELECT count(*) FROM users"))
        if (res.scalar() or 0) > 5:
            print("Database already contains users. Skipping seed.")
            return

        now = datetime.now(timezone.utc)

        # 1. Departments
        dept_cs = Department(code="CS", name="Computer Science & Engineering")
        dept_ai = Department(code="AI", name="Artificial Intelligence & Data")
        dept_ee = Department(code="EE", name="Electrical & Electronics")
        session.add_all([dept_cs, dept_ai, dept_ee])
        await session.flush()

        # 2. Admin
        admin = User(
            clerk_user_id="user_admin_01",
            email="admin@sbuniversity.edu",
            full_name="University Administrator",
            role=UserRole.ADMIN,
            status=UserStatus.ACTIVE,
        )
        session.add(admin)

        # 3. Teachers
        t1 = User(
            clerk_user_id="user_teacher_01",
            email="meera.iyer@sbuniversity.edu",
            full_name="Dr. Meera Iyer",
            role=UserRole.TEACHER,
            status=UserStatus.ACTIVE,
        )
        t1.teacher_profile = TeacherProfile(
            employee_code="T-2026-001",
            department_id=dept_cs.id,
            designation="Professor & HOD",
            bio="Specialist in Algorithms, Graph Theory, and Advanced Computing.",
        )

        t2 = User(
            clerk_user_id="user_teacher_02",
            email="rajesh.patel@sbuniversity.edu",
            full_name="Dr. Rajesh Patel",
            role=UserRole.TEACHER,
            status=UserStatus.ACTIVE,
        )
        t2.teacher_profile = TeacherProfile(
            employee_code="T-2026-002",
            department_id=dept_ai.id,
            designation="Associate Professor",
            bio="Researcher in Machine Learning, Statistical Learning, and AI Systems.",
        )

        t3 = User(
            clerk_user_id="user_teacher_03",
            email="ananya.das@sbuniversity.edu",
            full_name="Prof. Ananya Das",
            role=UserRole.TEACHER,
            status=UserStatus.ACTIVE,
        )
        t3.teacher_profile = TeacherProfile(
            employee_code="T-2026-003",
            department_id=dept_ee.id,
            designation="Assistant Professor",
            bio="Expertise in Digital Systems and Embedded Computer Architecture.",
        )
        session.add_all([t1, t2, t3])
        await session.flush()

        # 4. Students (20 students)
        student_names = [
            "Aarav Sharma", "Isha Patil", "Kabir Nair", "Sneha Joshi", "Vikram Rao",
            "Neha Kulkarni", "Rohan Mehta", "Pooja Reddy", "Aditya Verma", "Kavya Menon",
            "Siddharth Sen", "Anika Deshmukh", "Dev Patel", "Tanvi Bhat", "Arjun Pillai",
            "Meera Nambiar", "Yash Chopra", "Rhea Kapoor", "Varun Saxena", "Diya Mukherjee"
        ]

        students: list[User] = []
        for idx, name in enumerate(student_names, start=1):
            email = f"{name.lower().replace(' ', '.')}@sbuniversity.edu"
            u = User(
                clerk_user_id=f"user_student_{idx:02d}",
                email=email,
                full_name=name,
                role=UserRole.STUDENT,
                status=UserStatus.ACTIVE,
            )
            u.student_profile = StudentProfile(
                student_code=f"SBU-2026-{idx:04d}",
                department_id=dept_cs.id if idx % 2 == 0 else dept_ai.id,
                batch_year=2026,
                phone=f"+91 98765 {idx:05d}",
                date_of_birth=date(2004, (idx % 12) + 1, (idx % 25) + 1),
                id_valid_until=date(2028, 6, 30),
                qr_token=f"qr-token-student-{idx:04d}",
            )
            students.append(u)
            session.add(u)
        await session.flush()

        # 5. Courses (4 courses)
        c1 = Course(
            code="CS-201",
            title="Data Structures & Algorithms",
            description="Fundamental algorithms, sorting, binary trees, dynamic programming, and complexity.",
            department_id=dept_cs.id,
            teacher_id=t1.id,
            is_published=True,
        )
        c2 = Course(
            code="AI-101",
            title="Introduction to Artificial Intelligence",
            description="Search strategies, knowledge representation, Bayesian networks, and heuristic reasoning.",
            department_id=dept_ai.id,
            teacher_id=t2.id,
            is_published=True,
        )
        c3 = Course(
            code="CS-102",
            title="Python Systems Programming",
            description="Core language design, concurrency, asyncio, object-oriented software architecture.",
            department_id=dept_cs.id,
            teacher_id=t1.id,
            is_published=True,
        )
        c4 = Course(
            code="EE-205",
            title="Computer Organization & Digital Logic",
            description="Logic gates, processor datapath, pipelining, and cache hierarchies.",
            department_id=dept_ee.id,
            teacher_id=t3.id,
            is_published=True,
        )
        session.add_all([c1, c2, c3, c4])
        await session.flush()

        courses = [c1, c2, c3, c4]

        # 6. Enrollments (enroll all students into CS-201 and AI-101)
        for s in students:
            session.add(Enrollment(student_id=s.id, course_id=c1.id, status=EnrollmentStatus.ACTIVE, progress_percent=50.0))
            session.add(Enrollment(student_id=s.id, course_id=c2.id, status=EnrollmentStatus.ACTIVE, progress_percent=25.0))
            session.add(Enrollment(student_id=s.id, course_id=c3.id, status=EnrollmentStatus.ACTIVE, progress_percent=100.0))
        await session.flush()

        # 7. Exams & Questions (2 exams per course, 10 MCQs each)
        for course in courses:
            for exam_no in (1, 2):
                start_time = now - timedelta(days=2) if exam_no == 1 else now + timedelta(days=5)
                end_time = now + timedelta(days=3) if exam_no == 1 else now + timedelta(days=10)
                
                exam = Exam(
                    course_id=course.id,
                    created_by=course.teacher_id,
                    title=f"{course.title} - Exam {exam_no}",
                    instructions="Answer all questions. Each correct answer awards 2 marks. Negative marking applies.",
                    duration_minutes=45,
                    total_marks=20.0,
                    pass_marks=10.0,
                    negative_marking=0.5,
                    max_attempts=1,
                    start_at=start_time,
                    end_at=end_time,
                    status=ExamStatus.PUBLISHED,
                )
                session.add(exam)
                await session.flush()

                # Add 10 MCQs
                for q_idx in range(1, 11):
                    q = Question(
                        exam_id=exam.id,
                        text=f"Question {q_idx} on core concepts of {course.code} (Topic {q_idx})?",
                        marks=2.0,
                        position=q_idx,
                        explanation=f"Option 1 is correct based on foundational principles taught in Module {q_idx}.",
                    )
                    session.add(q)
                    await session.flush()

                    opt1 = QuestionOption(question_id=q.id, text=f"Correct standard resolution definition for Q{q_idx}", is_correct=True, position=1)
                    opt2 = QuestionOption(question_id=q.id, text=f"Suboptimal alternative hypothesis A", is_correct=False, position=2)
                    opt3 = QuestionOption(question_id=q.id, text=f"Non-convergent implementation B", is_correct=False, position=3)
                    opt4 = QuestionOption(question_id=q.id, text=f"Degenerate runtime complexity C", is_correct=False, position=4)
                    session.add_all([opt1, opt2, opt3, opt4])

                # Exam task (Task Points)
                exam_task = Task(
                    course_id=course.id,
                    created_by=course.teacher_id,
                    type=TaskType.EXAM,
                    exam_id=exam.id,
                    title=f"Pass {exam.title}",
                    description=f"Pass the {exam.title} with at least 50% score to earn 50 Task Points.",
                    points=50,
                    verification=TaskVerification.AUTO,
                    due_at=exam.end_at,
                    status=TaskStatus.ACTIVE,
                )
                session.add(exam_task)

            # Assignment tasks for the course
            assign1 = Task(
                course_id=course.id,
                created_by=course.teacher_id,
                type=TaskType.ASSIGNMENT,
                title=f"{course.code} Practical Implementation Report",
                description="Submit a short write-up or repository link containing your module laboratory exercises.",
                points=40,
                verification=TaskVerification.TEACHER_APPROVAL,
                due_at=now + timedelta(days=7),
                status=TaskStatus.ACTIVE,
            )
            assign2 = Task(
                course_id=course.id,
                created_by=course.teacher_id,
                type=TaskType.ASSIGNMENT,
                title=f"{course.code} Case Study Analysis",
                description="Analyze the asymptotic runtime behavior of the benchmark dataset.",
                points=30,
                verification=TaskVerification.TEACHER_APPROVAL,
                due_at=now + timedelta(days=12),
                status=TaskStatus.ACTIVE,
            )
            session.add_all([assign1, assign2])

        await session.flush()

        # 8. Task completions & Task Points (Create realistic varied leaderboard scores)
        # Isha Patil (s2): 520 pts
        # Kabir Nair (s3): 455 pts
        # Sneha Joshi (s4): 410 pts
        # Vikram Rao (s5): 300 pts
        # Aarav Sharma (s1): 290 pts
        all_tasks = (await session.execute(select(Task))).scalars().all()
        exam_tasks = [t for t in all_tasks if t.type == TaskType.EXAM]
        assign_tasks = [t for t in all_tasks if t.type == TaskType.ASSIGNMENT]

        # Seed completions with exact timestamps to test tie-breaks
        point_distribution = [
            (students[1], 500),  # Isha
            (students[2], 450),  # Kabir
            (students[3], 400),  # Sneha
            (students[4], 300),  # Vikram
            (students[0], 280),  # Aarav
            (students[5], 250),  # Neha
            (students[6], 200),
            (students[7], 150),
        ]

        for student, target_pts in point_distribution:
            earned = 0
            for t in all_tasks:
                if earned >= target_pts:
                    break
                # Award completion
                completion_time = now - timedelta(hours=random.randint(5, 100))
                comp = TaskCompletion(
                    task_id=t.id,
                    student_id=student.id,
                    status=CompletionStatus.COMPLETED,
                    submission_note="Completed coursework verified.",
                    submission_url="https://github.com/sbuniversity/lab-submissions",
                    points_awarded=t.points,
                    submitted_at=completion_time,
                    completed_at=completion_time,
                    reviewed_by=t.created_by,
                )
                session.add(comp)
                earned += t.points

        # One pending review & one revoked completion to test admin/teacher flows
        if assign_tasks:
            pending_comp = TaskCompletion(
                task_id=assign_tasks[0].id,
                student_id=students[8].id,
                status=CompletionStatus.PENDING_REVIEW,
                submission_note="drive.google.com/aditya-report",
                submission_url="https://drive.google.com/file",
                points_awarded=0,
                submitted_at=now - timedelta(hours=2),
            )
            session.add(pending_comp)

            revoked_comp = TaskCompletion(
                task_id=assign_tasks[1].id,
                student_id=students[9].id,
                status=CompletionStatus.REVOKED,
                submission_note="Plagiarized report flagged.",
                points_awarded=0,
                submitted_at=now - timedelta(days=3),
                completed_at=now - timedelta(days=2),
                revoked_at=now - timedelta(days=1),
                revoked_by=admin.id,
            )
            session.add(revoked_comp)

        # 9. Results
        first_exam = (await session.execute(select(Exam))).scalars().first()
        if first_exam:
            for idx, student in enumerate(students[:10], start=1):
                score = 16.0 + (idx % 4)
                pct = (score / 20.0) * 100.0
                attempt = ExamAttempt(
                    exam_id=first_exam.id,
                    student_id=student.id,
                    attempt_no=1,
                    status=AttemptStatus.SUBMITTED,
                    started_at=now - timedelta(days=1, minutes=40),
                    expires_at=now - timedelta(days=1),
                    submitted_at=now - timedelta(days=1, minutes=5),
                )
                session.add(attempt)
                await session.flush()

                res = Result(
                    attempt_id=attempt.id,
                    exam_id=first_exam.id,
                    student_id=student.id,
                    score=score,
                    total_marks=20.0,
                    percentage=pct,
                    grade="A" if pct >= 80 else "B",
                    passed=True,
                    time_taken_sec=2100,
                    rank_in_exam=idx,
                )
                session.add(res)

        # 10. Notices (5 notices as specified)
        n1 = Notice(
            author_id=t1.id,
            title="Midterm Examination Schedule Published",
            body="The Data Structures midterm examination opens on Oct 18 and closes on Oct 20 at 6 PM. You will have 45 minutes for your single timed attempt.",
            audience=NoticeAudience.COURSE,
            course_id=c1.id,
            priority=NoticePriority.IMPORTANT,
            is_pinned=True,
            status=NoticeStatus.PUBLISHED,
        )
        n2 = Notice(
            author_id=admin.id,
            title="Scheduled Portal Maintenance",
            body="Results and digital certificate verification will undergo regular maintenance tonight from 1 AM to 2 AM UTC.",
            audience=NoticeAudience.ALL,
            priority=NoticePriority.URGENT,
            is_pinned=True,
            status=NoticeStatus.PUBLISHED,
        )
        n3 = Notice(
            author_id=admin.id,
            title="Central Campus Library Extended Timings",
            body="During midterm examinations, the central digital reading hall will remain open 24/7 for all registered students.",
            audience=NoticeAudience.STUDENTS,
            priority=NoticePriority.NORMAL,
            is_pinned=False,
            status=NoticeStatus.PUBLISHED,
        )
        n4 = Notice(
            author_id=t2.id,
            title="AI Lab Assignment 1 Submissions Open",
            body="Please submit your search heuristic benchmark links on the Tasks page before the due date for teacher review.",
            audience=NoticeAudience.COURSE,
            course_id=c2.id,
            priority=NoticePriority.NORMAL,
            is_pinned=False,
            status=NoticeStatus.PUBLISHED,
        )
        n5 = Notice(
            author_id=admin.id,
            title="Faculty Academic Committee Meeting",
            body="All department heads and teaching faculty are requested to assemble in Conference Hall B this Friday at 3 PM.",
            audience=NoticeAudience.TEACHERS,
            priority=NoticePriority.NORMAL,
            is_pinned=False,
            status=NoticeStatus.PUBLISHED,
        )
        session.add_all([n1, n2, n3, n4, n5])

        # 11. Certificates (2 valid, 1 revoked)
        cert1 = Certificate(
            certificate_code="SBU-CERT-7F3K9Q2M",
            student_id=students[0].id,
            course_id=c3.id,
            final_percentage=94.50,
            issued_at=now - timedelta(days=5),
        )
        cert2 = Certificate(
            certificate_code="SBU-CERT-4N9X2P8K",
            student_id=students[1].id,
            course_id=c3.id,
            final_percentage=96.00,
            issued_at=now - timedelta(days=3),
        )
        cert3 = Certificate(
            certificate_code="SBU-CERT-1V6M8T4W",
            student_id=students[2].id,
            course_id=c3.id,
            final_percentage=82.00,
            issued_at=now - timedelta(days=10),
            revoked_at=now - timedelta(days=1),
            revoked_by=admin.id,
        )
        session.add_all([cert1, cert2, cert3])

        await session.commit()
        print("✅ PostgreSQL Seed Data successfully committed!")

        # 12. Rebuild Redis Leaderboard
        ranking_svc = RankingService(session)
        rebuilt_cnt = await ranking_svc.rebuild_all_scores()
        print(f"🏆 Rebuilt Redis Leaderboard with {rebuilt_cnt} ranked students!")


if __name__ == "__main__":
    asyncio.run(seed_database())
