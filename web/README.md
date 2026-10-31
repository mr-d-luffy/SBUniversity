# SiliconBrains University Web

Next.js 16 (App Router, TypeScript strict) + Tailwind CSS 4. Bordo/Green/Cream palette and light/dark theme tokens are documented in [`../Docs/design.md`](../Docs/design.md).

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
2. Configure Clerk and the backend webhook/JWT settings using `server/.env.example`.
3. New accounts default to student; an authorized admin changes roles through the application. The backend database supplies the authoritative role; a custom JWT role claim is not the role gate.
4. In development, the API helper uses Next.js's `/api/local-backend` rewrite, which targets `http://127.0.0.1:8010/api/v1` by default. Set `LOCAL_API_PROXY_TARGET` to override it. In production, set `NEXT_PUBLIC_API_BASE_URL` to the API base URL.

Permanent admin account deletion calls Clerk before deleting the application database record, so `CLERK_SECRET_KEY` must be present on the server. Never expose this key through a `NEXT_PUBLIC_*` variable.

## Structure
```
src/app/(app)/{student,teacher,admin,ranking,notices,community-chat} authenticated app pages
src/components/ui        Button, Card, Badge, Toast primitives
src/components/shell     Shell (sidebar + topbar, mobile drawer)
src/components/features  TaskList, RankBoard, ApprovalQueue, UsersTable, AdminCourses, LiveWhiteboard
src/lib                  auth, actions, api, mock
src/proxy.ts             authentication gate (the server layout/API use the authoritative role)
```

## Current feature set

- Student and teacher dashboards, exams and tasks, Task Points ranking, notices, results/certificates, and virtual student identity.
- Aarsh Intelligence assistant with a shared animated orb in the full-page assistant and floating chat controls.
- Admin course creation/edit/deletion, teacher and student assignment, and user account deletion.
- Course-scoped live whiteboard for assigned teachers and enrolled students.
- Community Chat with client-side WebCrypto encryption for text and voice messages. Device/private and conversation keys persist in IndexedDB without a TTL; conversation records and database message history are cleaned up after 10 hours of inactivity. See [`../Docs/SECURITY_AND_ACCESS_CONTROL.md`](../Docs/SECURITY_AND_ACCESS_CONTROL.md#community-chat-encryption) for storage and retention limits.
- The full project feature list and remaining hardening/deployment work are tracked in [`../Docs/phases.md`](../Docs/phases.md).

## Checks

```bash
npm run typecheck
npm run lint
npm run build
```
