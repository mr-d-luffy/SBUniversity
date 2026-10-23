-- =============================================================================
-- SiliconBrains University Production Supabase PostgreSQL Schema Migration
-- Source of Truth: Docs/database.md & Docs/architecture.md
-- =============================================================================

-- 1. EXTENSIONS
CREATE EXTENSION IF NOT EXISTS "pgcrypto";
CREATE EXTENSION IF NOT EXISTS "citext";

-- 2. CUSTOM ENUMS
DO $$ BEGIN
    CREATE TYPE user_role AS ENUM ('student', 'teacher', 'admin');
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

DO $$ BEGIN
    CREATE TYPE user_status AS ENUM ('active', 'suspended', 'deleted');
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

DO $$ BEGIN
    CREATE TYPE user_verification_status AS ENUM ('not_verified', 'verified');
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

DO $$ BEGIN
    CREATE TYPE enrollment_status AS ENUM ('active', 'completed', 'dropped');
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

DO $$ BEGIN
    CREATE TYPE exam_status AS ENUM ('draft', 'published', 'closed');
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

DO $$ BEGIN
    CREATE TYPE attempt_status AS ENUM ('in_progress', 'submitted', 'auto_submitted');
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

DO $$ BEGIN
    CREATE TYPE notice_audience AS ENUM ('all', 'students', 'teachers', 'course');
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

DO $$ BEGIN
    CREATE TYPE notice_priority AS ENUM ('normal', 'important', 'urgent');
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

DO $$ BEGIN
    CREATE TYPE notice_status AS ENUM ('draft', 'published', 'archived');
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

DO $$ BEGIN
    CREATE TYPE chat_role AS ENUM ('user', 'model');
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

DO $$ BEGIN
    CREATE TYPE community_conversation_kind AS ENUM (
        'student_room', 'peer_direct', 'admin_support', 'teacher_support'
    );
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

DO $$ BEGIN
    CREATE TYPE planner_entry_kind AS ENUM (
        'learning_plan', 'note', 'sticky_note', 'event', 'voice_note'
    );
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

DO $$ BEGIN
    CREATE TYPE planner_note_shape AS ENUM (
        'rectangle', 'rounded', 'circle', 'cloud', 'star'
    );
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

DO $$ BEGIN
    CREATE TYPE task_type AS ENUM ('exam', 'assignment');
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

DO $$ BEGIN
    CREATE TYPE task_verification AS ENUM ('auto', 'teacher_approval');
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

DO $$ BEGIN
    CREATE TYPE task_status AS ENUM ('active', 'archived');
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

DO $$ BEGIN
    CREATE TYPE task_resource_type AS ENUM ('video', 'learning_source');
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

DO $$ BEGIN
    CREATE TYPE task_assignment_scope AS ENUM ('all_students', 'selected_students');
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

DO $$ BEGIN
    CREATE TYPE completion_status AS ENUM ('pending_review', 'completed', 'rejected', 'revoked');
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

-- 3. UPDATED_AT TRIGGER FUNCTION
CREATE OR REPLACE FUNCTION trigger_set_timestamp()
RETURNS TRIGGER AS $$
BEGIN
  NEW.updated_at = NOW();
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- 4. TABLES

-- 4.1 users
CREATE TABLE IF NOT EXISTS public.users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    clerk_user_id TEXT UNIQUE NOT NULL,
    email CITEXT UNIQUE NOT NULL,
    full_name TEXT NOT NULL,
    avatar_url TEXT NULL,
    role user_role NOT NULL DEFAULT 'student',
    status user_status NOT NULL DEFAULT 'active',
    last_seen_at TIMESTAMPTZ NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_users_role ON public.users(role);
CREATE INDEX IF NOT EXISTS idx_users_status ON public.users(status);
CREATE INDEX IF NOT EXISTS idx_users_lower_full_name ON public.users(LOWER(full_name));

DROP TRIGGER IF EXISTS set_timestamp_users ON public.users;
CREATE TRIGGER set_timestamp_users
BEFORE UPDATE ON public.users
FOR EACH ROW EXECUTE FUNCTION trigger_set_timestamp();

-- 4.2 departments
CREATE TABLE IF NOT EXISTS public.departments (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    code TEXT UNIQUE NOT NULL,
    name TEXT UNIQUE NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 4.3 student_profiles
CREATE TABLE IF NOT EXISTS public.student_profiles (
    user_id UUID PRIMARY KEY REFERENCES public.users(id) ON DELETE CASCADE,
    student_code TEXT UNIQUE NOT NULL,
    department_id UUID NULL REFERENCES public.departments(id) ON DELETE SET NULL,
    batch_year INT NULL,
    academic_term VARCHAR(100) NULL,
    verification_status user_verification_status NOT NULL DEFAULT 'not_verified',
    phone TEXT NULL,
    date_of_birth DATE NULL,
    photo_path TEXT NULL,
    id_valid_until DATE NULL,
    qr_token TEXT UNIQUE NOT NULL DEFAULT encode(gen_random_bytes(16), 'hex'),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

DROP TRIGGER IF EXISTS set_timestamp_student_profiles ON public.student_profiles;
CREATE TRIGGER set_timestamp_student_profiles
BEFORE UPDATE ON public.student_profiles
FOR EACH ROW EXECUTE FUNCTION trigger_set_timestamp();

-- 4.4 teacher_profiles
CREATE TABLE IF NOT EXISTS public.teacher_profiles (
    user_id UUID PRIMARY KEY REFERENCES public.users(id) ON DELETE CASCADE,
    employee_code TEXT UNIQUE NOT NULL,
    department_id UUID NULL REFERENCES public.departments(id) ON DELETE SET NULL,
    verification_status user_verification_status NOT NULL DEFAULT 'not_verified',
    designation TEXT NULL,
    bio TEXT NULL,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

DROP TRIGGER IF EXISTS set_timestamp_teacher_profiles ON public.teacher_profiles;
CREATE TRIGGER set_timestamp_teacher_profiles
BEFORE UPDATE ON public.teacher_profiles
FOR EACH ROW EXECUTE FUNCTION trigger_set_timestamp();

-- 4.5 courses
CREATE TABLE IF NOT EXISTS public.courses (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    code TEXT UNIQUE NOT NULL,
    title TEXT NOT NULL,
    description TEXT NULL,
    department_id UUID NULL REFERENCES public.departments(id) ON DELETE SET NULL,
    teacher_id UUID NOT NULL REFERENCES public.users(id) ON DELETE RESTRICT,
    is_published BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_courses_teacher_id ON public.courses(teacher_id);
CREATE INDEX IF NOT EXISTS idx_courses_department_id ON public.courses(department_id);

DROP TRIGGER IF EXISTS set_timestamp_courses ON public.courses;
CREATE TRIGGER set_timestamp_courses
BEFORE UPDATE ON public.courses
FOR EACH ROW EXECUTE FUNCTION trigger_set_timestamp();

-- 4.6 enrollments
CREATE TABLE IF NOT EXISTS public.enrollments (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    student_id UUID NOT NULL REFERENCES public.users(id) ON DELETE CASCADE,
    course_id UUID NOT NULL REFERENCES public.courses(id) ON DELETE CASCADE,
    status enrollment_status NOT NULL DEFAULT 'active',
    progress_percent NUMERIC(5,2) NOT NULL DEFAULT 0.00 CHECK (progress_percent >= 0 AND progress_percent <= 100),
    enrolled_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    completed_at TIMESTAMPTZ NULL,
    CONSTRAINT uq_enrollment_student_course UNIQUE (student_id, course_id)
);

CREATE INDEX IF NOT EXISTS idx_enrollments_student_id ON public.enrollments(student_id);
CREATE INDEX IF NOT EXISTS idx_enrollments_course_id ON public.enrollments(course_id);

-- 4.7 exams
CREATE TABLE IF NOT EXISTS public.exams (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    course_id UUID NOT NULL REFERENCES public.courses(id) ON DELETE CASCADE,
    created_by UUID NOT NULL REFERENCES public.users(id) ON DELETE RESTRICT,
    title TEXT NOT NULL,
    instructions TEXT NULL,
    duration_minutes INT NOT NULL CHECK (duration_minutes > 0),
    total_marks NUMERIC(7,2) NOT NULL DEFAULT 0.00 CHECK (total_marks >= 0),
    pass_marks NUMERIC(7,2) NOT NULL DEFAULT 0.00 CHECK (pass_marks >= 0 AND pass_marks <= total_marks),
    negative_marking NUMERIC(4,2) NOT NULL DEFAULT 0.00 CHECK (negative_marking >= 0),
    max_attempts INT NOT NULL DEFAULT 1 CHECK (max_attempts > 0),
    shuffle_questions BOOLEAN NOT NULL DEFAULT TRUE,
    show_review BOOLEAN NOT NULL DEFAULT TRUE,
    start_at TIMESTAMPTZ NOT NULL,
    end_at TIMESTAMPTZ NOT NULL,
    status exam_status NOT NULL DEFAULT 'draft',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT ck_exam_window CHECK (end_at > start_at)
);

CREATE INDEX IF NOT EXISTS idx_exams_course_status ON public.exams(course_id, status);
CREATE INDEX IF NOT EXISTS idx_exams_window ON public.exams(start_at, end_at);

DROP TRIGGER IF EXISTS set_timestamp_exams ON public.exams;
CREATE TRIGGER set_timestamp_exams
BEFORE UPDATE ON public.exams
FOR EACH ROW EXECUTE FUNCTION trigger_set_timestamp();

-- 4.8 questions
CREATE TABLE IF NOT EXISTS public.questions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    exam_id UUID NOT NULL REFERENCES public.exams(id) ON DELETE CASCADE,
    text TEXT NOT NULL,
    marks NUMERIC(5,2) NOT NULL DEFAULT 1.00 CHECK (marks > 0),
    position INT NOT NULL,
    explanation TEXT NULL,
    CONSTRAINT uq_question_exam_position UNIQUE (exam_id, position)
);

CREATE INDEX IF NOT EXISTS idx_questions_exam_id ON public.questions(exam_id);

-- 4.9 question_options
CREATE TABLE IF NOT EXISTS public.question_options (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    question_id UUID NOT NULL REFERENCES public.questions(id) ON DELETE CASCADE,
    text TEXT NOT NULL,
    is_correct BOOLEAN NOT NULL DEFAULT FALSE,
    position INT NOT NULL,
    CONSTRAINT uq_option_question_position UNIQUE (question_id, position)
);

CREATE INDEX IF NOT EXISTS idx_question_options_question_id ON public.question_options(question_id);

-- Guarantee exactly one correct option per question
CREATE UNIQUE INDEX IF NOT EXISTS uq_question_single_correct_option 
ON public.question_options(question_id) 
WHERE is_correct = TRUE;

-- 4.10 exam_attempts
CREATE TABLE IF NOT EXISTS public.exam_attempts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    exam_id UUID NOT NULL REFERENCES public.exams(id) ON DELETE RESTRICT,
    student_id UUID NOT NULL REFERENCES public.users(id) ON DELETE CASCADE,
    attempt_no INT NOT NULL DEFAULT 1 CHECK (attempt_no > 0),
    status attempt_status NOT NULL DEFAULT 'in_progress',
    started_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    expires_at TIMESTAMPTZ NOT NULL,
    submitted_at TIMESTAMPTZ NULL,
    CONSTRAINT uq_exam_student_attempt UNIQUE (exam_id, student_id, attempt_no)
);

CREATE INDEX IF NOT EXISTS idx_exam_attempts_student ON public.exam_attempts(student_id);
CREATE INDEX IF NOT EXISTS idx_exam_attempts_exam ON public.exam_attempts(exam_id);
CREATE INDEX IF NOT EXISTS idx_exam_attempts_student_active ON public.exam_attempts(student_id) WHERE status = 'in_progress';

-- 4.11 attempt_answers
CREATE TABLE IF NOT EXISTS public.attempt_answers (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    attempt_id UUID NOT NULL REFERENCES public.exam_attempts(id) ON DELETE CASCADE,
    question_id UUID NOT NULL REFERENCES public.questions(id) ON DELETE CASCADE,
    selected_option_id UUID NULL REFERENCES public.question_options(id) ON DELETE SET NULL,
    answered_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_attempt_question_answer UNIQUE (attempt_id, question_id)
);

CREATE INDEX IF NOT EXISTS idx_attempt_answers_attempt ON public.attempt_answers(attempt_id);

-- 4.12 results
CREATE TABLE IF NOT EXISTS public.results (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    attempt_id UUID UNIQUE NOT NULL REFERENCES public.exam_attempts(id) ON DELETE CASCADE,
    exam_id UUID NOT NULL REFERENCES public.exams(id) ON DELETE CASCADE,
    student_id UUID NOT NULL REFERENCES public.users(id) ON DELETE CASCADE,
    score NUMERIC(7,2) NOT NULL,
    total_marks NUMERIC(7,2) NOT NULL,
    percentage NUMERIC(5,2) NOT NULL,
    grade TEXT NOT NULL,
    passed BOOLEAN NOT NULL,
    time_taken_sec INT NOT NULL,
    rank_in_exam INT NULL,
    pdf_path TEXT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_results_student ON public.results(student_id);
CREATE INDEX IF NOT EXISTS idx_results_exam_score ON public.results(exam_id, score DESC, time_taken_sec ASC);

-- 4.13 certificates
CREATE TABLE IF NOT EXISTS public.certificates (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    certificate_code TEXT UNIQUE NOT NULL,
    student_id UUID NOT NULL REFERENCES public.users(id) ON DELETE CASCADE,
    course_id UUID NOT NULL REFERENCES public.courses(id) ON DELETE CASCADE,
    final_percentage NUMERIC(5,2) NOT NULL,
    issued_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    revoked_at TIMESTAMPTZ NULL,
    revoked_by UUID NULL REFERENCES public.users(id) ON DELETE SET NULL,
    pdf_path TEXT NULL,
    CONSTRAINT uq_certificate_student_course UNIQUE (student_id, course_id)
);

CREATE INDEX IF NOT EXISTS idx_certificates_student ON public.certificates(student_id);
CREATE INDEX IF NOT EXISTS idx_certificates_code ON public.certificates(certificate_code);

-- 4.14 tasks
CREATE TABLE IF NOT EXISTS public.tasks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    course_id UUID NOT NULL REFERENCES public.courses(id) ON DELETE CASCADE,
    created_by UUID NOT NULL REFERENCES public.users(id) ON DELETE RESTRICT,
    type task_type NOT NULL,
    exam_id UUID NULL UNIQUE REFERENCES public.exams(id) ON DELETE RESTRICT,
    title TEXT NOT NULL,
    description TEXT NULL,
    points INT NOT NULL CHECK (points >= 0),
    verification task_verification NOT NULL,
    due_at TIMESTAMPTZ NULL,
    resource_type task_resource_type NULL,
    resource_url TEXT NULL,
    assignment_scope task_assignment_scope NOT NULL DEFAULT 'all_students',
    status task_status NOT NULL DEFAULT 'active',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT ck_task_resource_type_url CHECK (
        (resource_type IS NULL AND resource_url IS NULL) OR
        (resource_type IS NOT NULL AND resource_url IS NOT NULL)
    ),
    CONSTRAINT ck_task_type_exam CHECK (
        (type = 'exam' AND exam_id IS NOT NULL AND verification = 'auto') OR
        (type = 'assignment' AND exam_id IS NULL AND verification = 'teacher_approval')
    )
);

CREATE INDEX IF NOT EXISTS idx_tasks_course_status ON public.tasks(course_id, status);
CREATE INDEX IF NOT EXISTS idx_tasks_created_by ON public.tasks(created_by);

ALTER TABLE public.tasks
    ADD COLUMN IF NOT EXISTS resource_type task_resource_type,
    ADD COLUMN IF NOT EXISTS resource_url TEXT,
    ADD COLUMN IF NOT EXISTS assignment_scope task_assignment_scope NOT NULL DEFAULT 'all_students';

DROP TRIGGER IF EXISTS set_timestamp_tasks ON public.tasks;
CREATE TRIGGER set_timestamp_tasks
BEFORE UPDATE ON public.tasks
FOR EACH ROW EXECUTE FUNCTION trigger_set_timestamp();

ALTER TABLE public.tasks
    DROP CONSTRAINT IF EXISTS ck_task_type_exam,
    DROP CONSTRAINT IF EXISTS ck_task_type_verification;

ALTER TABLE public.tasks
    ADD CONSTRAINT ck_task_type_verification CHECK (
        (type = 'exam' AND exam_id IS NOT NULL AND verification = 'auto') OR
        (type = 'assignment' AND exam_id IS NULL AND verification IN ('auto', 'teacher_approval'))
    );

ALTER TABLE public.tasks
    DROP CONSTRAINT IF EXISTS ck_task_resource_type_url;

ALTER TABLE public.tasks
    ADD CONSTRAINT ck_task_resource_type_url CHECK (
        (resource_type IS NULL AND resource_url IS NULL) OR
        (resource_type IS NOT NULL AND resource_url IS NOT NULL)
    );

-- 4.15 task_recipients
CREATE TABLE IF NOT EXISTS public.task_recipients (
    task_id UUID NOT NULL REFERENCES public.tasks(id) ON DELETE CASCADE,
    student_id UUID NOT NULL REFERENCES public.users(id) ON DELETE CASCADE,
    assigned_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (task_id, student_id)
);

CREATE INDEX IF NOT EXISTS idx_task_recipients_student ON public.task_recipients(student_id);

-- 4.15 task_completions
CREATE TABLE IF NOT EXISTS public.task_completions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    task_id UUID NOT NULL REFERENCES public.tasks(id) ON DELETE RESTRICT,
    student_id UUID NOT NULL REFERENCES public.users(id) ON DELETE CASCADE,
    status completion_status NOT NULL,
    submission_note TEXT NULL,
    submission_url TEXT NULL,
    points_awarded INT NOT NULL DEFAULT 0 CHECK (points_awarded >= 0),
    submitted_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    completed_at TIMESTAMPTZ NULL,
    reviewed_by UUID NULL REFERENCES public.users(id) ON DELETE SET NULL,
    reviewed_at TIMESTAMPTZ NULL,
    review_note TEXT NULL,
    revoked_by UUID NULL REFERENCES public.users(id) ON DELETE SET NULL,
    revoked_at TIMESTAMPTZ NULL,
    CONSTRAINT uq_task_student_completion UNIQUE (task_id, student_id),
    CONSTRAINT ck_task_completion_completed CHECK (
        (status = 'completed' AND completed_at IS NOT NULL) OR
        (status != 'completed')
    )
);

CREATE INDEX IF NOT EXISTS idx_task_completions_student ON public.task_completions(student_id, status);
CREATE INDEX IF NOT EXISTS idx_task_completions_task ON public.task_completions(task_id, status);
CREATE INDEX IF NOT EXISTS idx_task_completions_completed ON public.task_completions(student_id, completed_at) WHERE status = 'completed';

-- 4.16 task_video_progress
CREATE TABLE IF NOT EXISTS public.task_video_progress (
    task_id UUID NOT NULL REFERENCES public.tasks(id) ON DELETE CASCADE,
    student_id UUID NOT NULL REFERENCES public.users(id) ON DELETE CASCADE,
    progress_percent DOUBLE PRECISION NOT NULL DEFAULT 0
        CHECK (progress_percent >= 0 AND progress_percent <= 100),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (task_id, student_id)
);

CREATE INDEX IF NOT EXISTS idx_task_video_progress_student
    ON public.task_video_progress(student_id);

-- 4.16 notices
CREATE TABLE IF NOT EXISTS public.notices (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    author_id UUID NOT NULL REFERENCES public.users(id) ON DELETE RESTRICT,
    title TEXT NOT NULL,
    body TEXT NOT NULL,
    audience notice_audience NOT NULL DEFAULT 'all',
    course_id UUID NULL REFERENCES public.courses(id) ON DELETE CASCADE,
    priority notice_priority NOT NULL DEFAULT 'normal',
    is_pinned BOOLEAN NOT NULL DEFAULT FALSE,
    status notice_status NOT NULL DEFAULT 'published',
    published_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    expires_at TIMESTAMPTZ NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT ck_notice_course_scope CHECK (
        (audience = 'course' AND course_id IS NOT NULL) OR
        (audience != 'course')
    )
);

CREATE INDEX IF NOT EXISTS idx_notices_status_pub ON public.notices(status, published_at DESC);
CREATE INDEX IF NOT EXISTS idx_notices_course ON public.notices(course_id);

DROP TRIGGER IF EXISTS set_timestamp_notices ON public.notices;
CREATE TRIGGER set_timestamp_notices
BEFORE UPDATE ON public.notices
FOR EACH ROW EXECUTE FUNCTION trigger_set_timestamp();

-- 4.17 chat_sessions & chat_messages (Aarsh Intelligence)
CREATE TABLE IF NOT EXISTS public.chat_sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES public.users(id) ON DELETE CASCADE,
    title TEXT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_chat_sessions_user ON public.chat_sessions(user_id);

DROP TRIGGER IF EXISTS set_timestamp_chat_sessions ON public.chat_sessions;
CREATE TRIGGER set_timestamp_chat_sessions
BEFORE UPDATE ON public.chat_sessions
FOR EACH ROW EXECUTE FUNCTION trigger_set_timestamp();

CREATE TABLE IF NOT EXISTS public.chat_messages (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id UUID NOT NULL REFERENCES public.chat_sessions(id) ON DELETE CASCADE,
    role chat_role NOT NULL,
    content TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_chat_messages_session ON public.chat_messages(session_id, created_at ASC);

-- 4.18 community conversations and messages
CREATE TABLE IF NOT EXISTS public.community_conversations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    kind community_conversation_kind NOT NULL,
    created_by UUID NULL REFERENCES public.users(id) ON DELETE SET NULL,
    room_key VARCHAR(64) NULL,
    peer_one_id UUID NULL REFERENCES public.users(id) ON DELETE CASCADE,
    peer_two_id UUID NULL REFERENCES public.users(id) ON DELETE CASCADE,
    requester_student_id UUID NULL REFERENCES public.users(id) ON DELETE CASCADE,
    expires_at TIMESTAMPTZ NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_community_conversation_room_key UNIQUE (room_key),
    CONSTRAINT uq_community_conversation_peer_pair UNIQUE (peer_one_id, peer_two_id),
    CONSTRAINT uq_community_conversation_student_support_kind
        UNIQUE (requester_student_id, kind),
    CONSTRAINT ck_community_conversation_target CHECK (
        (kind = 'student_room' AND room_key IS NOT NULL
            AND peer_one_id IS NULL AND peer_two_id IS NULL
            AND requester_student_id IS NULL) OR
        (kind = 'peer_direct' AND room_key IS NULL
            AND peer_one_id IS NOT NULL AND peer_two_id IS NOT NULL
            AND peer_one_id < peer_two_id AND requester_student_id IS NULL) OR
        (kind IN ('admin_support', 'teacher_support') AND room_key IS NULL
            AND peer_one_id IS NULL AND peer_two_id IS NULL
            AND requester_student_id IS NOT NULL)
    )
);

CREATE INDEX IF NOT EXISTS idx_community_conversations_kind
    ON public.community_conversations(kind);
CREATE INDEX IF NOT EXISTS idx_community_conversations_expires
    ON public.community_conversations(expires_at);
CREATE INDEX IF NOT EXISTS idx_community_conversations_requester
    ON public.community_conversations(requester_student_id);

DROP TRIGGER IF EXISTS set_timestamp_community_conversations
    ON public.community_conversations;
CREATE TRIGGER set_timestamp_community_conversations
BEFORE UPDATE ON public.community_conversations
FOR EACH ROW EXECUTE FUNCTION trigger_set_timestamp();

CREATE TABLE IF NOT EXISTS public.community_messages (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    conversation_id UUID NOT NULL
        REFERENCES public.community_conversations(id) ON DELETE CASCADE,
    sender_id UUID NOT NULL REFERENCES public.users(id) ON DELETE CASCADE,
    content TEXT NOT NULL,
    audio_path VARCHAR(512) NULL,
    audio_mime_type VARCHAR(100) NULL,
    audio_size_bytes INTEGER NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT ck_community_message_content_length
        CHECK (length(content) > 0 AND length(content) <= 4000),
    CONSTRAINT ck_community_message_audio_size CHECK (
        audio_size_bytes IS NULL OR
        (audio_size_bytes > 0 AND audio_size_bytes <= 26214400)
    )
);

CREATE INDEX IF NOT EXISTS idx_community_messages_conversation
    ON public.community_messages(conversation_id);
CREATE INDEX IF NOT EXISTS idx_community_messages_sender
    ON public.community_messages(sender_id);
CREATE INDEX IF NOT EXISTS idx_community_messages_created
    ON public.community_messages(created_at);
CREATE INDEX IF NOT EXISTS idx_community_messages_conversation_created
    ON public.community_messages(conversation_id, created_at);

-- 4.19 personal Learn Planner entries, including private voice-note metadata
CREATE TABLE IF NOT EXISTS public.planner_entries (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    owner_id UUID NOT NULL REFERENCES public.users(id) ON DELETE CASCADE,
    kind planner_entry_kind NOT NULL,
    title VARCHAR(160) NOT NULL,
    content TEXT NULL,
    due_at TIMESTAMPTZ NULL,
    is_completed BOOLEAN NOT NULL DEFAULT FALSE,
    color VARCHAR(7) NOT NULL DEFAULT '#fef3c7',
    shape planner_note_shape NOT NULL DEFAULT 'rounded',
    emoji VARCHAR(16) NULL,
    audio_path VARCHAR(512) NULL,
    audio_mime_type VARCHAR(100) NULL,
    audio_size_bytes INTEGER NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT ck_planner_entry_audio_size CHECK (
        audio_size_bytes IS NULL OR
        (audio_size_bytes > 0 AND audio_size_bytes <= 26214400)
    ),
    CONSTRAINT ck_planner_entry_audio_fields CHECK (
        (kind = 'voice_note' AND audio_path IS NOT NULL
            AND audio_mime_type IS NOT NULL AND audio_size_bytes IS NOT NULL) OR
        (kind != 'voice_note' AND audio_path IS NULL
            AND audio_mime_type IS NULL AND audio_size_bytes IS NULL)
    ),
    CONSTRAINT ck_planner_entry_color CHECK (
        length(color) = 7 AND substr(color, 1, 1) = '#'
    )
);

CREATE INDEX IF NOT EXISTS idx_planner_entries_owner_id
    ON public.planner_entries(owner_id);
CREATE INDEX IF NOT EXISTS idx_planner_entries_kind
    ON public.planner_entries(kind);
CREATE INDEX IF NOT EXISTS idx_planner_entries_owner_kind_due
    ON public.planner_entries(owner_id, kind, due_at);

DROP TRIGGER IF EXISTS set_timestamp_planner_entries ON public.planner_entries;
CREATE TRIGGER set_timestamp_planner_entries
BEFORE UPDATE ON public.planner_entries
FOR EACH ROW EXECUTE FUNCTION trigger_set_timestamp();

-- 4.20 course-scoped live whiteboard sessions and 10-minute class chat
CREATE TABLE IF NOT EXISTS public.whiteboard_sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    course_id UUID NOT NULL REFERENCES public.courses(id) ON DELETE CASCADE,
    created_by UUID NOT NULL REFERENCES public.users(id) ON DELETE RESTRICT,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    board_generation INTEGER NOT NULL DEFAULT 0,
    started_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    ended_at TIMESTAMPTZ NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

ALTER TABLE public.whiteboard_sessions
    ADD COLUMN IF NOT EXISTS board_generation INTEGER NOT NULL DEFAULT 0;

CREATE INDEX IF NOT EXISTS idx_whiteboard_sessions_course_id
    ON public.whiteboard_sessions(course_id);
CREATE INDEX IF NOT EXISTS idx_whiteboard_sessions_created_by
    ON public.whiteboard_sessions(created_by);
CREATE UNIQUE INDEX IF NOT EXISTS uq_whiteboard_sessions_active_course
    ON public.whiteboard_sessions(course_id) WHERE is_active = TRUE;

DROP TRIGGER IF EXISTS set_timestamp_whiteboard_sessions
    ON public.whiteboard_sessions;
CREATE TRIGGER set_timestamp_whiteboard_sessions
BEFORE UPDATE ON public.whiteboard_sessions
FOR EACH ROW EXECUTE FUNCTION trigger_set_timestamp();

CREATE TABLE IF NOT EXISTS public.whiteboard_strokes (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id UUID NOT NULL
        REFERENCES public.whiteboard_sessions(id) ON DELETE CASCADE,
    author_id UUID NOT NULL REFERENCES public.users(id) ON DELETE CASCADE,
    tool VARCHAR(16) NOT NULL,
    color VARCHAR(7) NOT NULL,
    width INTEGER NOT NULL,
    points JSONB NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT ck_whiteboard_stroke_tool
        CHECK (tool IN ('pen', 'eraser', 'line', 'rectangle', 'ellipse')),
    CONSTRAINT ck_whiteboard_stroke_color
        CHECK (color ~ '^#[0-9a-fA-F]{6}$'),
    CONSTRAINT ck_whiteboard_stroke_width
        CHECK (width BETWEEN 1 AND 40)
);

CREATE INDEX IF NOT EXISTS idx_whiteboard_strokes_session
    ON public.whiteboard_strokes(session_id);
CREATE INDEX IF NOT EXISTS idx_whiteboard_strokes_author
    ON public.whiteboard_strokes(author_id);
CREATE INDEX IF NOT EXISTS idx_whiteboard_strokes_created
    ON public.whiteboard_strokes(created_at);
CREATE INDEX IF NOT EXISTS idx_whiteboard_strokes_session_created
    ON public.whiteboard_strokes(session_id, created_at);

CREATE TABLE IF NOT EXISTS public.whiteboard_messages (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id UUID NOT NULL
        REFERENCES public.whiteboard_sessions(id) ON DELETE CASCADE,
    sender_id UUID NOT NULL REFERENCES public.users(id) ON DELETE CASCADE,
    content TEXT NOT NULL,
    expires_at TIMESTAMPTZ NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT ck_whiteboard_message_content_length
        CHECK (length(content) > 0 AND length(content) <= 1000),
    CONSTRAINT ck_whiteboard_message_expiry
        CHECK (expires_at > created_at)
);

CREATE INDEX IF NOT EXISTS idx_whiteboard_messages_session
    ON public.whiteboard_messages(session_id);
CREATE INDEX IF NOT EXISTS idx_whiteboard_messages_sender
    ON public.whiteboard_messages(sender_id);
CREATE INDEX IF NOT EXISTS idx_whiteboard_messages_created
    ON public.whiteboard_messages(created_at);
CREATE INDEX IF NOT EXISTS idx_whiteboard_messages_expires
    ON public.whiteboard_messages(expires_at);
CREATE INDEX IF NOT EXISTS idx_whiteboard_messages_session_created
    ON public.whiteboard_messages(session_id, created_at);

-- 4.21 audit_logs
CREATE TABLE IF NOT EXISTS public.audit_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    actor_id UUID NULL REFERENCES public.users(id) ON DELETE SET NULL,
    action TEXT NOT NULL,
    entity_type TEXT NOT NULL,
    entity_id TEXT NULL,
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    ip_address INET NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_audit_logs_created_at ON public.audit_logs(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_audit_logs_actor ON public.audit_logs(actor_id);

-- 4.22 user_activity_days: accumulated foreground time and badge state per account/day
CREATE TABLE IF NOT EXISTS public.user_activity_days (
    user_id UUID NOT NULL REFERENCES public.users(id) ON DELETE CASCADE,
    activity_date DATE NOT NULL,
    active_seconds INTEGER NOT NULL DEFAULT 0 CHECK (active_seconds >= 0),
    streak_badge_collected BOOLEAN NOT NULL DEFAULT FALSE,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (user_id, activity_date)
);

CREATE INDEX IF NOT EXISTS ix_user_activity_days_date
    ON public.user_activity_days(activity_date);

-- 5. DEFENSE-IN-DEPTH ROW LEVEL SECURITY (RLS)
-- As designed in Docs/architecture.md & Docs/database.md:
-- The browser NEVER talks to Supabase directly. All access goes through the FastAPI backend
-- using the service role connection. RLS is enabled on all tables with no policies for
-- anon or authenticated client roles, preventing direct data leakage via Supabase client SDKs.

ALTER TABLE public.users ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.departments ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.student_profiles ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.teacher_profiles ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.courses ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.enrollments ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.exams ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.questions ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.question_options ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.exam_attempts ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.attempt_answers ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.results ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.certificates ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.tasks ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.task_recipients ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.task_completions ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.task_video_progress ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.notices ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.chat_sessions ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.chat_messages ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.community_conversations ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.community_messages ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.planner_entries ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.whiteboard_sessions ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.whiteboard_strokes ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.whiteboard_messages ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.audit_logs ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.user_activity_days ENABLE ROW LEVEL SECURITY;

-- 8. COMMUNITY CHAT VOICE MESSAGE STORAGE
ALTER TABLE public.community_messages
    ADD COLUMN IF NOT EXISTS audio_path VARCHAR(512) NULL,
    ADD COLUMN IF NOT EXISTS audio_mime_type VARCHAR(100) NULL,
    ADD COLUMN IF NOT EXISTS audio_size_bytes INTEGER NULL;
DO $$
BEGIN
    ALTER TABLE public.community_messages
        ADD CONSTRAINT ck_community_message_audio_size CHECK (
            audio_size_bytes IS NULL OR
            (audio_size_bytes > 0 AND audio_size_bytes <= 26214400)
        );
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;

-- 6. STORAGE BUCKET INITIALIZATION (Supabase Storage)
INSERT INTO storage.buckets (id, name, public)
VALUES ('sbu-storage', 'sbu-storage', false)
ON CONFLICT (id) DO NOTHING;

-- 9. IDEMPOTENT ACADEMIC PROFILE UPDATES FOR EXISTING DATABASES
DO $$ BEGIN
    CREATE TYPE user_verification_status AS ENUM ('not_verified', 'verified');
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

ALTER TABLE public.student_profiles
    ADD COLUMN IF NOT EXISTS academic_term VARCHAR(100) NULL,
    ADD COLUMN IF NOT EXISTS verification_status user_verification_status
        NOT NULL DEFAULT 'not_verified';

ALTER TABLE public.teacher_profiles
    ADD COLUMN IF NOT EXISTS verification_status user_verification_status
        NOT NULL DEFAULT 'not_verified';

INSERT INTO public.teacher_profiles (user_id, employee_code, department_id)
SELECT users.id,
       'T-' || upper(substr(replace(users.id::text, '-', ''), 1, 12)),
       student_profiles.department_id
FROM public.users
LEFT JOIN public.student_profiles ON student_profiles.user_id = users.id
WHERE users.role = 'teacher'
  AND NOT EXISTS (
      SELECT 1
      FROM public.teacher_profiles
      WHERE teacher_profiles.user_id = users.id
  )
ON CONFLICT (user_id) DO NOTHING;

-- 7. ADMIN COURSE MANAGEMENT AND ACCOUNT DELETION
CREATE TABLE IF NOT EXISTS public.course_teachers (
    course_id UUID NOT NULL REFERENCES public.courses(id) ON DELETE CASCADE,
    teacher_id UUID NOT NULL REFERENCES public.users(id) ON DELETE CASCADE,
    PRIMARY KEY (course_id, teacher_id)
);
CREATE INDEX IF NOT EXISTS idx_course_teachers_teacher_id
    ON public.course_teachers(teacher_id);

INSERT INTO public.course_teachers (course_id, teacher_id)
SELECT c.id, c.teacher_id
FROM public.courses AS c
JOIN public.users AS u ON u.id = c.teacher_id
WHERE u.role = 'teacher'
ON CONFLICT (course_id, teacher_id) DO NOTHING;

ALTER TABLE public.exams
    ALTER COLUMN created_by DROP NOT NULL,
    DROP CONSTRAINT IF EXISTS exams_created_by_fkey,
    ADD CONSTRAINT exams_created_by_fkey
        FOREIGN KEY (created_by) REFERENCES public.users(id) ON DELETE SET NULL;
ALTER TABLE public.tasks
    ALTER COLUMN created_by DROP NOT NULL,
    DROP CONSTRAINT IF EXISTS tasks_created_by_fkey,
    ADD CONSTRAINT tasks_created_by_fkey
        FOREIGN KEY (created_by) REFERENCES public.users(id) ON DELETE SET NULL;
ALTER TABLE public.notices
    ALTER COLUMN author_id DROP NOT NULL,
    DROP CONSTRAINT IF EXISTS notices_author_id_fkey,
    ADD CONSTRAINT notices_author_id_fkey
        FOREIGN KEY (author_id) REFERENCES public.users(id) ON DELETE SET NULL;
ALTER TABLE public.whiteboard_sessions
    ALTER COLUMN created_by DROP NOT NULL,
    DROP CONSTRAINT IF EXISTS whiteboard_sessions_teacher_id_fkey,
    DROP CONSTRAINT IF EXISTS whiteboard_sessions_created_by_fkey,
    ADD CONSTRAINT whiteboard_sessions_created_by_fkey
        FOREIGN KEY (created_by) REFERENCES public.users(id) ON DELETE SET NULL;

ALTER TABLE public.course_teachers ENABLE ROW LEVEL SECURITY;
