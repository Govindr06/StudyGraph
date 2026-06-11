CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    email VARCHAR(320) NOT NULL UNIQUE,
    google_access_token TEXT NOT NULL,
    google_refresh_token TEXT NOT NULL,
    token_expiry TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS study_schedule (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    study_goal TEXT NOT NULL DEFAULT '',
    sequence_no INTEGER NOT NULL,
    title TEXT NOT NULL,
    content TEXT NOT NULL,
    learner_context TEXT NOT NULL DEFAULT '',
    scheduled_date DATE NOT NULL,
    start_datetime TIMESTAMPTZ NOT NULL,
    end_datetime TIMESTAMPTZ NOT NULL,
    timezone VARCHAR(100) NOT NULL DEFAULT 'Asia/Kolkata',
    calendar_event_id TEXT,
    status VARCHAR(20) NOT NULL DEFAULT 'planned',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(user_id, sequence_no)
);

ALTER TABLE study_schedule
    ADD COLUMN IF NOT EXISTS study_goal TEXT NOT NULL DEFAULT '';

ALTER TABLE study_schedule
    ADD COLUMN IF NOT EXISTS learner_context TEXT NOT NULL DEFAULT '';

CREATE INDEX IF NOT EXISTS idx_study_schedule_user_id ON study_schedule(user_id);
CREATE INDEX IF NOT EXISTS idx_study_schedule_event_id ON study_schedule(calendar_event_id);
