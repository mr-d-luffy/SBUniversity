# phases.md — SiliconBrains University Development Roadmap

Legend: `[ ]` pending · `[x]` done. Each phase must end with a working, demonstrable result.

## Repository status (2026-11-01)
The repository includes the web app, FastAPI API, Clerk-backed auth, admin and teacher flows, whiteboard, planner, ranking, AI assistant, Community Chat, and public credential verification, plus a student-scoped Flutter Android client foundation. Checkboxes below reflect repository implementation only; they do not imply production deployment, configured external services, or completed load testing.

---
## Phase 0 — Documentation Foundation
**Objective:** Finalize source-of-truth docs.
- [x] PRD.md, architecture.md, database.md, rules.md, phases.md, design.md, memory.md, System_Design.md
- [ ] Owner confirms assumptions A1–A11 in PRD.md (incl. Task Points model: A3, A9–A11)
**Completion:** Docs approved, no contradictions.

## Phase 1 — Project Setup
**Objective:** The web and API packages run locally with project checks.
- [x] `web/` uses Next.js 16 + TypeScript and `server/` uses FastAPI; backend package metadata supports Python 3.11+.
- [x] Web lint/typecheck/build scripts and backend pytest configuration are present.
- [x] `.env.example` files and backend configuration validation are present.
- [x] Backend Dockerfile and Docker Compose configuration are present.
- [ ] Supabase project, Clerk app, Redis instance, Gemini key created
- [ ] GitHub repo, branch protection, CI (lint + test)
**Files:** root configs, `app/main.py`, `core/config.py`
**Dependencies:** accounts for Clerk/Supabase/Redis/Gemini
**Result:** `GET /api/v1/health` returns OK; web app boots.
**Completion:** CI green on both repos.

## Phase 2 — UI Foundation & Landing Page
**Objective:** Design system + public landing page.
- [x] Tailwind theme tokens from `design.md` §3 are applied in the current frontend styling system.
- [x] Core UI primitives are implemented in `web/src/components/ui/`.
- [x] Public landing page and credential verification flows exist under `web/src/app/`.
- [x] App-level error and loading handling exist in the current route structure.
**Result:** Responsive landing page and role-based app shell in the repository.
**Completion:** The current codebase reflects the design tokens and public experience described in the design docs.

## Phase 3 — Authentication & Roles
**Objective:** Clerk login with Student/Teacher/Admin and secure routing.
- [x] Clerk-backed sign-in/sign-up flows are present in the front end.
- [x] Role-based redirect and portal entry functionality are implemented.
- [x] FastAPI auth/deps enforce Clerk JWT verification and role checks.
- [x] Clerk webhook handlers are in the backend router set.
- [x] `GET /me` and role-aware routing are implemented in the app shell.
**Result:** Users sign in to a role-aware portal with backend authorization checks.
**Completion:** Current repository code reflects the intended Clerk + RBAC flow; deployment and production secret configuration still need verification.

## Phase 4 — Database & Core Models
**Objective:** Schema live in Supabase.
- [x] SQLAlchemy models and repositories exist under `server/app/db/models/` and `server/app/repositories/`.
- [x] Alembic migration infrastructure is present in `server/migrations/`.
- [x] The application is structured around relational domain models and server-side authorization.
- [x] The schema is documented in `Docs/database.md` and `Docs/System_Design.md`.
**Result:** The repo contains a full domain-model structure aligned to the current app features.
**Completion:** Database correctness must still be validated against the live service environment and migration chain in real deployments.

## Phase 5 — Admin: User Control & Notices
**Objective:** Admin can manage the platform basics.
- [x] Admin users table and course management are implemented in the current app and API.
- [x] Multi-teacher assignment and enrollment flows are present in the application code.
- [x] Notice and admin analytics routes are implemented in the backend and front end.
- [x] Audit and platform activity flows are represented in the repository structure.
**Result:** Admin-level management, role changes, and notice flows are present in the repository.
**Completion:** The codebase reflects the intended admin control plane, while detailed operational validation remains separate from repo-level implementation.

## Phase 6 — Teacher: Exam Management
**Objective:** Teachers build exams.
- [x] Teacher dashboard and exam/task flows are present in the current app routes.
- [x] Exam and task entities exist in the API and model layers.
- [x] Course-scoped task completion and approval workflows are represented in the project code.
- [x] Exam publishing and task-points behavior is implemented in the backend/service structure.
**Result:** Teacher-side course administration, exams, and tasks are implemented in the repo.
**Completion:** The codebase has the intended teacher workflows; final operational validation depends on deployment and data integrity checks.

## Phase 7 — Student: Dashboard, ID Card & Exam Engine
**Objective:** Students take exams.
- [x] Student dashboard and profile flows are present in the repo.
- [x] Public credential verification and student ID-related UI are implemented.
- [x] Exam execution and result generation exist in the backend and routes.
- [x] Task completion and points logic are represented in the service layer.
- [x] Auto-submission cleanup for expired attempts exists in the server startup lifecycle.
**Result:** The repo contains the student exam and progress experience described in the project docs.
**Completion:** Runtime behavior should still be validated against environment and integration checks before calling the system production-ready.

## Phase 8 — Results & PDF Generation
**Objective:** Result page + backend PDF.
- [x] Results and certificate-related API routes exist in the backend.
- [x] PDF generation services are part of the backend architecture.
- [x] Frontend flow for result/certificate download is supported by the app code.
**Result:** Result and certificate-related downloads are implemented in the repo.
**Completion:** Actual export content and production validation need environment-level verification.

## Phase 9 — Certificates
**Objective:** Auto-issue and download certificates.
- [x] Certificate pages and certificate API routes exist in the repository.
- [x] Public verification flows are implemented in the front end and backend.
- [x] Credential generation and verification are expressed in the service and schema layers.
**Result:** The repo includes a certificate issuance and verification flow.
**Completion:** Actual certificate issuance policies still require environment and security validation.

## Phase 10 — Live Ranking (Task Points)
**Objective:** Live Top 4 driven by automatically awarded Task Points.
- [x] Ranking service and public ranking endpoints are in the backend.
- [x] Redis-backed leaderboard logic and ranking-related routes exist in the application structure.
- [x] Front-end ranking UI is present under `web/src/app/(app)/ranking` and `web/src/components/features/RankBoard.tsx`.
**Result:** The repository contains the leaderboard pattern described by the product/design docs.
**Completion:** Runtime and tie-break verification need production-like data and service configuration.

## Phase 11 — Aarsh Intelligence (AI)
**Objective:** Gemini chatbot.
- [x] AI assistant service and routes are present in the backend.
- [x] Assistant UI is implemented in the app and feature components.
- [x] Safety and user-context boundaries are represented in the service and documentation structure.
**Result:** The repo includes the assistant experience described in the architecture and product docs.
**Completion:** Live AI behavior still needs environment and security validation in deployment settings.

## Phase 12 — Admin: Progress & Live Analytics
**Objective:** Admin monitoring.
- [x] Admin analytics and progress routes are part of the current backend API.
- [x] Admin dashboard pages and analytics UI exist in the front end.
- [x] Analytics and reporting patterns are part of the current architecture and data model.
**Result:** The repository contains the admin monitoring experience described in the system design docs.
**Completion:** Data accuracy and performance verification remain external to the repository snapshot.

## Phase 13 — Testing & Hardening
- [x] Security hardening and production checks are included in the FastAPI startup config.
- [x] Core route and model architecture is in place for testing and service hardening.
- [ ] Full OWASP, accessibility, and load validation remain to be executed in a real deployment environment.
**Completion:** The repository is structurally hardened, but external security and performance validation are still outstanding.

## Phase 14 — Optimization
- [x] Query and service optimization patterns are present in the current implementation notes.
- [x] Live whiteboard polling was tuned and documented.
- [x] Student dashboard completion checks were batched in the current codebase.
- [ ] Full production profiling, load tuning, and deployment acceptance remain outstanding.
- [ ] Bulk teacher analytics aggregation and bound/paginate task-completion history; add regression coverage.
**Completion:** Verify targets in PRD §8 against measurements and document results.

## Phase 15 — Deployment
- [ ] Vercel (web), container host (API), Redis, Supabase prod project
- [ ] Prod env vars, domains, Clerk prod instance, webhook URLs
- [ ] Monitoring/logging, backups, runbook
**Completion:** Production smoke test passes; `memory.md` marks deployed.

## Phase 16 — Community Chat
**Objective:** Provide shared student chat, peer conversations, and staff support with encrypted text and audio.
- [x] Conversation, device-public-key, and wrapped-key-envelope models and API routes are present.
- [x] Browser WebCrypto encrypts text/audio; device private keys and conversation keys persist in IndexedDB without a TTL.
- [x] Expired conversation/message database rows and key envelopes are removed after 10 hours without a new message.
- [ ] Uploaded audio objects are not removed by the database cleanup; add/configure storage expiry and verify provider retention.
**Completion:** Application behavior is implemented in the repository; cryptographic review, device/browser recovery UX, external storage retention, and production configuration remain to be verified.
