# database.md — SiliconBrains University Database Design

## 1. Technology
- **Supabase PostgreSQL** (database name: `postgres`, schema `public`)
- Access: **FastAPI only** (SQLAlchemy 2 async + asyncpg) using the Supabase connection string (pooler).
- Migrations: **Alembic**.
- Extensions: `pgcrypto` (UUID), `citext` (case-insensitive email).
- Conventions: UUID PKs (`gen_random_uuid()`), `timestamptz`, `created_at`/`updated_at` on all mutable tables, snake_case.

## 2. Enums
```
user_role:        student | teacher | admin
user_status:      active | suspended | deleted
enrollment_status: active | completed | dropped
exam_status:      draft | published | closed
attempt_status:   in_progress | submitted | auto_submitted
notice_audience:  all | students | teachers | course
notice_priority:  normal | important | urgent
notice_status:    draft | published | archived
chat_role:        user | model
planner_entry_kind: learning_plan | note | sticky_note | event | voice_note
planner_note_shape: rectangle | rounded | circle | cloud | star
task_type:        exam | assignment
task_verification: auto | teacher_approval
task_status:      active | archived
task_resource_type: video | learning_source
task_assignment_scope: all_students | selected_students
completion_status: pending_review | completed | rejected | revoked
```

## 3. Entity Relationship Overview
```
users 1──1 student_profiles
users 1──1 teacher_profiles
departments 1──* student_profiles / teacher_profiles / courses
users(teacher) *──* courses        (via course_teachers; courses.teacher_id remains the primary teacher)
users(student) *──* courses   (via enrollments)
courses 1──* exams 1──* questions 1──* question_options
exams 1──* exam_attempts *──1 users(student)
exam_attempts 1──* attempt_answers *──1 questions
exam_attempts 1──1 results
users(student) *──* courses → certificates
courses 1──* tasks            (exams 1──0..1 tasks, for exam-type tasks)
tasks 1──* task_completions *──1 users(student)
tasks 1──* task_recipients *──1 users(student)   (selected-student assignments)
tasks 1──* task_video_progress *──1 users(student)
users 1──* notices (author)
users 1──* chat_sessions 1──* chat_messages
users 1──* community_messages
community_conversations 1──* community_messages
users 1──* planner_entries (private owner)
courses 1──* whiteboard_sessions 1──* whiteboard_strokes
whiteboard_sessions 1──* whiteboard_messages (expires after 10 minutes)
users 1──* audit_logs (actor)
```

## 4. Tables

### users
```
users
 ├── id                uuid PK default gen_random_uuid()
 ├── clerk_user_id     text UNIQUE NOT NULL
 ├── email             citext UNIQUE NOT NULL
 ├── full_name         text NOT NULL
 ├── avatar_url        text NULL
 ├── role              user_role NOT NULL default 'student'
 ├── status            user_status NOT NULL default 'active'
 ├── last_seen_at      timestamptz NULL
 ├── created_at        timestamptz NOT NULL default now()
 └── updated_at        timestamptz NOT NULL default now()
```
Indexes: `(role)`, `(status)`, `(lower(full_name))`.

### departments
```
departments
 ├── id        uuid PK
 ├── code      text UNIQUE NOT NULL
 ├── name      text UNIQUE NOT NULL
 └── created_at timestamptz default now()
```

### student_profiles
```
student_profiles
 ├── user_id          uuid PK → users.id ON DELETE CASCADE
 ├── student_code     text UNIQUE NOT NULL        -- SBU-2026-0001
 ├── department_id    uuid NULL → departments.id
 ├── batch_year       int NULL
 ├── phone            text NULL
 ├── date_of_birth    date NULL
 ├── photo_path       text NULL                   -- Supabase Storage
 ├── id_valid_until   date NULL
 ├── qr_token         text UNIQUE NOT NULL        -- random, for public verify
 └── updated_at       timestamptz
```

### teacher_profiles
```
teacher_profiles
 ├── user_id        uuid PK → users.id ON DELETE CASCADE
 ├── employee_code  text UNIQUE NOT NULL
 ├── department_id  uuid NULL → departments.id
 ├── designation    text NULL
 └── bio            text NULL
```

### courses
```
courses
 ├── id            uuid PK
 ├── code          text UNIQUE NOT NULL
 ├── title         text NOT NULL
 ├── description   text NULL
 ├── department_id uuid NULL → departments.id
 ├── teacher_id    uuid NOT NULL → users.id        -- primary teacher
 ├── is_published  boolean NOT NULL default false
 ├── created_at / updated_at
```
Indexes: `(teacher_id)`, `(department_id)`.
Admin course creation can enroll every currently active student or selected students by inserting active `enrollments` rows in the same transaction. Suspended/deleted accounts cannot be newly enrolled. Course teacher assignments are stored in `course_teachers`; existing primary teachers are backfilled by migration.

### course_teachers
```
course_teachers
 ├── course_id  uuid NOT NULL → courses.id ON DELETE CASCADE
 ├── teacher_id uuid NOT NULL → users.id ON DELETE CASCADE
 └── PRIMARY KEY (course_id, teacher_id)
```
Index: `(teacher_id)`. The course's `teacher_id` is retained as its primary teacher for compatibility; this table records every teacher authorized to manage that course.

### enrollments
```
enrollments
 ├── id                uuid PK
 ├── student_id        uuid NOT NULL → users.id
 ├── course_id         uuid NOT NULL → courses.id
 ├── status            enrollment_status default 'active'
 ├── progress_percent  numeric(5,2) default 0     -- derived, cached
 ├── enrolled_at       timestamptz default now()
 ├── completed_at      timestamptz NULL
 └── UNIQUE (student_id, course_id)
```
Indexes: `(course_id)`, `(student_id)`.

### exams
```
exams
 ├── id                 uuid PK
 ├── course_id          uuid NOT NULL → courses.id
 ├── created_by         uuid NULL → users.id ON DELETE SET NULL
 ├── title              text NOT NULL
 ├── instructions       text NULL
 ├── duration_minutes   int NOT NULL CHECK (> 0)
 ├── total_marks        numeric(7,2) NOT NULL         -- computed from questions
 ├── pass_marks         numeric(7,2) NOT NULL CHECK (pass_marks <= total_marks)
 ├── negative_marking   numeric(4,2) NOT NULL default 0
 ├── max_attempts       int NOT NULL default 1
 ├── shuffle_questions  boolean default true
 ├── show_review        boolean default true          -- show per-question review
 ├── start_at           timestamptz NOT NULL
 ├── end_at             timestamptz NOT NULL CHECK (end_at > start_at)
 ├── status             exam_status default 'draft'
 ├── created_at / updated_at
```
Indexes: `(course_id, status)`, `(start_at, end_at)`.

### questions
```
questions
 ├── id           uuid PK
 ├── exam_id      uuid NOT NULL → exams.id ON DELETE CASCADE
 ├── text         text NOT NULL
 ├── marks        numeric(5,2) NOT NULL default 1
 ├── position     int NOT NULL
 ├── explanation  text NULL
 └── UNIQUE (exam_id, position)
```

### question_options
```
question_options
 ├── id           uuid PK
 ├── question_id  uuid NOT NULL → questions.id ON DELETE CASCADE
 ├── text         text NOT NULL
 ├── is_correct   boolean NOT NULL default false
 ├── position     int NOT NULL
 └── UNIQUE (question_id, position)
```
Rule: exactly **one** `is_correct = true` per question (MVP) — enforced by partial unique index `ON question_options(question_id) WHERE is_correct`.

### exam_attempts
```
exam_attempts
 ├── id            uuid PK
 ├── exam_id       uuid NOT NULL → exams.id
 ├── student_id    uuid NOT NULL → users.id
 ├── attempt_no    int NOT NULL default 1
 ├── status        attempt_status default 'in_progress'
 ├── started_at    timestamptz NOT NULL default now()
 ├── expires_at    timestamptz NOT NULL      -- min(started_at+duration, exam.end_at)
 ├── submitted_at  timestamptz NULL
 └── UNIQUE (exam_id, student_id, attempt_no)
```
Indexes: `(student_id)`, `(exam_id)`, partial `(student_id) WHERE status='in_progress'`.

### attempt_answers
```
attempt_answers
 ├── id                  uuid PK
 ├── attempt_id          uuid NOT NULL → exam_attempts.id ON DELETE CASCADE
 ├── question_id         uuid NOT NULL → questions.id
 ├── selected_option_id  uuid NULL → question_options.id
 ├── answered_at         timestamptz default now()
 └── UNIQUE (attempt_id, question_id)
```

### results
```
results
 ├── id             uuid PK
 ├── attempt_id     uuid UNIQUE NOT NULL → exam_attempts.id
 ├── exam_id        uuid NOT NULL → exams.id
 ├── student_id     uuid NOT NULL → users.id
 ├── score          numeric(7,2) NOT NULL
 ├── total_marks    numeric(7,2) NOT NULL
 ├── percentage     numeric(5,2) NOT NULL
 ├── grade          text NOT NULL            -- A+, A, B...
 ├── passed         boolean NOT NULL
 ├── time_taken_sec int NOT NULL
 ├── rank_in_exam   int NULL                 -- per-exam rank, informational (NOT the Live Ranking)
 ├── pdf_path       text NULL                -- cached PDF in Storage
 └── created_at     timestamptz default now()
```
Indexes: `(student_id)`, `(exam_id, score DESC, time_taken_sec ASC)`.

### certificates
```
certificates
 ├── id                uuid PK
 ├── certificate_code  text UNIQUE NOT NULL   -- e.g. SBU-CERT-7F3K9Q2M
 ├── student_id        uuid NOT NULL → users.id
 ├── course_id         uuid NOT NULL → courses.id
 ├── final_percentage  numeric(5,2) NOT NULL
 ├── issued_at         timestamptz default now()
 ├── revoked_at        timestamptz NULL
 ├── revoked_by        uuid NULL → users.id
 ├── pdf_path          text NULL
 └── UNIQUE (student_id, course_id)
```

### tasks
```
tasks
 ├── id            uuid PK
 ├── course_id     uuid NOT NULL → courses.id
 ├── created_by    uuid NULL → users.id ON DELETE SET NULL
 ├── type          task_type NOT NULL
 ├── exam_id       uuid NULL UNIQUE → exams.id ON DELETE RESTRICT   -- exam tasks only
 ├── title         text NOT NULL
 ├── description   text NULL
 ├── points        int NOT NULL CHECK (points >= 0)
 ├── verification  task_verification NOT NULL
 ├── due_at        timestamptz NULL                                  -- informational
 ├── resource_type task_resource_type NULL                           -- video or learning source
 ├── resource_url  text NULL
 ├── assignment_scope task_assignment_scope NOT NULL default 'all_students'
 ├── status        task_status NOT NULL default 'active'
 ├── created_at / updated_at
```
Checks: `type='exam' ⇒ exam_id IS NOT NULL AND verification='auto'`; `type='assignment' ⇒ exam_id IS NULL AND verification='teacher_approval'`.
Resource type and URL must either both be set or both be null. `all_students` targets active course enrollments; `selected_students` uses `task_recipients`.
Indexes: `(course_id, status)`, `(created_by)`.
Rules (service layer): exam tasks are created/archived by exam publish/close; new linked learning assignments use `verification='teacher_approval'` and award their configured points only after faculty approval; legacy assignments using `verification='auto'` continue to award points immediately on completion; `points` becomes **immutable** once any completion exists; published exams cannot be hard-deleted.

### task_recipients
```
task_recipients
 ├── task_id     uuid NOT NULL → tasks.id ON DELETE CASCADE
 ├── student_id  uuid NOT NULL → users.id ON DELETE CASCADE
 ├── assigned_at timestamptz NOT NULL default now()
 └── PRIMARY KEY (task_id, student_id)
```
Each recipient must be an active student. A selected student can be assigned even if they are not enrolled in the task's course; selected tasks are visible to those recipients only. `all_students` tasks are visible to active students enrolled in the course.

### task_completions
```
task_completions
 ├── id                uuid PK
 ├── task_id           uuid NOT NULL → tasks.id
 ├── student_id        uuid NOT NULL → users.id
 ├── status            completion_status NOT NULL
 ├── submission_note   text NULL                  -- assignment tasks
 ├── submission_url    text NULL
 ├── points_awarded    int NOT NULL default 0     -- snapshot of task.points when completed
 ├── submitted_at      timestamptz NOT NULL default now()
 ├── completed_at      timestamptz NULL           -- set when status becomes 'completed'
 ├── reviewed_by       uuid NULL → users.id
 ├── reviewed_at       timestamptz NULL
 ├── review_note       text NULL
 ├── revoked_by        uuid NULL → users.id
 ├── revoked_at        timestamptz NULL
 └── UNIQUE (task_id, student_id)                 -- guarantees points are awarded once
```
Indexes: `(student_id, status)`, `(task_id, status)`, partial `(student_id, completed_at) WHERE status='completed'`.
Constraint: `status='completed' ⇒ completed_at IS NOT NULL AND points_awarded >= 0`.
Rows are **never hard-deleted** — revoke instead (keeps the audit trail).

### task_video_progress
```
task_video_progress
 ├── task_id          uuid NOT NULL → tasks.id ON DELETE CASCADE
 ├── student_id       uuid NOT NULL → users.id ON DELETE CASCADE
 ├── progress_percent double precision NOT NULL default 0 CHECK (0..100)
 ├── updated_at       timestamptz NOT NULL default now()
 └── PRIMARY KEY (task_id, student_id)
```
Students can update progress only for assigned video tasks. Progress is monotonic and its increase is rate-limited using the reported video duration and elapsed time; submissions are blocked until recorded progress reaches 80%. The student UI measures played segments through YouTube's embedded player; points still require faculty approval.

### notices
```
notices
 ├── id            uuid PK
 ├── author_id     uuid NULL → users.id ON DELETE SET NULL
 ├── title         text NOT NULL
 ├── body          text NOT NULL
 ├── audience      notice_audience NOT NULL default 'all'
 ├── course_id     uuid NULL → courses.id        -- required when audience='course'
 ├── priority      notice_priority default 'normal'
 ├── is_pinned     boolean default false
 ├── status        notice_status default 'published'
 ├── published_at  timestamptz default now()
 ├── expires_at    timestamptz NULL
 ├── created_at / updated_at
```
Check: `audience='course'` ⇒ `course_id IS NOT NULL`. Indexes: `(status, published_at DESC)`, `(course_id)`.
Rule (service layer): teachers may only use `audience='course'` for their own courses.

### chat_sessions / chat_messages
```
chat_sessions
 ├── id          uuid PK
 ├── user_id     uuid NOT NULL → users.id ON DELETE CASCADE
 ├── title       text NULL
 └── created_at, updated_at

chat_messages
 ├── id          uuid PK
 ├── session_id  uuid NOT NULL → chat_sessions.id ON DELETE CASCADE
 ├── role        chat_role NOT NULL
 ├── content     text NOT NULL
 ├── created_at  timestamptz default now()
```
Index: `(session_id, created_at)`.

### community_conversations / community_messages
```
community_conversations
 ├── id                  uuid PK
 ├── kind                student_room | peer_direct | admin_support | teacher_support
 ├── created_by          uuid NULL → users.id ON DELETE SET NULL
 ├── room_key            varchar(64) NULL UNIQUE       -- singleton student room
 ├── peer_one_id         uuid NULL → users.id          -- ordered direct-chat pair
 ├── peer_two_id         uuid NULL → users.id
 ├── requester_student_id uuid NULL → users.id         -- private support inbox thread
 ├── expires_at          timestamptz NOT NULL
 ├── created_at / updated_at

community_messages
 ├── id              uuid PK
 ├── conversation_id uuid NOT NULL → community_conversations.id ON DELETE CASCADE
 ├── sender_id       uuid NOT NULL → users.id ON DELETE CASCADE
 ├── content         text NOT NULL CHECK (1..4000 characters)
 └── created_at      timestamptz NOT NULL default now()
```
`student_room` is shared by active students; `peer_direct` is private to its ordered student pair; `admin_support` is visible only to its student and active admins; `teacher_support` is visible only to its student and active teachers. Admin and teacher buttons open role-specific inbox threads, not conversations with arbitrary students or the other staff role. `expires_at` is reset to ten hours after every new message. A backend sweeper deletes expired conversations (and cascaded messages) once a minute; chat API calls also remove expired rows, so cleanup resumes on the next request after service downtime. Existing `chat_sessions` and `chat_messages` remain reserved for Aarsh AI and are not affected.
Indexes: `(kind)`, `(expires_at)`, `(requester_student_id)`, `(conversation_id)`, `(sender_id)`, `(created_at)`, `(conversation_id, created_at)`. Database RLS is enabled; application access is additionally checked per conversation.

### planner_entries
```
planner_entries
 ├── id                uuid PK
 ├── owner_id          uuid NOT NULL → users.id ON DELETE CASCADE
 ├── kind              planner_entry_kind NOT NULL
 ├── title             varchar(160) NOT NULL
 ├── content           text NULL
 ├── due_at            timestamptz NULL
 ├── is_completed      boolean NOT NULL default false
 ├── color             varchar(7) NOT NULL default '#fef3c7'
 ├── shape             planner_note_shape NOT NULL default 'rounded'
 ├── emoji             varchar(16) NULL
 ├── audio_path        varchar(512) NULL → private Supabase/local storage object
 ├── audio_mime_type   varchar(100) NULL
 ├── audio_size_bytes  integer NULL (1..26214400 for voice notes)
 └── created_at / updated_at
```
`learning_plan`, `note`, `sticky_note`, `event`, and `voice_note` are personal to the signed-in user, regardless of whether the user is a student, teacher, or admin. The API always scopes reads, updates, deletes, and audio playback to `owner_id`; planner content is never shared between users. Events require a date/time. Sticky-note color, shape, and emoji are stored with the entry. Voice audio itself is stored in private object storage; only its storage path, MIME type, and byte size are stored in PostgreSQL. The API accepts WebM, Ogg, MP4, MP3, WAV, and AAC recordings up to 25 MiB and serves audio only through an authenticated endpoint.
Indexes: `(owner_id)`, `(kind)`, `(owner_id, kind, due_at)`. Database RLS is enabled; all browser access is mediated by FastAPI.

### whiteboard_sessions / whiteboard_strokes / whiteboard_messages
```
whiteboard_sessions
 ├── id          uuid PK
 ├── course_id   uuid NOT NULL → courses.id ON DELETE CASCADE
 ├── created_by  uuid NULL → users.id ON DELETE SET NULL
 ├── is_active   boolean NOT NULL default true
 ├── board_generation integer NOT NULL default 0  -- bumped when strokes are removed
 ├── started_at  timestamptz NOT NULL default now()
 ├── ended_at    timestamptz NULL
 └── created_at / updated_at

whiteboard_strokes
 ├── id          uuid PK
 ├── session_id  uuid NOT NULL → whiteboard_sessions.id ON DELETE CASCADE
 ├── author_id   uuid NOT NULL → users.id ON DELETE CASCADE
 ├── tool        varchar(16) NOT NULL  -- pen | eraser | line | rectangle | ellipse
 ├── color       varchar(7) NOT NULL   -- #RRGGBB
 ├── width       integer NOT NULL CHECK (1..40)
 ├── points      jsonb NOT NULL        -- normalized x/y points (0..1)
 └── created_at  timestamptz NOT NULL default now()

whiteboard_messages
 ├── id          uuid PK
 ├── session_id  uuid NOT NULL → whiteboard_sessions.id ON DELETE CASCADE
 ├── sender_id   uuid NOT NULL → users.id ON DELETE CASCADE
 ├── content     text NOT NULL CHECK (1..1000 characters)
 ├── expires_at  timestamptz NOT NULL  -- created_at + 10 minutes
 └── created_at  timestamptz NOT NULL default now()
```
The assigned course teacher or an administrator can create/end a live session, draw, undo, and clear the board. Active enrollees must explicitly join; after joining, they can view the board read-only and send/read class messages. A student cannot access another course's session. Admins may create and control a board but do not receive the class chat; the assigned teacher and enrolled students can chat. A partial unique index permits only one active session per course. `board_generation` is incremented on undo/clear so clients can request only newly added strokes until a full snapshot is required. Whiteboard strokes remain for the session history; live chat messages are permanently deleted ten minutes after each message is sent. The backend sweeper removes expired messages every 30 seconds, while reads also delete expired rows to cover downtime. Apply migrations `009_whiteboard_creator` after `008_live_whiteboard` and `010_whiteboard_sync_generation` after `009`. For a database initialized from the SQL bootstrap before `board_generation` was added, apply `ALTER TABLE public.whiteboard_sessions ADD COLUMN IF NOT EXISTS board_generation INTEGER NOT NULL DEFAULT 0;`; this is safe when the column already exists. Direct browser access remains blocked by RLS.
Indexes: `(course_id) WHERE is_active`, `(session_id, created_at)` for strokes and messages, `(expires_at)` for chat cleanup, and author/sender ownership indexes.

### audit_logs
```
audit_logs
 ├── id           bigserial PK
 ├── actor_id     uuid NULL → users.id
 ├── action       text NOT NULL         -- e.g. user.role_changed
 ├── entity_type  text NOT NULL
 ├── entity_id    text NULL
 ├── metadata     jsonb default '{}'
 ├── ip_address   inet NULL
 └── created_at   timestamptz default now()
```
Index: `(created_at DESC)`, `(actor_id)`.

Permanent admin course deletion removes the course's related exams, attempts, results, tasks, enrollments, certificates, notices, and whiteboard sessions. Permanent user deletion removes the identity-provider account and database user; student-owned records cascade with that user, while authored exams, tasks, notices, and whiteboard sessions are retained with their creator field set to NULL. A teacher must be reassigned from all courses before their account can be deleted. The last active administrator and the signed-in administrator cannot be deleted.

Apply the new schema with `alembic upgrade head` (revision `011_admin_course_management`) or execute the corresponding update section at the end of `server/supabase_migration.sql` against Supabase PostgreSQL.

## 5. Derived Data (no duplicate storage)
- **Leaderboard (Task Points):** computed from `task_completions` and held in Redis; rebuilt from DB on cold start and reconciled nightly. Exam marks are **not** used.
  ```sql
  -- Overall Top 4
  SELECT tc.student_id,
         SUM(tc.points_awarded) AS points,
         COUNT(*)               AS tasks_completed,
         MAX(tc.completed_at)   AS last_completed_at
  FROM task_completions tc
  JOIN users u ON u.id = tc.student_id AND u.status = 'active'
  WHERE tc.status = 'completed'
  GROUP BY tc.student_id
  HAVING SUM(tc.points_awarded) > 0
  ORDER BY points DESC, last_completed_at ASC
  LIMIT 4;
  -- Course scope: JOIN tasks t ON t.id = tc.task_id WHERE t.course_id = :course_id
  ```
  Redis score = `points + (1 − epoch_seconds(last_completed_at) / 1e10)` (tie-break: earlier wins), set absolutely via `ZADD`.
- **Course progress:** `passed published exams / total published exams` per enrollment (cached in `enrollments.progress_percent` on result creation).
- **Analytics:** aggregate queries over `results`, `exam_attempts`, `exams` (cached in Redis).

## 6. Important Queries
1. Exams available to a student (enrolled, published, within window, attempts left).
2. Active attempt for a student (blocks AI exam-help).
3. Grading: join `attempt_answers` → `question_options.is_correct`.
4. Top 4 leaderboard (above) and "my rank" (`ZREVRANK` in Redis).
5. Course completion check (all published exams passed).
6. Teacher analytics: exams, submissions, avg score, pass rate per teacher.
7. Notice feed filtered by audience/course/expiry.
8. Award points (idempotent): `INSERT INTO task_completions ... ON CONFLICT (task_id, student_id) DO NOTHING` inside the grading/approval transaction.
9. Student points summary: total, tasks completed, history (`task_completions` joined to `tasks`).
10. Teacher approval queue: `status='pending_review'` for tasks in own courses.

## 7. Seed / Dummy Data Requirements
- 3 departments, 1 admin, 3 teachers, 20 students.
- 4 courses (1 per teacher + 1 shared), 2 exams per course with 10 MCQs each.
- Enrollments for all students; ~40 results with varied scores (Result pages).
- ~6 tasks per course (exam tasks + assignment tasks, points 10–100) and ~60 task completions (completed / pending / rejected / one revoked) with varied totals to test the leaderboard, including **ties**.
- 5 notices (mix of admin/teacher, pinned, expired).
- 1 revoked + 2 valid certificates.
Seed script: `scripts/seed.py` (dev/staging only; never run in production).

## 8. Database Security
- Enable **RLS on all tables** with **no policies** for `anon`/`authenticated` roles → direct Supabase client access is denied. Backend uses a dedicated DB role / service connection.
- Service-role key and DB URL only in backend env.
- Storage buckets private; PDFs/photos served via backend or short-lived signed URLs.
- `is_correct` never selected in student-facing queries pre-submission.
- Parameterized queries only (SQLAlchemy). No raw string SQL with user input.
- Daily automated backups (Supabase), PITR if plan allows.
- PII minimal; soft delete (`status='deleted'`) for users; audit log immutable (no update/delete from app).
- `points_awarded` is written only by backend services (snapshot of `tasks.points`); no API accepts points from clients. Revokes are audit-logged.
