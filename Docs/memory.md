# SiliconBrains University Project Memory / Current State

> Update this file after meaningful project changes.

## Current Status
- **Current focus:** Repository documentation alignment with the current `web/`, `server/`, and mobile-client foundation as of 2026-11-01.
- **Deployment:** Not verified. Do not assume production services, secrets, or migrations have been configured.
- **Backend:** FastAPI (Python package metadata requires 3.11+), SQLAlchemy async, PostgreSQL/Supabase, Redis, Clerk-backed auth.
- **Frontend:** Next.js 16 App Router, TypeScript, Tailwind CSS 4, role-based dashboard routes.
- **Authentication:** Clerk; roles are student, teacher, and admin.
- **AI:** Aarsh Intelligence backed by Google Gemini.
- **Live ranking:** Task Points, Redis sorted sets, server updates and SSE.
- **Design:** Bordo `#6C151E`, Green `#0F3D3A`, Cream `#F5DABF`.

## Implemented Feature Areas
- Student, teacher, and admin routes are implemented in the app and API: exams, tasks, results, certificates, notices, ranking, planner, community chat, whiteboard, assistant, and admin management.
- Admin user controls include role assignment, status changes, permanent deletion workflow, and course management with teacher/student assignment.
- Permanent account deletion removes the Clerk identity first and then the application record; authored records remain usable with a cleared author reference when required by policy.
- Course-scoped live whiteboard sessions persist strokes while expiring live messages after ten minutes.
- Community Chat encrypts text/audio in the browser using WebCrypto; device and conversation keys persist in IndexedDB without a TTL. Conversation/message database rows and envelopes expire 10 hours after the latest message; uploaded audio objects are outside that database cleanup.
- A student-scoped Flutter Android client foundation exists, but it is not feature-complete or production-ready ([`mobile/README.md`](../mobile/README.md)).
- Aarsh Intelligence and the public credential verification flow are implemented in the UI and backend.

## Repository Snapshot
- `web/src/app/` contains the public, student, teacher, admin, assistant, whiteboard, ranking, planner, and community-chat routes.
- `server/app/api/v1/` contains the corresponding API routers, including `admin/` routes for analytics, users, courses, notices, and progress.
- `server/app/db/models/` is the source of truth for the persisted schema; migrations are managed through Alembic.
- `server/app/main.py` enforces production hardening checks (HTTPS-only origins, secure Redis/database requirements, and disabled dev auth bypass).

## Validation Status
- The current repository includes working web and backend route architecture, type-safe frontend code, and SQLAlchemy models with API/service layering.
- Production deployment, external service configuration, and load testing remain out of scope for this repo snapshot and must be validated separately.
- Documentation should stay aligned with the live code in `web/` and `server/` instead of legacy planning artifacts.

## Important Decisions
| Decision | Detail |
|---|---|
| Backend-only data access | Browser does not access Supabase directly; API enforces authorization and ownership. |
| Permanent course deletion | Deletes the course and its related records after confirmation. |
| Permanent account deletion | Delete Clerk identity before database user; fail without deleting DB if provider deletion fails. |
| Teacher protection | A teacher assigned to a course cannot be demoted or deleted until reassigned. |
| Multiple course teachers | `course_teachers` is authoritative for additional assignments; `courses.teacher_id` remains primary for compatibility. |
| Whiteboard history | Strokes remain for session history; live class chat expires after ten minutes. |
| Community Chat | Text/audio payloads are encrypted client-side. Browser keys have no TTL; conversation history and server key envelopes are cleaned after 10 hours of inactivity. Audio object cleanup needs separate storage retention. |

## Recent Changes
- 2026-10-31: Added Community Chat end-to-end encryption support and migration `019_community_chat_e2ee`; database cleanup removes expired conversation history and key envelopes after 10 hours of inactivity.

## Remaining Work
- Verify frontend checks after optimization; review any warnings separately from errors.
- Bulk teacher analytics aggregation and paginated task-completion history; add query-count/pagination regression tests.
- Complete load/security/accessibility acceptance, external-service configuration, deployment, monitoring, and backup/restore verification before production.
