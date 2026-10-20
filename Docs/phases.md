# phases.md — SiliconBrains University Development Roadmap

Legend: `[ ]` pending · `[x]` done. Each phase must end with a working, demonstrable result.

## Repository status (2026-10-18)
The repository has progressed beyond the original planning-only state. Admin course/account controls, the live whiteboard, Aarsh Intelligence UI, and major student/teacher workflows are implemented. Checkboxes below track individual acceptance criteria; implementation does not imply production deployment, configured external services, or completed load testing.

---
## Phase 0 — Documentation Foundation
**Objective:** Finalize source-of-truth docs.
- [x] PRD.md, architecture.md, database.md, rules.md, phases.md, design.md, memory.md, System_Design.md
- [ ] Owner confirms assumptions A1–A11 in PRD.md (incl. Task Points model: A3, A9–A11)
**Completion:** Docs approved, no contradictions.

## Phase 1 — Project Setup
**Objective:** Both repos run locally with CI basics.
- [ ] Create `sbuniversity-web` (Next.js + TS + Tailwind) and `sbuniversity-api` (FastAPI, Python 3.13)
- [ ] ESLint/Prettier, Ruff/Black, pre-commit
- [ ] `.env.example` for both; config loader with validation
- [ ] Dockerfile + docker-compose (api + redis) for local dev
- [ ] Supabase project, Clerk app, Redis instance, Gemini key created
- [ ] GitHub repo, branch protection, CI (lint + test)
**Files:** root configs, `app/main.py`, `core/config.py`
**Dependencies:** accounts for Clerk/Supabase/Redis/Gemini
**Result:** `GET /api/v1/health` returns OK; web app boots.
**Completion:** CI green on both repos.

## Phase 2 — UI Foundation & Landing Page
**Objective:** Design system + public landing page.
- [ ] Tailwind theme tokens from `design.md` §3 (Bordo/Green/Cream, 60:30:10) + semantic aliases; fonts
- [ ] UI primitives: Button, Card, Input, Badge, Modal, Table, Skeleton, Toast
- [ ] Layouts: Navbar, Footer, DashboardShell (sidebar)
- [ ] Landing page + certificate verify input
- [ ] 403 / 404 / error pages
**Result:** Responsive landing page and component kit.
**Completion:** Passes mobile/desktop review; a11y basics; palette QA checklist (`design.md` §14) passes.

## Phase 3 — Authentication & Roles
**Objective:** Clerk login with Student/Teacher/Admin and secure routing.
- [ ] Clerk in Next.js; sign-in/up pages; JWT template with `role`
- [ ] `middleware.ts` role gating (`/student`, `/teacher`, `/admin`)
- [ ] FastAPI JWT verification (JWKS), `get_current_user`, `require_role`
- [ ] Clerk webhook → `users` sync
- [ ] `GET /me`; role-based redirect after login
- [ ] Admin MFA setting in Clerk
**Dependencies:** Phase 1, 2
**Result:** Users can sign in and land on the correct role dashboard (placeholder content).
**Completion:** Tests prove student cannot access admin page/API.

## Phase 4 — Database & Core Models
**Objective:** Schema live in Supabase.
- [ ] Alembic setup; migrations for all tables in `database.md`
- [ ] Enums, constraints, indexes, RLS deny-all
- [ ] SQLAlchemy models + repositories
- [ ] Seed script (dev)
**Result:** Database matches `database.md`; seed data loads.
**Completion:** Migration up/down works; schema doc matches reality.

## Phase 5 — Admin: User Control & Notices
**Objective:** Admin can manage the platform basics.
- [x] Admin users table: search/filter, role change (DB + Clerk), suspend/reactivate, permanent account deletion
- [x] Course creation/editing/deletion, multi-teacher assignment, and selected/all-active-student enrollment
- [ ] Departments management and remaining enrollment administration
- [ ] Audit log writes + viewer
- [ ] Notice board backend + UI (admin all, teacher scoped, read for all)
- [ ] Redis notice cache + invalidation
**Result:** Admin promotes a teacher; notices visible by audience.
**Completion:** RBAC + audit tests pass.

## Phase 6 — Teacher: Exam Management
**Objective:** Teachers build exams.
- [ ] Teacher dashboard (stats)
- [ ] Exam CRUD + question/option editor, publish/close
- [ ] Validation (one correct option, marks totals, windows)
- [ ] Exam publish form: **Task Points** field → auto-creates linked exam task
- [ ] Assignment task CRUD (teacher/admin): title, points, due date; points locked after first completion
- [ ] Teacher tasks page + approval queue UI (approve/reject endpoints)
**Result:** Published exam visible to enrolled students.
**Completion:** Teacher can only manage own courses.

## Phase 7 — Student: Dashboard, ID Card & Exam Engine
**Objective:** Students take exams.
- [ ] Student dashboard
- [ ] Virtual ID Card profile page + QR + public student verify
- [ ] Exam list, start attempt, runner with server timer, autosave, submit
- [ ] Auto-grading service; result record creation
- [ ] `task_service`: auto-complete exam task on pass (same transaction, idempotent) and award points
- [ ] Student Tasks page: open / pending / completed, submit assignment (note/link), points per task + total
- [ ] `GET /student/points`; points total on student dashboard; toast on award
- [ ] Auto-submit on expiry (lazy check + background sweep)
**Result:** Student completes an exam and sees a score.
**Completion:** Correct answers never leaked; expiry enforced server-side.

## Phase 8 — Results & PDF Generation
**Objective:** Result page + backend PDF.
- [ ] Result list/detail with review
- [ ] `pdf_service` result PDF (ReportLab), cache in Storage
- [ ] Frontend blob download helper
**Result:** Student downloads Result PDF.
**Completion:** PDF content verified; only owner/admin/teacher-of-course can access.

## Phase 9 — Certificates
**Objective:** Auto-issue and download certificates.
- [ ] Completion rule + issuance on result creation
- [ ] Certificate PDF with unique code + QR
- [ ] Certificates page; public `/verify/[code]`
- [ ] Admin revoke
**Result:** Completing a course yields a downloadable, verifiable certificate.
**Completion:** Revoked cert shows invalid on verify page.

## Phase 10 — Live Ranking (Task Points)
**Objective:** Live Top 4 driven by automatically awarded Task Points.
- [ ] `ranking_service.refresh_student()` hooked to every completion/approval/revoke/suspend event (recompute from DB → absolute `ZADD` → publish)
- [ ] Redis score with tie-break fraction; rebuild-from-DB job + nightly reconcile
- [ ] `/ranking/top` (overall & course), `/ranking/me`, SSE stream
- [ ] Ranking page: Top 4 cards (points + tasks completed), "Your rank", course filter, live updates
- [ ] Admin revoke completion endpoint + audit log
**Files:** `ranking_service.py`, `task_service.py`, `api/v1/ranking.py`, `components/ranking/*`
**Dependencies:** Phase 6, 7 (tasks & completions exist)
**Result:** Completing a task (passing an exam task or an approved assignment) changes the Top 4 live without any manual step.
**Completion:** Tests for no double-award, revoke, tie-break, Redis-vs-SQL parity, suspended users excluded.

## Phase 11 — Aarsh Intelligence (AI)
**Objective:** Gemini chatbot.
- [ ] `ai_service` with system prompt, streaming, history
- [ ] Rate limiting; active-exam block; safe user context
- [ ] Chat widget + `/assistant` page; session list
**Result:** Users chat with Aarsh Intelligence.
**Completion:** Key never exposed; blocked during exams; failures handled.

## Phase 12 — Admin: Progress & Live Analytics
**Objective:** Admin monitoring.
- [ ] Progress check (student/course)
- [ ] Analytics overview, teachers, students; charts (incl. task completion rate and points awarded)
- [ ] Redis-cached aggregates + SSE refresh
**Result:** Live dashboards for admin.
**Completion:** Numbers match DB queries in tests.

## Phase 13 — Testing & Hardening
- [ ] Unit/integration/e2e suites; load test exam submit (500 concurrent)
- [ ] Security review (OWASP top 10), headers, CORS, rate limits
- [ ] Accessibility audit + palette QA re-check (60:30:10, contrast, no bordo-on-green)
**Completion:** No critical/high issues open.

## Phase 14 — Optimization
- [ ] Query/index tuning, cache hit-rate review, bundle size, image optimization
- [x] Reduced live whiteboard chat polling from every 4 seconds to every 5 seconds; visibility/focus refresh remains available.
- [x] Batch student dashboard task-completion status lookups into one query; regression test verifies statuses and query count.
- [ ] Bulk teacher analytics aggregation and bound/paginate task-completion history; add regression coverage.
**Completion:** Meets NFR targets in PRD §8.

## Phase 15 — Deployment
- [ ] Vercel (web), container host (API), Redis, Supabase prod project
- [ ] Prod env vars, domains, Clerk prod instance, webhook URLs
- [ ] Monitoring/logging, backups, runbook
**Completion:** Production smoke test passes; `memory.md` marks deployed.
