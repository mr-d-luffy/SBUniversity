# SiliconBrains University Web

Next.js 15 (App Router, TypeScript strict) + Tailwind CSS 3. Light theme, Bordo/Green/Cream palette (60:30:10) from `design.md`.

## Run
```bash
npm install
cp .env.example .env.local
npm run dev        # http://localhost:3000
```

## Demo accounts (`NEXT_PUBLIC_DEMO_MODE=true`)
| Role | Email | Password |
|---|---|---|
| Student | student@sbu.demo | Student@123 |
| Teacher | teacher@sbu.demo | Teacher@123 |
| Admin | admin@sbu.demo | Admin@123 |

Demo mode uses an httpOnly cookie and mock data in `src/lib/mock.ts`. **Set `NEXT_PUBLIC_DEMO_MODE=false` before deploying.**

## Connected development / production (Clerk)
1. Set `NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY` and `CLERK_SECRET_KEY`.
2. Clerk Dashboard → Sessions → customize token: `{ "metadata": "{{user.public_metadata}}" }` so `middleware.ts` can read `role`.
3. Admin sets `publicMetadata.role` (`student` default, `teacher`, `admin`).
4. Configure the API URL using the documented environment settings. Local development proxies requests to the API; demo mode uses mock data.

Permanent admin account deletion calls Clerk before deleting the application database record, so `CLERK_SECRET_KEY` must be present on the server. Never expose this key through a `NEXT_PUBLIC_*` variable.

## Structure
```
src/app/(app)/{student,teacher,admin,ranking,notices}   role-gated pages
src/components/ui        Button, Card, Badge, Toast primitives
src/components/shell     Shell (sidebar + topbar, mobile drawer)
src/components/features  TaskList, RankBoard, ApprovalQueue, UsersTable, AdminCourses, LiveWhiteboard
src/lib                  auth, actions, api, mock
src/middleware.ts        role gating (layer 1 of 3; the API enforces RBAC too)
```

## Current feature set

- Student and teacher dashboards, exams and tasks, Task Points ranking, notices, results/certificates, and virtual student identity.
- Aarsh Intelligence assistant with a shared animated orb in the full-page assistant and floating chat controls.
- Admin course creation/edit/deletion, teacher and student assignment, and user account deletion.
- Course-scoped live whiteboard for assigned teachers and enrolled students.
- The full project feature list and remaining hardening/deployment work are tracked in [`../Docs/phases.md`](../Docs/phases.md).

## Checks

```bash
npm run typecheck
npm run lint
npm run build
```
