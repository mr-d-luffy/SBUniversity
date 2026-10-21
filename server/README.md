# SiliconBrains University Backend (FastAPI + Supabase + Redis)

Backend API for the **SiliconBrains University** platform.

---

## 🏛 Architecture Overview

- **Framework:** FastAPI, Python 3.13, Pydantic v2
- **Database:** Supabase PostgreSQL with SQLAlchemy 2 (async) & `asyncpg`
- **Real-Time & Cache:** Redis (Task Points leaderboard sorted sets, live SSE updates, caching, rate limiting)
- **Authentication:** Clerk JWT verification via JWKS (cached) with RBAC (`student`, `teacher`, `admin`)
- **Webhooks:** Clerk Webhook synchronization with Svix signature verification
- **Document Generation:** Backend ReportLab PDF engine (official Result statements & Certificates with QR codes)
- **AI Assistant:** Aarsh Intelligence (Google Gemini) with anti-cheat live exam guardrails
- **Live classroom:** Course-scoped whiteboard sessions, persisted strokes, and expiring class chat
- **Admin controls:** Course CRUD, multiple course teachers, selected student enrollment, and permanent account deletion
- **Security:** RLS enabled across all Supabase tables, parameterized queries, strict role gating

---

## 📁 Project Structure

```
server/
├── app/
│   ├── main.py                     # FastAPI application, lifespan, CORS, exception handlers
│   ├── core/
│   │   ├── config.py                # Environment configuration (pydantic-settings)
│   │   ├── logging.py               # Structured logging
│   │   ├── redis.py                 # Async Redis client with in-memory fallback
│   │   ├── security.py              # Clerk JWT verification via JWKS
│   │   ├── rate_limit.py            # Sliding window rate limiter
│   │   └── deps.py                  # Dependencies (auth, RBAC, DB session)
│   ├── db/
│   │   ├── base.py                  # SQLAlchemy DeclarativeBase
│   │   ├── session.py               # Async engine and sessionmaker
│   │   └── models/                  # SQLAlchemy 2.0 ORM models
│   │       ├── user.py              # User, Department, StudentProfile, TeacherProfile
│   │       ├── course.py            # Course, Enrollment
│   │       ├── exam.py              # Exam, Question, QuestionOption, ExamAttempt, AttemptAnswer
│   │       ├── result.py            # Result
│   │       ├── certificate.py       # Certificate
│   │       ├── task.py              # Task, TaskCompletion (Task Points engine)
│   │       ├── notice.py            # Notice
│   │       ├── chat.py              # ChatSession, ChatMessage
│   │       └── audit.py             # AuditLog
│   ├── schemas/                     # Pydantic v2 validation models
│   ├── repositories/                # Domain data access layers
│   ├── services/                    # Business logic services
│   │   ├── exam_service.py          # Exam attempts, timer, grading, automatic task completion
│   │   ├── task_service.py          # Task Points awarding, approval queue, admin revoke
│   │   ├── ranking_service.py       # Live Top 4 Redis leaderboard & SSE broadcast
│   │   ├── certificate_service.py   # Course completion check, issuance, verification
│   │   ├── pdf_service.py           # ReportLab branded result & certificate PDFs
│   │   ├── ai_service.py            # Gemini assistant (Aarsh Intelligence)
│   │   ├── notice_service.py        # Scoped notice delivery & caching
│   │   ├── user_service.py          # Profiles, Virtual ID card, role sync
│   │   ├── course_service.py        # Courses and enrollments
│   │   └── analytics_service.py     # Real-time analytics & SSE stream
│   └── api/v1/                      # REST endpoints (/api/v1)
│       ├── public.py                # Public stats & QR verification
│       ├── auth_webhooks.py         # Clerk webhook sync (Svix)
│       ├── me.py                    # Current user profile & ID photo
│       ├── student.py               # Student dashboard, ID card, points
│       ├── teacher.py               # Teacher dashboard, course results
│       ├── exams.py                 # Exam management, runner, autosave, submit
│       ├── results.py               # Exam results and PDF downloads
│       ├── certificates.py          # Certificates and PDF downloads
│       ├── tasks.py                 # Tasks, reviews, approvals
│       ├── ranking.py               # Top 4 live leaderboard & SSE stream
│       ├── notices.py               # Notice board
│       ├── assistant.py             # Aarsh Intelligence streaming chat
│       └── admin/                   # Admin panel (users, progress, analytics, notices, audit)
├── migrations/                      # Alembic migrations
├── scripts/
│   ├── schema.sql                   # Supabase migration SQL schema
│   └── seed.py                      # Database seeder (20 students, 4 courses, exams, tasks)
├── tests/                           # Pytest test suite (auth, exams, ranking, certificates, pdf)
├── supabase_migration.sql           # Complete Supabase PostgreSQL schema with RLS & Storage
├── Dockerfile                       # Multi-stage production container
├── docker-compose.yml               # Local container stack with Redis
├── requirements.txt
└── pyproject.toml
```

---

## 🚀 Getting Started

### 1. Environment Configuration

Copy `.env.example` to `.env`:
```bash
cp .env.example .env
```

Fill in your connection details:
- `DATABASE_URL`: Supabase connection string (`postgresql+asyncpg://...`)
- `CLERK_SECRET_KEY` & `CLERK_JWKS_URL`: Clerk authentication keys
- `REDIS_URL`: Redis connection URL (`redis://localhost:6379/0` or Upstash)
- `GEMINI_API_KEY`: Google Gemini API key for Aarsh Intelligence

### 2. Supabase Migration

#### New database bootstrap

For a new Supabase database only, apply the full `supabase_migration.sql` bootstrap in the SQL Editor:
1. Open the Supabase Dashboard -> **SQL Editor**.
2. Paste the contents of `supabase_migration.sql`.
3. Click **Run**.
4. The bootstrap creates the tables, custom ENUMs, indexes, triggers, and RLS policies.

#### Existing database

Use Alembic (recommended) to apply versioned changes. Do not rerun the full bootstrap over an initialized production database. Alternatively, apply the matching update section in `supabase_migration.sql`.
```bash
alembic upgrade head
```
The current head is `012_chat_voice_messages`. New deployments should use Alembic migrations to keep schema history aligned.

### 3. Seed Sample Data (Development/Staging)

```bash
python scripts/seed.py
```
This populates:
- 3 Departments (CS, AI, EE)
- 1 Admin (`admin@sbuniversity.edu`)
- 3 Teachers (`meera.iyer@...`, `rajesh.patel@...`, `ananya.das@...`)
- 20 Students with virtual student codes (`SBU-2026-0001` to `0020`)
- 4 Courses with published exams and 10 MCQs each
- Tasks and completed Task Points populating the Live Top 4 leaderboard
- Notices and issued certificates

### 4. Running the Server

From the repository root, start the local SiliconBrains University API on port `8010`:
```bash
./scripts/run-local-backend.sh
```
The launcher uses `server/.venv`, changes into `server/` before importing `app.main`,
and avoids the common module collision with other installed projects also named `app`.
Set `SBUNIVERSITY_API_PORT` to use a different local port. The web development server
proxies local API calls to `http://127.0.0.1:8010/api/v1`; override that target with
`LOCAL_API_PROXY_TARGET` if the API is on another local port.

Using Docker:
```bash
docker-compose up --build
```

---

## 🏆 Key Features & Business Rules

1. **Task Points Live Ranking:**
   - Students earn Task Points automatically upon passing an exam task or upon teacher approval of an assignment task.
   - Leaderboard score: `points + (1.0 - epoch_seconds / 1e10)` (tie-break: earliest completion ranks higher).
   - Redis sorted sets (`lb:overall` and `lb:course:{id}`) update in real-time, publishing events to `/api/v1/ranking/stream` (SSE).

2. **Exam Lifecycle & Anti-Cheat:**
   - Server-authoritative timer (`expires_at`).
   - Correct answers are **never** returned before submission.
   - Background sweeper auto-submits expired attempts.
   - Aarsh Intelligence AI **blocks** assistance if the student has an active exam attempt.

3. **Verifiable Certificates & Result Statements:**
   - When a student passes all published exams of a course, a Certificate is automatically issued with a unique code (e.g., `SBU-CERT-7F3K9Q2M`).
   - Official ReportLab PDFs generated server-side using the institutional brand palette (Bordo `#6C151E`, Green `#0F3D3A`, Cream `#F5DABF`).
   - Public QR verification at `/api/v1/public/verify/certificate/{code}` and `/api/v1/public/verify/student/{qr_token}`.

4. **Admin course and account control:**
   - Admins can create, update, and permanently delete courses; assign several teachers; and enroll selected or all active students.
   - Permanent account deletion removes the Clerk identity before deleting the database user. `CLERK_SECRET_KEY` is required; the API refuses to remove the database account if identity-provider deletion fails.
   - Assigned teachers, the current admin, and the last active admin are protected from unsafe deletion/demotion.

5. **Live classroom:**
   - Assigned teachers/admins manage course sessions; enrolled students join to view and chat.
   - Chat expires after ten minutes; board strokes are retained with the session.

---

## 🧪 Running Tests

```bash
pytest tests
```
