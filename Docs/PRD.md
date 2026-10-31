# PRD.md — SiliconBrains University Product Requirements

> Source of truth for WHAT we are building. Version 0.2 (repository-aligned snapshot). Assumptions are marked **[A#]** and listed in section 17. This file reflects the current repository snapshot as of 2026-11-01; it does not imply a verified production deployment.

## 1. Project Name
**SiliconBrains University**

## 2. Overview
SiliconBrains University is a web-based learning platform where students take online exams, receive generated results and course certificates, see a live leaderboard, and use an AI study assistant called **Aarsh Intelligence**. Teachers manage courses, exams, notices, tasks, and live classroom sessions. Admins manage courses and accounts, monitor progress and analytics, and control course membership and teaching assignments.

## 3. Problem Statement
Institutions typically run exams, results, certificates, notices and student identity across disconnected tools. This causes manual result work, forged or unverifiable certificates, missed announcements, and no real-time view of student/teacher performance.

## 4. Goals
1. One platform for the exam → result → certificate lifecycle.
2. Role-based experience for Student, Teacher, Admin.
3. Server-generated, verifiable PDFs (results, certificates) downloaded from the frontend.
4. Live Top-4 ranking driven by **Task Points**, awarded automatically when tasks are completed.
5. Admin control over users, courses, course teacher assignments, and student enrollments, plus visibility into progress and live analytics.
6. Context-aware AI assistant (Aarsh Intelligence) powered by Google Gemini.
7. Community Chat for student rooms, peer conversations, and staff support, with browser-side end-to-end encryption.

## 5. Target Users & Roles
| Role | Who | Key powers |
|---|---|---|
| **Student** | Enrolled learners | Take exams, view results, download result PDF & certificates, view ID card, view ranking & notices, chat with AI |
| **Teacher** | Faculty | Create/manage own courses' exams & questions, view own students' results, post notices (scoped), use AI |
| **Admin** | Platform staff | User and course control, role assignment, course teacher/student assignment, progress check, analytics, notice control, certificate revoke |

## 6. Core Features
1. Landing page (public)
2. Clerk authentication with three roles
3. Student Dashboard
4. Student Profile as **Virtual ID Card** (with QR for verification)
5. Teacher Dashboard
6. Exam engine (timed, server-validated)
7. Result page + backend-generated Result PDF
8. Certificate page + backend-generated Certificate PDF (public verify link)
9. Live Ranking Page (Top 4) — ranked by **Task Points**, updated automatically on task completion
10. Notice Board (Admin + Teachers post; everyone reads)
11. Aarsh Intelligence chatbot (Gemini)
12. Admin panel: User Control, Course Management, Progress Check, Live Analytics, Notice Control
13. Tasks & Task Points (teacher-created tasks, points auto-awarded on completion)
14. Course-scoped live whiteboard with teacher controls and enrolled-student participation
15. Community Chat with encrypted text and voice messages

## 7. Functional Requirements
### 7.1 Authentication & Roles
- FR-A1: Sign up / sign in via Clerk (email + optional Google social).
- FR-A2: New users default to `student`. Only Admin can promote to `teacher` or `admin`. **[A1]**
- FR-A3: Role stored in Clerk `publicMetadata.role` and mirrored in DB `users.role`.
- FR-A4: Suspended users cannot access any protected API or page.

### 7.2 Landing Page
- Hero, features, how-it-works, live stats (public counts), Sign in / Sign up CTAs, footer. Certificate verification input (public).

### 7.3 Student Dashboard
- Enrolled courses with progress %, upcoming exams, recent results, latest notices, open tasks, **Task Points total**, current rank, certificates earned, AI chat shortcut.

### 7.4 Virtual ID Card (Student Profile)
- Card-style layout: photo, name, student code (e.g. `SBU-2026-0001`), department, batch, validity, QR code (opens public verify page showing name + status only).
- Editable fields: phone, photo. Name/code/department are admin-controlled.

### 7.5 Teacher Dashboard
- My courses, exams (draft/published/closed), submissions count, average score, pass rate, recent notices, pending task approvals, create-exam / create-task CTAs.

### 7.6 Exam Page
- Student sees only exams for enrolled courses, within the start/end window.
- Timer is **server-authoritative** (`expires_at`). Auto-submit on expiry.
- MCQ single-choice (MVP). Answers autosaved per question.
- Correct answers are **never** sent to the client before submission.
- Teacher creates exam: title, duration, marks, pass marks, negative marking (optional), attempts, questions/options.
- On **publish**, the teacher sets **Task Points** for the exam (0 = no points). A linked exam task is created automatically (see 7.13).

### 7.7 Result Page
- Score, percentage, pass/fail, grade, rank in exam, per-question review (after exam closes, configurable by teacher).
- **Download Result PDF** (generated by backend).

### 7.8 Certificate Page
- Lists certificates earned. Certificate is issued automatically when the student completes a course (see 7.8.1).
- **Download Certificate PDF** (generated by backend, contains unique code + QR).
- Public verify page: `/verify/[code]`.
- 7.8.1 Completion rule **[A2]**: all published exams of the course passed → certificate issued; admin can revoke.

### 7.9 Live Ranking Page (Top 4)
- Ranked by **Task Points** = total points of a student's completed tasks (see 7.13). Points are awarded **automatically** on task completion, so the ranking needs no manual action.
- Shows the top 4 students: rank, name, avatar, total points, tasks completed. Updates live (SSE) the moment points are awarded. Filter: Overall / by Course.
- Logged-in student also sees "Your rank" and their points.
- **Tie-break [A3]:** equal points → the student who reached that total first ranks higher.
- Exam marks do **not** affect rank (they appear only on the Result page).
- Suspended/deleted users are excluded; students with 0 points are not listed.

### 7.10 Notice Board
- Admin: create/edit/delete/pin any notice, target All/Students/Teachers.
- Teacher: create/edit/delete **own** notices, targeted to own course's students.
- Students/Teachers: read notices relevant to them; priority badges; expiry.

### 7.11 Aarsh Intelligence (AI Assistant)
- Floating chat widget + full chat page.
- Backend proxies Google Gemini; API key never in browser.
- Capabilities: study help, explain exam topics, platform help (how to download certificate), summarize notices, personal context (own results/rank) for logged-in user.
- Guardrails: no answers to *live in-progress exam* questions (blocked while the student has an active attempt); rate limited; history stored per user.

### 7.12 Admin
- **User Control:** list/search/filter, change role, suspend/reactivate, permanently delete accounts, assign student code/department, enroll/unenroll. Permanent account deletion also deletes the Clerk identity; student-owned records cascade, while authored teaching content is retained without its author reference.
- **Course Management:** create, edit, and permanently delete courses; assign multiple teachers and selected students, or enroll all active students. Existing primary-teacher assignment remains supported.
- **Progress Check:** per-student and per-course progress, exam history, certificate status, task completions and points; **revoke** a task completion (its points are removed, action audited).
- **Live Analytics:** teachers (exams created, submissions, avg score, pass rate) and students (active now, avg score, completion rate); auto-refresh.
- **Notice Control:** moderate all notices (edit, pin, archive, delete).
- All admin routes secured (see 11).
- Assigned teachers cannot be demoted or deleted until reassigned. Administrators cannot delete their own account or the last active administrator.

### 7.13 Tasks & Task Points
- A **Task** belongs to a course and has: title, description, **points** (integer ≥ 0), type, optional due date, and a verification mode.
- **Task types**
  | Type | Created by | Completion | Verification |
  |---|---|---|---|
  | **Exam task** | Auto-created when a teacher publishes an exam with Task Points > 0 | Student **passes** the exam | Automatic |
  | **Assignment task** | Teacher/Admin for a course | Student submits a short note/link | Teacher approves |
- **Automated awarding**
  - Exam task: on submit, if the student passed → completion recorded and points awarded instantly, in the same transaction as grading.
  - Assignment task: on teacher **approval** → completion recorded and points awarded instantly. Rejection awards nothing (student may resubmit).
  - Leaderboard refreshes automatically after every award (see 7.9).
- Points are awarded **once per task per student** (retries or extra attempts never double-award).
- Points are fixed per task and **locked** once anyone has completed it (create a new task to change points).
- Student: sees open / pending / completed tasks, points per task, total points; gets an in-app toast when points are awarded.
- Teacher: create/edit/archive tasks for **own courses**, review the approval queue. Admin: all courses, can revoke a completion.
- Points are computed server-side only; clients can never send or edit points.

### 7.14 Live Classroom Whiteboard
- An assigned course teacher or administrator can create and end a live whiteboard session for a course.
- Enrolled students explicitly join to view the board and participate in class chat; students cannot access another course's session.
- Teachers can draw, undo, and clear the board. Students have read-only canvas access.
- Chat messages expire after ten minutes; whiteboard strokes remain with the session history.

### 7.15 Community Chat and encryption
- Community Chat provides a shared student room, student-to-student direct conversations, and role-specific staff support conversations.
- The browser uses WebCrypto to encrypt text and recorded audio with AES-GCM conversation keys. Device identity keys use RSA-OAEP; the browser wraps each conversation key to registered participant-device public keys and stores the private device key and conversation keys in IndexedDB.
- The API stores encrypted message bodies/audio, public device keys, encrypted key envelopes, and conversation metadata. It does not receive message plaintext or private keys. Encryption does not hide sender/recipient identity, timing, role, or other service metadata.
- Browser-held device and conversation keys have no application TTL. Clearing browser storage or changing browser/device can make prior messages unreadable on that device; a device without a key needs a device that already has access to provide an envelope.
- A conversation's expiry is reset on each new message. The backend removes expired conversation and message database rows, including their key envelopes, after 10 hours without a new message. Uploaded audio objects are stored separately and are not deleted by that database cleanup; their storage retention must be managed/verified separately.

## 8. Non-Functional Requirements
| Area | Requirement |
|---|---|
| Performance | Page TTFB < 500 ms (cached); API p95 < 300 ms for reads; leaderboard < 50 ms (Redis) |
| Availability | 99.5% target for MVP |
| Scalability | 5,000 registered users, 500 concurrent exam takers **[A4]** |
| Security | Clerk JWT verification, RBAC on every endpoint, rate limiting, audit log |
| Accessibility | WCAG 2.1 AA basics |
| Responsive | Mobile-first (320px+) |
| Reliability | Exam answers autosaved; submit is idempotent |
| Privacy | Minimal PII; public verify pages expose no sensitive data |

## 9. Pages / Screens
| Route | Page | Access |
|---|---|---|
| `/` | Landing | Public |
| `/sign-in`, `/sign-up` | Clerk auth | Public |
| `/verify/[code]` | Certificate / ID verification | Public |
| `/student/dashboard` | Student dashboard | Student |
| `/student/profile` | Virtual ID card | Student |
| `/student/exams`, `/student/exams/[id]` | Exam list / exam taking | Student |
| `/student/results`, `/student/results/[id]` | Results | Student |
| `/student/certificates` | Certificates | Student |
| `/student/tasks` | My tasks & Task Points | Student |
| `/ranking` | Live Top 4 | Auth |
| `/notices` | Notice board | Auth |
| `/assistant` | Aarsh Intelligence | Auth |
| `/community-chat` | Encrypted community conversations | Auth |
| `/teacher/dashboard` | Teacher dashboard | Teacher |
| `/teacher/exams`, `/teacher/exams/new`, `/teacher/exams/[id]` | Manage exams | Teacher |
| `/teacher/notices` | Teacher notices | Teacher |
| `/teacher/tasks` | Manage tasks & approval queue | Teacher |
| `/whiteboard` | Course live whiteboard | Assigned teacher / enrolled student |
| `/admin` | Admin overview | Admin |
| `/admin/users` | User control | Admin |
| `/admin/courses` | Course creation, teacher assignments, and student enrollment | Admin |
| `/admin/progress` | Progress check | Admin |
| `/admin/analytics` | Live analytics | Admin |
| `/admin/notices` | Notice control | Admin |

## 10. User Journeys
**Student:** Sign up → dashboard → open enrolled course → start exam → answer → submit → result page → download Result PDF → pass all course exams → certificate auto-issued → download → earns Task Points automatically as tasks complete → checks live rank.

**Teacher:** Sign in (role granted by admin) → create exam + questions → publish → monitor submissions → post notice → view results.

**Admin:** Sign in → promote user to teacher → check analytics → moderate notice → revoke/re-issue certificate.

**Public verifier:** Scan certificate QR → `/verify/[code]` → sees valid/revoked.

## 11. Authentication & Admin Security Requirements
- Clerk is the only identity provider. Backend never stores passwords.
- The frontend proxy requires an authenticated session for protected paths; it is not the authoritative role gate. The FastAPI API enforces `require_role("admin")`, and sensitive admin writes are audited.
- The backend uses the database role for existing accounts after verifying the Clerk JWT; a client-supplied role is never an authorization grant.
- Admin-only actions require re-checking DB `users.status = active`.
- Admin MFA is an external Clerk configuration requirement and is not verified by this repository. **[A5]**

## 12. API Requirements
REST JSON under `/api/v1`. Auth via `Authorization: Bearer <Clerk JWT>`. PDFs returned as `application/pdf` streams. Full endpoint list in `architecture.md`.

## 13. Notifications
- In-app only (notice board badge, toast when Task Points are awarded). No email/SMS in MVP.

## 14. Integrations
Clerk (auth), Supabase PostgreSQL (+ Storage for generated PDFs and photos), Redis (cache, leaderboard, rate limiting, pub/sub), Google Gemini API (chatbot).

## 15. Future Features
Lesson/video content & lesson-based progress, weekly/monthly leaderboards, streaks/badges, auto-checked assignment types, descriptive/coding questions, proctoring, email notifications, ID card PDF/wallet download, multi-language, parent portal, payments.

## 16. Out of Scope (MVP)
Payments, video lessons/video conferencing, proctoring/webcam, email/SMS, multi-tenant (multiple universities), manual grading. The repository also contains a student-scoped Flutter Android client foundation; it is not feature-complete or production-ready (see [`mobile/README.md`](../mobile/README.md)).

## 17. Assumptions (please confirm or correct)
- **[A1]** Teacher/Admin roles are granted only by Admin (no self-selection of role at signup).
- **[A2]** No lesson content in MVP; course progress = % of the course's published exams passed. Certificate issued at 100%.
- **[A3]** Live ranking = total **Task Points** (sum of points of completed, non-revoked tasks), all-time. Tie-break: whoever reached the total first. Exam marks do not affect rank.
- **[A4]** Expected scale ≈ 5,000 users / 500 concurrent exam takers.
- **[A5]** Admin MFA is expected to be configured through Clerk by the deployment owner; this repository does not verify or enforce that setting.
- **[A6]** Python version is **3.13** (interpreted from "python13.3").
- **[A7]** Exam format is MCQ single-answer in MVP.
- **[A8]** Students are enrolled by Admin (or Teacher for own course); no self-enrollment in MVP.
- **[A9]** Task points are fixed per task (not proportional to exam score). Exam tasks complete when the student **passes**.
- **[A10]** Assignment tasks need teacher approval; points are auto-awarded at the moment of approval.
- **[A11]** Due dates are informational (no late penalty or expiry of points in MVP). No weekly/monthly reset.
