# SiliconBrains University Project Memory / Current State

> Update this file after meaningful project changes.

## Current Status
- **Current focus:** Phase 14 — Optimization and documentation synchronization.
- **Deployment:** Not verified. Do not assume production services, secrets, or migrations have been configured.
- **Backend:** FastAPI, Python 3.13, SQLAlchemy async, PostgreSQL/Supabase, Redis.
- **Frontend:** Next.js App Router, TypeScript strict, Tailwind CSS.
- **Authentication:** Clerk; roles are student, teacher, and admin.
- **AI:** Aarsh Intelligence, backed by Google Gemini.
- **Live ranking:** Task Points, Redis sorted sets, server updates and SSE.
- **Design:** Bordo `#6C151E`, Green `#0F3D3A`, Cream `#F5DABF`.

## Implemented Feature Areas
- Student/teacher workflows for courses, exams, tasks, results, certificates, and notices.
- Admin user controls and course CRUD, multi-teacher assignment, and selected/all-active-student enrollment.
- Permanent account deletion removes the Clerk identity first and then the database account; authored teaching content is retained with a null author reference. This requires `CLERK_SECRET_KEY`.
- Course-scoped live whiteboard with teacher controls, explicit student join, retained strokes, and chat messages expiring after ten minutes.
- Aarsh Intelligence page and floating launcher/panel share the animated orb; the site favicon is `web/src/app/icon.svg`.

## Recent Optimization
- Live whiteboard chat polling was reduced from every 4 seconds to every 5 seconds (20% fewer periodic requests) while keeping the added worst-case freshness delay to about one second. Focus/visibility refresh remains enabled. Stroke merge and snapshot semantics were not changed.
- Student dashboard task completion statuses are now loaded with one query for the selected task IDs, instead of one sequential completion query per task. A regression test covers statuses and query count.
- Remaining profiling items: bulk teacher analytics aggregation, bound or paginate task-completion history, and measure API p95/query counts.

## Database
- Schema changes are managed through Alembic; current migration head is `011_admin_course_management`.
- For new databases, the full Supabase bootstrap is `server/supabase_migration.sql`. For existing databases, prefer `alembic upgrade head` or use only the matching update section, never rerun the whole bootstrap indiscriminately.
- The schema reference is `Docs/database.md`.

## Validation Status
- Previous implementation validation: backend suite passed (38 tests), frontend typecheck and production build passed, and the migration chain/offline SQL generation passed.
- This optimization turn must rerun frontend typecheck/build and verify the chat interval change.
- Do not treat production p95, scalability targets, a complete accessibility audit, or deployment as verified.

## Important Decisions
| Decision | Detail |
|---|---|
| Backend-only data access | Browser does not access Supabase directly; API enforces authorization and ownership. |
| Permanent course deletion | Deletes the course and its related records after confirmation. |
| Permanent account deletion | Delete Clerk identity before database user; fail without deleting DB if provider deletion fails. |
| Teacher protection | A teacher assigned to a course cannot be demoted or deleted until reassigned. |
| Multiple course teachers | `course_teachers` is authoritative for additional assignments; `courses.teacher_id` remains primary for compatibility. |
| Whiteboard history | Strokes remain for session history; live class chat expires after ten minutes. |

## Recent Changes
- 2026-10-18: Added admin course CRUD, teacher/student assignments, permanent account deletion safeguards, schema migration `011_admin_course_management`, and project documentation.
- 2026-10-18: Reduced live whiteboard chat polling from four seconds to five seconds and batched student dashboard completion lookups; synchronized product, architecture, design, database, setup, and roadmap documentation.

## Remaining Work
- Verify frontend checks after optimization; review any warnings separately from errors.
- Bulk teacher analytics aggregation and paginated task-completion history; add query-count/pagination regression tests.
- Complete load/security/accessibility acceptance, external-service configuration, deployment, monitoring, and backup/restore verification before production.
