# rules.md — SiliconBrains University Development Rules

> Mandatory for every developer and AI assistant working on this repo. This version reflects the live `web/`, `server/`, and mobile-client foundation as of 2026-11-01.

## 1. Golden Rules
1. Read `Docs/PRD.md`, `Docs/architecture.md`, `Docs/database.md`, `Docs/design.md`, `Docs/phases.md`, and `Docs/memory.md` before implementing.
2. Update `Docs/memory.md` after every meaningful change.
3. Do not change architecture, schema, or design system without updating the matching doc.
4. Reuse existing components/utilities before creating new ones.

## 2. Coding Standards
**DO**
- TypeScript `strict` on the frontend; type hints + Pydantic models on the backend.
- Small focused functions/components (< ~150 lines).
- Run the configured checks before commit: ESLint, TypeScript typecheck, and build (web); pytest (API). Ruff and Black are optional development dependencies; use them if installed and applicable.
- Backend package metadata supports Python 3.11+ (`server/pyproject.toml`); validate against the target runtime.

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
- Follow the structures in `Docs/architecture.md` as a guide and keep it synchronized with the code.
- Frontend: UI primitives in `components/ui`, feature components in `components/features`.
- Backend: **router → service → repository**. Routers never contain business logic or SQL.

## 5. Component Conventions
**DO** Server Components by default; add `"use client"` only for interactivity. Props typed with interfaces. Use design tokens from `design.md`.
**DON'T** Create a second Button/Card/Modal. Don't inline raw hex colors or random spacing — use the tokens in `design.md` §3.

## 6. API Conventions
- Prefix `/api/v1`; JSON; API fields use snake_case. The shared helper in `src/lib/api.ts` does not provide a generic snake_case-to-camelCase mapper.
- Use appropriate HTTP status codes (400/401/403/404/409/422/429); error bodies follow current FastAPI/application handlers and are not documented as a universal envelope.
- Protected endpoints require authentication and authorization; public routes are explicitly public.
- Bound or paginate list endpoints where appropriate; do not assume every current endpoint is paginated.
- PDFs: `Content-Type: application/pdf`, `Content-Disposition: attachment; filename=...`.

## 7. Database Conventions
- All changes via **Alembic migrations**; never edit the DB by hand in shared environments.
- UUID PKs, `timestamptz`, FK with explicit `ON DELETE`.
- Add indexes for FK columns and frequent filters.
- No duplicate data; derive when possible (see `database.md` §5).

## 8. Security Rules
**DO**
- Verify Clerk JWT on **every** protected request; the database role is authoritative for existing accounts. Never grant a role from request body/query.
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

Use `server/.env.example` and `web/.env.example` as the environment-variable inventory; required values depend on enabled features and deployment mode. Do not assume every variable is required for every local setup.

## 11. Error Handling Rules
- Backend: use the existing FastAPI/application exception handlers; do not promise a uniform error envelope unless the API implements one. No stack traces to clients.
- Frontend: error boundaries per route group; toast for recoverable errors; friendly empty/error states.
- Exam autosave failures retry with backoff and show "not saved" indicator.

## 12. Validation Rules
- Backend Pydantic is the source of truth; frontend validation should mirror backend constraints for UX only.
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
- Web dependencies are declared in `web/package.json` (Next.js 16, React 19, Tailwind CSS 4, Clerk, and Lucide). Backend runtime and optional development dependencies are declared in `server/pyproject.toml` and `server/requirements.txt`; review those manifests before adding assumptions about frameworks or test tooling.

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
- Frontend: the current package scripts expose `lint`, `typecheck`, `build`, `dev`, and `start`; no frontend component-test or Playwright script is defined in `web/package.json`.
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
- Use semantic palette tokens declared with Tailwind CSS v4 `@theme` in `web/src/app/globals.css`.
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
- Serve the leaderboard from Redis; fall back to the SQL in `database.md` when Redis is empty or unavailable. Rebuild overall scores from DB at startup and refresh them on score-changing events.
- Enforce ownership: teachers create/approve tasks only for their **own courses**.

**DON'T**
- Don't accept or trust points from the client, query string, or webhook payloads.
- Don't use exam marks, `results.rank_in_exam`, or any other source for the Live Ranking.
- Don't use `ZINCRBY` for ranking (it can drift); always recompute and set.
- Don't let students approve/complete assignment tasks without teacher approval.
- Don't edit `points` of a task that already has completions — create a new task.
- Don't hard-delete published exams or tasks that have completions (archive instead).

**Tests (mandatory):** no double-award (retry + multi-attempt), points awarded in the same transaction (rollback leaves no points), approve/reject flow, revoke removes points and rank, tie-break order, Redis rebuild equals SQL result, suspended users excluded, teacher cannot approve another teacher's course.

## 21. Community Chat Encryption Rules
- Encrypt message text and audio in the browser using the existing WebCrypto utility; never send plaintext or private keys to the API.
- Persist device private keys and conversation keys in IndexedDB. They have no application TTL; document device/browser storage loss and key-provisioning limits.
- Treat server-stored message bodies, audio objects, and key envelopes as ciphertext, but remember that sender/recipient, timestamps, role, and other metadata remain visible to the service.
- The 10-hour inactivity cleanup removes conversation/message database rows and key envelopes; it does not delete uploaded audio objects. Do not describe audio object retention as complete until that storage cleanup is implemented/configured.
