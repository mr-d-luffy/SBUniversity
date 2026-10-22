# SiliconBrains University

SiliconBrains University is a role-based learning platform with student, teacher, and admin experiences. The web application uses Next.js, TypeScript, and Tailwind CSS; the API uses FastAPI and SQLAlchemy with PostgreSQL as its source of truth.

## Current capabilities

- Student and teacher dashboards, course enrollment, exams, results, certificates, and tasks with Task Points.
- Live Task Points ranking, notices, analytics, and an AI study assistant named Aarsh Intelligence.
- Course-scoped live whiteboards with teacher controls, student participation, and expiring classroom chat.
- Admin controls for users, course creation and editing, teacher/student course assignments, and account deletion.
- Clerk authentication, backend role/ownership checks, and database audit records for administrative actions.

## Repository layout

- [`web/`](./web/README.md) — Next.js frontend.
- [`server/`](./server/README.md) — FastAPI backend, Alembic migrations, and tests.
- [`Docs/`](./Docs/architecture.md) — product, architecture, database, design, operating, and [security/access-control](./Docs/SECURITY_AND_ACCESS_CONTROL.md) documentation.

## Local development

1. Configure `web/.env.local` from [`web/.env.example`](./web/.env.example) and `server/.env` from [`server/.env.example`](./server/.env.example). Keep all secrets out of source control.
   Set `NEXT_PUBLIC_SITE_URL` to the production website origin so canonical URLs and `sitemap.xml` use the correct domain.
2. Apply database migrations from `server/` with `alembic upgrade head`. The Supabase SQL bootstrap/update is in [`server/supabase_migration.sql`](./server/supabase_migration.sql).
3. Start the API from the repository root with `./scripts/run-local-backend.sh`.
4. Start the frontend from `web/` with `npm install` then `npm run dev`.

## Verification

From `web/`, run `npm run typecheck`, `npm run lint`, and `npm run build`. From `server/`, run `pytest tests`.

See [`Docs/phases.md`](./Docs/phases.md) for implementation status and next steps. Account deletion is permanent and requires a configured Clerk backend secret.

Production deployments must configure exact HTTPS `CORS_ORIGINS`, Clerk issuer/audience and webhook secrets, Supabase Storage credentials, Redis rate limiting, and `DEBUG=false`; the API refuses insecure or incomplete production settings. See the [security and access control policy](./Docs/SECURITY_AND_ACCESS_CONTROL.md) for application controls and external deployment obligations.
