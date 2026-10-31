# architecture.md — SiliconBrains University System Architecture

> Repository snapshot: this document reflects the current implementation in the `web/` and `server/` folders as of 2026-11-01.
> It is intentionally aligned to the live stack, routes, and service layout in the codebase rather than a hypothetical future product.

## 1. Tech Stack
| Layer | Technology |
|---|---|
| Frontend | Next.js 16 (App Router, TypeScript), Tailwind CSS 4 |
| Auth | Clerk (`@clerk/nextjs`, backend JWT verification via JWKS) |
| Backend | FastAPI, Python 3.11+ per `server/pyproject.toml`, Uvicorn, Pydantic v2 |
| DB | Supabase PostgreSQL (accessed by backend via SQLAlchemy 2 async + asyncpg) |
| Storage | Supabase Storage (generated PDFs, profile photos) |
| Cache / Realtime | Redis (cache, leaderboard sorted sets, rate limits, pub/sub) |
| AI | Google Gemini API (`google-genai` SDK) |
| PDF generation | ReportLab + `qrcode` (backend) |
| Live classroom | Course-scoped FastAPI whiteboard sync; persisted strokes and short-lived chat |
| Community Chat | Browser WebCrypto encryption for text/audio; device keys, key envelopes, and 10-hour inactive-conversation cleanup |
| Mobile | Student-scoped Flutter Android client foundation; not feature-complete or production-ready |
| Hosting (suggested) | Frontend: Vercel · Backend: Docker on Render/Railway/Fly · Redis: Upstash/Redis Cloud |

## 2. Overall Architecture
```
 Browser (Next.js + Tailwind)
   │  Clerk session (JWT)
   ▼
 Next.js proxy ── authentication gate for protected routes
   │  fetch /api/v1/*  (Bearer JWT)
   ▼
 FastAPI (Python 3.11+ package requirement)
   ├── Auth dependency  → verify Clerk JWT (JWKS) → load user/role
   ├── RBAC dependency  → require_role(...)
   ├── Routers → Services → Repositories
   │        ├──► Supabase PostgreSQL  (source of truth)
   │        ├──► Redis (cache / leaderboard / rate limit / pub-sub)
   │        ├──► Supabase Storage (PDFs, photos)
   │        └──► Gemini API (Aarsh Intelligence)
   └── Clerk webhook endpoint (user.created/updated/deleted)
```
**Style:** modular monolith backend (one FastAPI app, domain modules). Simpler to build/deploy than microservices and sufficient for the target scale.

**Key decision:** The browser **never talks to Supabase directly**. Application data goes through FastAPI. Supabase RLS is configured in the SQL bootstrap as defense-in-depth; production database policies and roles still need deployment verification.

## 3. Application Flow
```
Landing → Sign in (Clerk) → role redirect
   ├─ student → /student/dashboard
   ├─ teacher → /teacher/dashboard
   └─ admin   → /admin
```

## 4. Authentication Flow
```
1. User signs in with Clerk (frontend).
2. Clerk issues a signed session JWT.
3. Frontend sends JWT in Authorization header (via getToken()).
4. FastAPI verifies signature (JWKS, cached), `exp`, `azp`/issuer.
5. FastAPI loads the `users` row by `clerk_user_id` and checks that the account is active; the database role is authoritative for existing users.
6. RBAC dependency compares role with the endpoint requirement.
7. Clerk webhook (Svix-signed) keeps `users` table in sync (create/update/delete).
```
**Role change:** Admin calls `PATCH /admin/users/{id}/role` → backend updates Clerk metadata and the database; authorization on existing accounts uses the database role.

## 5. Authorization / Role Matrix
| Capability | Student | Teacher | Admin |
|---|:-:|:-:|:-:|
| View own dashboard/profile | ✅ | ✅ | ✅ |
| Take exams | ✅ | ❌ | ❌ |
| Complete tasks / earn Task Points | ✅ | ❌ | ❌ |
| Create tasks, approve assignment tasks | ❌ | own courses | all |
| Revoke a task completion | ❌ | ❌ | ✅ |
| Create/edit exams | ❌ | own courses | all |
| View results | own | own course | all |
| Download own result/certificate | ✅ | – | any |
| Post notices | ❌ | own scope | all |
| View ranking | ✅ | ✅ | ✅ |
| Use AI assistant | ✅ | ✅ | ✅ |
| User control / analytics / progress | ❌ | ❌ | ✅ |
| Manage courses and teacher/student assignments | ❌ | ❌ | ✅ |
| Manage a course whiteboard | ❌ | assigned courses | ✅ |
| Use Community Chat | ✅ | ✅ | ✅ |

Ownership checks (e.g., "student can only read own result") are enforced in the **service layer**, not only by role.

## 6. Admin Route Security (3 layers)
1. **Frontend gate:** `src/proxy.ts` requires an authenticated session for protected role areas; it does not decide the authoritative role.
2. **Backend gate:** admin API routers use `require_role("admin")`.
3. **Audit:** sensitive admin mutations are recorded in `audit_logs`.
Clerk MFA is a deployment/account configuration requirement, not something established by this repository.

## 7. Frontend Architecture
- Next.js App Router, TypeScript, Server Components by default; Client Components only for interactivity (exam timer, chat, live ranking).
- Data fetching: feature components use the shared API helper in `src/lib/api.ts`; no SWR or React Query dependency is declared.
- Route groups: shared authenticated routes are under `(app)`; role-specific pages are directories within that group, with public routes alongside it.
- PDF download: client calls API with Bearer token → receives Blob → triggers browser download (`URL.createObjectURL`). No PDF logic in the frontend.
- Live ranking: `EventSource` (SSE) with polling fallback.

### Folder Structure (Current frontend repo: `web/`)
```
web/
├─ src/app/
│  ├─ (app)/
│  │  ├─ admin/
│  │  │  ├─ analytics/
│  │  │  ├─ courses/
│  │  │  ├─ notices/
│  │  │  ├─ progress/
│  │  │  └─ users/
│  │  ├─ assistant/
│  │  ├─ community-chat/
│  │  ├─ notices/
│  │  ├─ planner/
│  │  ├─ ranking/
│  │  ├─ student/
│  │  │  ├─ certificates/
│  │  │  ├─ dashboard/
│  │  │  ├─ exams/
│  │  │  ├─ profile/
│  │  │  ├─ results/
│  │  │  └─ tasks/
│  │  ├─ teacher/
│  │  │  ├─ dashboard/
│  │  │  ├─ exams/
│  │  │  └─ tasks/
│  │  └─ whiteboard/
│  ├─ about/
│  ├─ portal/
│  ├─ sign-in/
│  ├─ sign-up/
│  ├─ verify/
│  ├─ layout.tsx
│  ├─ page.tsx
│  └─ globals.css
├─ src/components/
│  ├─ features/
│  │  ├─ AarshFloatingWidget.tsx
│  │  ├─ AdminCourses.tsx
│  │  ├─ ApprovalQueue.tsx
│  │  ├─ CommunityChat.tsx
│  │  ├─ LearnPlanner.tsx
│  │  ├─ LiveWhiteboard.tsx
│  │  ├─ RankBoard.tsx
│  │  ├─ TaskList.tsx
│  │  ├─ TeacherTaskCreator.tsx
│  │  ├─ UsersTable.tsx
│  │  └─ YoutubeVideoTracker.tsx
│  └─ ui/
├─ src/lib/
│  ├─ api.ts
│  ├─ auth.ts
│  ├─ actions.ts
│  └─ mock.ts
└─ src/proxy.ts
```

## 8. Backend Architecture
Layered: **Router → Service → Repository → DB**. Routers are thin; business rules live in services.

### Folder Structure (Current backend repo: `server/`)
```
server/
├─ app/
│  ├─ main.py                  # app factory, CORS, lifespan, periodic sweeps
│  ├─ api/v1/
│  │  ├─ admin/
│  │  │  ├─ analytics.py
│  │  │  ├─ audit_logs.py
│  │  │  ├─ courses.py
│  │  │  ├─ notices.py
│  │  │  ├─ progress.py
│  │  │  └─ users.py
│  │  ├─ assistant.py
│  │  ├─ certificates.py
│  │  ├─ community_chat.py
│  │  ├─ exams.py
│  │  ├─ me.py
│  │  ├─ notices.py
│  │  ├─ planner.py
│  │  ├─ public.py
│  │  ├─ ranking.py
│  │  ├─ results.py
│  │  ├─ router.py
│  │  ├─ student.py
│  │  ├─ tasks.py
│  │  ├─ teacher.py
│  │  └─ whiteboard.py
│  ├─ core/
│  │  ├─ config.py
│  │  ├─ deps.py
│  │  ├─ logging.py
│  │  ├─ rate_limit.py
│  │  ├─ redis.py
│  │  └─ security.py
│  ├─ db/
│  │  ├─ base.py
│  │  ├─ session.py
│  │  └─ models/              # SQLAlchemy models, including community chat
│  ├─ repositories/
│  ├─ schemas/
│  ├─ services/
│  └─ tests/
├─ migrations/               # Alembic revisions
├─ Dockerfile
├─ docker-compose.yml
├─ requirements.txt
└─ pyproject.toml
```

## 9. API Architecture
- Base: `/api/v1`. JSON with Pydantic validation. HTTP error responses follow the implemented FastAPI/application handlers; this snapshot does not establish one uniform error envelope.
- List endpoints use route-specific query parameters; pagination is not universal.

### Endpoint Structure
**Public**
- `GET /public/stats` · `GET /public/verify/certificate/{code}` · `GET /public/verify/student/{token}`

**Me**
- `GET /me` · `PATCH /me` · `POST /me/photo`

**Student**
- `GET /student/dashboard` · `GET /student/id-card` · `GET /student/courses`

**Exams**
- `GET /exams` (role-filtered) · `GET /exams/{id}`
- `POST /exams` · `PATCH /exams/{id}` · `POST /exams/{id}/publish` (body: `task_points`) · `POST /exams/{id}/questions` (teacher/admin)
- `POST /exams/{id}/attempts` (start) · `GET /attempts/{id}` (questions, no answers)
- `PUT /attempts/{id}/answers/{question_id}` (autosave) · `POST /attempts/{id}/submit`

**Results**
- `GET /results` · `GET /results/{id}` · `GET /results/{id}/pdf`

**Certificates**
- `GET /certificates` · `GET /certificates/{id}/pdf` · (admin) `POST /admin/certificates/{id}/revoke`

**Tasks**
- `GET /tasks` (student: tasks of enrolled courses with my status · teacher: own courses) · `GET /tasks/{id}`
- `POST /tasks` · `PATCH /tasks/{id}` · `POST /tasks/{id}/archive` (teacher own / admin) — **assignment** tasks only; exam tasks are created automatically by exam publish
- `POST /tasks/{id}/complete` (student; assignment → `pending_review`, body: note/url)
- `GET /tasks/reviews?status=pending_review` · `POST /tasks/completions/{id}/approve` · `POST /tasks/completions/{id}/reject` (teacher own / admin)
- `GET /student/points` (total, tasks completed, history)
- `POST /admin/tasks/completions/{id}/revoke` (admin)

**Ranking**
- `GET /ranking/top?scope=overall|course&course_id=` · `GET /ranking/stream` (SSE) · `GET /ranking/me`

**Notices**
- `GET /notices` · `POST /notices` · `PATCH /notices/{id}` · `DELETE /notices/{id}`

**Assistant**
- `POST /assistant/chat` (streams) · `GET /assistant/sessions` · `GET /assistant/sessions/{id}` · `DELETE /assistant/sessions/{id}`

**Teacher**
- `GET /teacher/dashboard` · `GET /teacher/courses/{id}/results`

**Admin** (all require admin)
- `GET /admin/users` · `PATCH /admin/users/{id}/role` · `PATCH /admin/users/{id}/status` · `DELETE /admin/users/{id}` · `POST /admin/enrollments`
- `GET /admin/courses` · `GET /admin/courses/students` · `POST /admin/courses` · `PATCH /admin/courses/{id}` · `DELETE /admin/courses/{id}` · teacher assignment sync
- `GET /admin/progress/students` · `GET /admin/progress/students/{id}` · `GET /admin/progress/courses/{id}`
- `GET /admin/analytics/overview` · `/teachers` · `/students` · `GET /admin/analytics/stream` (SSE)
- `GET /admin/notices` · moderation via `/notices/*`
- `GET /admin/audit-logs`

**Webhooks**
- `POST /webhooks/clerk`

**Live classroom**
- Course-scoped live whiteboard session endpoints are grouped under `/whiteboard`; only assigned teachers/admins can control a session, and enrolled students must join before viewing or chatting.

**Community Chat**
- `/community-chat` provides conversation lists, direct/staff support initiation, device registration, public-key listing, wrapped-key envelope exchange, encrypted text/audio messages, and authenticated audio retrieval.
- Text and voice payloads are encrypted in the browser with WebCrypto AES-GCM keys. Device identities use RSA-OAEP; the server stores public keys and per-device wrapped-key envelopes, not private keys or plaintext.
- Device/private and conversation keys persist in IndexedDB with no app TTL. Conversation/message database rows and key envelopes are removed after 10 hours without a new message. The expiry job does not delete separately stored audio objects; their retention must be managed separately.

## 14. Current implementation notes (2026-11-01)
- Admin course management supports create, edit, permanent delete, multiple assigned teachers, selected student enrollment, and enroll-all-active-students.
- Course-teacher membership is stored in `course_teachers`; `courses.teacher_id` remains the primary-teacher compatibility field.
- Account deletion is permanent in both Clerk and the application database. It requires `CLERK_SECRET_KEY`; assigned teachers, the signed-in administrator, and the last active administrator are protected by service-layer checks.
- Course deletion removes dependent course records; authored material is retained when an author account is deleted by setting its creator reference to `NULL`.
- Live whiteboard messages expire after ten minutes; stored strokes remain with the session history. Chat polling on the web client is every five seconds; focus/visibility refreshes remain available for more immediate updates.
- Student dashboard task completion statuses are fetched in one batched query for the selected tasks.
- The AI orb animation is shared by the assistant page, floating launcher, and floating panel. Its black canvas is screen-blended into the UI; the site favicon is `web/src/app/icon.svg`.
- Community Chat uses browser WebCrypto and IndexedDB-retained keys without an application TTL; conversation/message database rows and server key envelopes are removed after 10 hours without a new message. Stored audio objects are outside that database cleanup.

## 10. Data Flow Diagrams
### Task completion → Task Points → Live Ranking
```
A) Exam task (fully automatic)
Student ► POST /attempts/{id}/submit
            │
            ▼
      exam_service.grade()  → write results + attempt status           ┐ one DB
            │ (student PASSED and exam has an active task)             │ transaction
            ▼                                                          │
      task_service.complete_exam_task()                                │
            INSERT task_completions (status=completed,                 │
            points_awarded = task.points)  UNIQUE(task_id, student_id) ┘ → no double award
            │ after commit
            ▼
      ranking_service.refresh_student(student_id)
            ► recompute SUM(points) + last completion time from DB
            ► Redis ZADD lb:overall + lb:course:{id}   (absolute score, idempotent)
            ► PUBLISH lb:updates ► SSE ► Ranking page updates live
            ▼
      certificate_service.check_completion() ► issue certificate if complete
Frontend ► GET /results/{id}/pdf ► pdf_service (ReportLab) ► PDF stream ► browser download

B) Assignment task (teacher approval, then automatic)
Student ► POST /tasks/{id}/complete (note/url)  → status = pending_review
Teacher ► POST /tasks/completions/{id}/approve
            ► status = completed, points_awarded = task.points (one transaction)
            ► ranking_service.refresh_student() ► Redis ► SSE   (same as above)

C) Revoke (admin)
Admin ► POST /admin/tasks/completions/{id}/revoke → status = revoked, audit_log
            ► ranking_service.refresh_student() ► points removed ► SSE
```
**Leaderboard score (Redis):** `score = total_points + (1 − last_completed_epoch_seconds / 1e10)`. Points are integers, so the fraction (always < 1) only breaks ties — earlier completion ranks higher. Scores are **recomputed from the database and set absolutely** (never incremented), so retries cannot drift.

### AI Chat
```
Frontend ► POST /assistant/chat
   ► auth + rate limit (Redis) ► block if active exam attempt
   ► build prompt (system + role + safe user context + history)
   ► Gemini API ► stream tokens ► store messages ► client
```

## 11. Caching Strategy (Redis)
| Key | Purpose | TTL |
|---|---|---|
| `lb:overall`, `lb:course:{id}` | Leaderboard sorted sets (score = Task Points + tie-break fraction) | no TTL; overall scores rebuild from `task_completions` at startup and refresh on score-changing events; reads fall back to SQL when empty |
| `cache:public:stats` | Landing stats | 5 min |
| `cache:admin:analytics:overview` | Admin overview aggregate | 45 s |
| `rl:{route}:{user_id}` | Rate limiting | window |
| `jwks:clerk` | Clerk JWKS | 1 h |
Notice writes invalidate legacy notice-cache keys; current notice-list caching is not confirmed in code.
Redis Pub/Sub channel: `lb:updates`. Admin analytics exposes an SSE stream that refreshes its overview every 5 s.

## 12. External Services
Clerk, Supabase (Postgres + Storage), Redis provider, Google Gemini.

## 13. Important Technical Decisions
| # | Decision | Reason |
|---|---|---|
| 1 | Backend-only DB access | Keeps secrets and authorization in one place |
| 2 | Server-authoritative exam timer | Prevents client clock cheating |
| 3 | Never send correct answers pre-submit | Anti-cheat |
| 4 | Rank by **Task Points** (not exam marks), stored in a Redis sorted set | Rewards completed work, fully automatable, O(log N) updates, instant Top 4 |
| 5 | SSE (not WebSocket) for live data | One-way updates, simpler, works over HTTP |
| 6 | ReportLab for PDFs | Pure Python, no system deps, stable on 3.13 |
| 7 | Generated PDFs cached in Supabase Storage | Avoid re-render; certificates are immutable |
| 8 | Clerk metadata synced to a database role | Frontend checks session authentication; the database role is authoritative in the app/API |
| 9 | Gemini model name via env var | Models change; avoid hardcoding |
| 10 | Alembic migrations | Versioned schema |
| 11 | Points awarded in the **same DB transaction** as completion, unique per (task, student) | Atomic and idempotent — no double points |
| 12 | Leaderboard score recomputed from DB and set absolutely (no incrementing) | Self-healing, safe with retries and revokes |
| 13 | Exam tasks auto-created on exam publish; assignment tasks need teacher approval | Keeps awarding automated without enabling self-claimed points |
