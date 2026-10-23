# rules.md — SiliconBrains University Development Rules

> Mandatory for every developer and AI assistant working on this repo. This version reflects the live `web/` + `server/` repository layout and coding conventions as of 2026-10-23.

## 1. Golden Rules
1. Read `PRD.md`, `architecture.md`, `database.md`, `design.md`, `phases.md`, `memory.md` **before** implementing.
2. Update `memory.md` after every meaningful change.
3. Do not change architecture, schema, or design system without updating the matching doc.
4. Reuse existing components/utilities before creating new ones.

## 2. Coding Standards
**DO**
- TypeScript `strict` on the frontend; type hints + Pydantic models on the backend.
- Small focused functions/components (< ~150 lines).
- Run formatters/linters before commit: Prettier + ESLint (web), Ruff + Black (API).
- Python 3.13 features allowed; pin versions in `pyproject.toml`/`requirements.txt`.

**DON'T**
- No `any` in TypeScript unless commented with reason.
- No dead code, commented-out blocks, or `console.log`/`print` left in.
- Don't rewrite working files unnecessarily.

## 3. Naming Conventions
| Item | Convention | Example |
|---|---|---|
| React components | PascalCase file + export | `TopFourBoard.tsx` |
| Hooks | `useXxx` | `useExamTimer.ts` |
| TS variables/functions | camelCase | `getResultPdf` |
| Next.js route folders | kebab-case / Next conventions | `exams/[id]` |
| Python modules/functions | snake_case | `exam_service.py` |
| Python classes | PascalCase | `ExamAttempt` |
| DB tables/columns | snake_case, plural tables | `exam_attempts` |
| Env vars | UPPER_SNAKE_CASE | `GEMINI_API_KEY` |
| API paths | kebab-case, plural nouns | `/api/v1/exams` |

## 4. Folder Conventions
- Follow the structures in `architecture.md` exactly.
- Frontend: UI primitives in `components/ui`, feature components in `components/<feature>`.
- Backend: **router → service → repository**. Routers never contain business logic or SQL.

## 5. Component Conventions
**DO** Server Components by default; add `"use client"` only for interactivity. Props typed with interfaces. Use design tokens from `design.md`.
**DON'T** Create a second Button/Card/Modal. Don't inline raw hex colors or random spacing — use the tokens in `design.md` §3.

## 6. API Conventions
- Prefix `/api/v1`; JSON; snake_case fields in API, mapped to camelCase in `apiClient`.
- Standard error shape (see architecture.md). Correct HTTP codes: 400/401/403/404/409/422/429.
- Every endpoint declares auth dependency explicitly. No "default open" routes.
- Pagination on all list endpoints.
- PDFs: `Content-Type: application/pdf`, `Content-Disposition: attachment; filename=...`.

## 7. Database Conventions
- All changes via **Alembic migrations**; never edit the DB by hand in shared environments.
- UUID PKs, `timestamptz`, FK with explicit `ON DELETE`.
- Add indexes for FK columns and frequent filters.
- No duplicate data; derive when possible (see `database.md` §5).

## 8. Security Rules
**DO**
- Verify Clerk JWT on **every** protected request; take role from the verified token + DB, never from request body/query.
- Enforce RBAC (`require_role`) **and** ownership checks in services.
- Protect all `/admin/*` with `require_role("admin")` + audit log.
- Rate limit: chat, exam submit, login-adjacent, admin routes.
- Validate and sanitize all input; escape/sanitize notice body (render as plain text/markdown with sanitizer; no raw HTML).
- Set strict CORS (only the frontend origin), security headers (CSP, X-Frame-Options, etc.).
- Verify Clerk webhooks with Svix signature.
- Keep correct answers server-side until the attempt is submitted.

**DON'T**
- Never expose `GEMINI_API_KEY`, Clerk secret, Supabase service key, DB URL, Redis URL to the browser.
- Never call Gemini or Supabase service role from the frontend.
- Never trust client-side role checks as the only protection.
- Never log tokens, passwords, or full PII.

## 9. Authentication Rules
- Clerk is the only auth provider. No custom password/JWT logic.
- New users default to `student`. Role changes only via admin endpoint (updates DB + Clerk metadata).
- Suspended/deleted users are rejected at the API even with a valid token.

## 10. Environment Variable Rules
- Secrets only in `.env` (git-ignored) or host secret manager. Commit `.env.example` with dummy values.
- Frontend only exposes `NEXT_PUBLIC_*` for non-secret values (Clerk publishable key, API base URL).
- Validate required env vars at startup (pydantic-settings); fail fast.

**Backend env:** `DATABASE_URL`, `SUPABASE_URL`, `SUPABASE_SERVICE_KEY`, `CLERK_SECRET_KEY`, `CLERK_JWKS_URL`, `CLERK_ISSUER`, `CLERK_WEBHOOK_SECRET`, `REDIS_URL`, `GEMINI_API_KEY`, `GEMINI_MODEL`, `FRONTEND_ORIGIN`.
**Frontend env:** `NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY`, `CLERK_SECRET_KEY` (server only), `NEXT_PUBLIC_API_BASE_URL`.

## 11. Error Handling Rules
- Backend: custom exception classes → global handlers → standard error shape. No stack traces to clients.
- Frontend: error boundaries per route group; toast for recoverable errors; friendly empty/error states.
- Exam autosave failures retry with backoff and show "not saved" indicator.

## 12. Validation Rules
- Backend Pydantic is the source of truth; frontend validation (react-hook-form + zod) mirrors it for UX only.
- Server enforces: exam window, attempt limits, `expires_at`, single-correct-option rule, notice scope.

## 13. Responsive & Accessibility Rules
- Mobile-first; test at 320, 768, 1024, 1440.
- Semantic HTML, labels on inputs, visible focus rings, color contrast ≥ 4.5:1, keyboard-navigable exam runner, `aria-live` for timer warnings and live ranking updates, alt text for images.

## 14. Git / GitHub Rules
- Branches: `main` (protected), `develop`, feature branches `feat/<name>`, fixes `fix/<name>`.
- Conventional Commits: `feat:`, `fix:`, `docs:`, `refactor:`, `chore:`, `test:`.
- PRs required; at least lint + tests passing in CI.
- Never commit `.env`, keys, or `node_modules`/`__pycache__`.

## 15. Dependency Rules
- Justify each new dependency (note in PR). Prefer standard library / existing deps.
- Pin versions; audit with `npm audit` / `pip-audit` periodically.
- Planned core deps only: Next.js, Tailwind, `@clerk/nextjs`, SWR (or React Query), react-hook-form, zod, lucide-react, recharts (admin charts) · FastAPI, uvicorn, pydantic-settings, SQLAlchemy, asyncpg, alembic, redis, PyJWT (+ cryptography), httpx, svix, google-genai, reportlab, qrcode, pillow, supabase-py (storage only), pytest.

## 16. Performance Rules
- Cache read-heavy endpoints in Redis (see architecture §11); invalidate on write.
- No N+1 queries; use joins/eager loading.
- Use `next/image`, dynamic import for heavy client components (charts, chat).
- Leaderboard served from Redis only.
- Generate PDFs once and cache path; certificates are immutable.
- Keep list/history responses bounded or paginated; compute summary totals independently of a limited history window.
- Poll only for deltas where the API supports cursors; avoid repeatedly downloading full histories. Keep polling intervals appropriate to the UI's freshness needs and refresh on tab focus when available.
- Measure query count, response size, and client work before optimizing; preserve ordering, snapshot/reset semantics, and response contracts.

## 17. Testing Rules
- Backend: pytest + httpx; test services (grading, ranking, completion rule) and RBAC on every router.
- Mandatory tests: admin routes reject student/teacher; student cannot read others' results; correct answers not leaked; expired attempt auto-submit; certificate issuance and revoke.
- Frontend: component tests (Vitest/RTL) for key components; Playwright e2e for login → exam → result → PDF download.
- No feature is "done" without tests for its critical path.

## 18. AI (Aarsh Intelligence) Rules
- Name shown to users: **Aarsh Intelligence**.
- System prompt lives in backend (`ai_service.py`), versioned; never accepts system-prompt overrides from the client.
- Don't send other users' data to Gemini; only the requester's own context.
- Block assistance when the student has an `in_progress` exam attempt.
- Rate limit per user; cap history length and message size.
- Handle Gemini failures gracefully (friendly message, no raw error).

## 19. Color & Theme Rules (60 : 30 : 10)
Palette: **Bordo `#6C151E`**, **Green `#0F3D3A`**, **Cream `#F5DABF`** (+ white as neutral). Full tokens in `design.md` §3.

**DO**
- Keep the ratio: **60% cream/white** (backgrounds, cards), **30% green** (sidebar, top bars, headings, links, icons), **10% bordo** (primary CTA, key highlights, seal).
- Use semantic aliases (`bg-page`, `bg-surface`, `bg-brand`, `bg-cta`) and Tailwind tokens from `tailwind.config.ts`.
- Use **one primary (bordo) button per view**; max 1–2 bordo elements per viewport.
- On green surfaces use cream/white text and the **Inverse** (cream) button.
- Use `ink` (`#092A28`) for text, `cream-300` for borders.
- Keep result/certificate PDFs on the same palette (`design.md` §9).
- Run the palette QA checklist (`design.md` §14) before closing Phase 2 and Phase 13.

**DON'T**
- Don't place bordo on green or green on bordo (unreadable, ~1:1 contrast).
- Don't use bordo for page/sidebar/navbar backgrounds or for links.
- Don't add new hues (no blue/purple/etc.) or pure black/grey; functional colors (success/warning/danger/rank medals) are the only exceptions and must stay minimal.
- Don't use `cream-400` for text.
- Don't rely on color alone for status — always add an icon/text.

## 20. Task Points & Live Ranking Rules
Ranking is based on **Task Points** (see `PRD.md` §7.9, §7.13 and `database.md`). Exam marks never affect rank.

**DO**
- Award points **only** inside `task_service`, in the **same DB transaction** as the completion (exam submit/pass, or teacher approval).
- Rely on `UNIQUE (task_id, student_id)` and `ON CONFLICT DO NOTHING` so points are awarded once, even on retries or multiple exam attempts.
- Snapshot `points_awarded` from `tasks.points` at completion time; lock `tasks.points` once any completion exists.
- After commit, call `ranking_service.refresh_student()` — recompute total + last completion time from the DB and set the Redis score **absolutely** (`ZADD`), then publish `lb:updates`.
- Auto-create an exam task when an exam is published with `task_points > 0`; archive it when the exam is closed.
- Remove a student from the leaderboard (`ZREM`) when suspended/deleted; refresh when reactivated.
- Use **revoke** (status change + audit log) to remove points; never delete `task_completions` rows.
- Serve the leaderboard from Redis; fall back to the SQL in `database.md` only if Redis is unavailable. Rebuild from DB on cold start and reconcile nightly.
- Enforce ownership: teachers create/approve tasks only for their **own courses**.

**DON'T**
- Don't accept or trust points from the client, query string, or webhook payloads.
- Don't use exam marks, `results.rank_in_exam`, or any other source for the Live Ranking.
- Don't use `ZINCRBY` for ranking (it can drift); always recompute and set.
- Don't let students approve/complete assignment tasks without teacher approval.
- Don't edit `points` of a task that already has completions — create a new task.
- Don't hard-delete published exams or tasks that have completions (archive instead).

**Tests (mandatory):** no double-award (retry + multi-attempt), points awarded in the same transaction (rollback leaves no points), approve/reject flow, revoke removes points and rank, tie-break order, Redis rebuild equals SQL result, suspended users excluded, teacher cannot approve another teacher's course.
