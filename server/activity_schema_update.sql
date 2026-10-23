-- Apply this once to an existing Supabase database initialized from the SQL bootstrap.
-- Alembic-managed databases should use: alembic upgrade head
BEGIN;

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

ALTER TABLE public.user_activity_days ENABLE ROW LEVEL SECURITY;

COMMIT;
