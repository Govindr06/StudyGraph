"""Database helper for local PostgreSQL interactions via psycopg2."""

from __future__ import annotations

import os
from contextlib import contextmanager
from datetime import datetime
from typing import Any, Iterable, Optional

import psycopg2
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv


load_dotenv()


def _build_connection_kwargs() -> dict[str, Any]:
    database_url = os.getenv("DATABASE_URL")
    if database_url:
        return {"dsn": database_url}

    return {
        "host": os.getenv("DB_HOST", "localhost"),
        "port": int(os.getenv("DB_PORT", "5432")),
        "dbname": os.getenv("DB_NAME", "studygraph"),
        "user": os.getenv("DB_USER", "postgres"),
        "password": os.getenv("DB_PASSWORD", "postgres"),
    }


@contextmanager
def get_connection():
    """Yields a PostgreSQL connection and commits on success."""
    conn = psycopg2.connect(**_build_connection_kwargs())
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def execute_query(
    query: str,
    params: Optional[Iterable[Any]] = None,
    *,
    fetchone: bool = False,
    fetchall: bool = False,
) -> Any:
    with get_connection() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(query, params)
            if fetchone:
                return cur.fetchone()
            if fetchall:
                return cur.fetchall()
    return None


def execute_many(query: str, rows: list[tuple[Any, ...]]) -> None:
    if not rows:
        return
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.executemany(query, rows)


def upsert_user(
    email: str,
    access_token: str,
    refresh_token: str,
    token_expiry: Optional[datetime] = None,
) -> dict[str, Any]:
    """Creates or updates a user and returns id/email."""
    return execute_query(
        """
        INSERT INTO users (email, google_access_token, google_refresh_token, token_expiry, updated_at)
        VALUES (%s, %s, %s, %s, NOW())
        ON CONFLICT (email)
        DO UPDATE SET
            google_access_token = EXCLUDED.google_access_token,
            google_refresh_token = EXCLUDED.google_refresh_token,
            token_expiry = EXCLUDED.token_expiry,
            updated_at = NOW()
        RETURNING id, email;
        """,
        (email, access_token, refresh_token, token_expiry),
        fetchone=True,
    )


def update_user_tokens(
    user_id: int,
    access_token: str,
    refresh_token: Optional[str],
    token_expiry: Optional[datetime],
) -> None:
    execute_query(
        """
        UPDATE users
        SET google_access_token = %s,
            google_refresh_token = COALESCE(%s, google_refresh_token),
            token_expiry = %s,
            updated_at = NOW()
        WHERE id = %s;
        """,
        (access_token, refresh_token, token_expiry, user_id),
    )


def get_user_by_email(email: str) -> Optional[dict[str, Any]]:
    return execute_query(
        """
        SELECT id, email, google_access_token, google_refresh_token, token_expiry
        FROM users
        WHERE email = %s;
        """,
        (email,),
        fetchone=True,
    )


def clear_schedule_for_user(user_id: int) -> None:
    execute_query("DELETE FROM study_schedule WHERE user_id = %s;", (user_id,))


def insert_study_schedule(user_id: int, schedule_rows: list[dict[str, Any]]) -> None:
    values = [
        (
            user_id,
            row["study_goal"],
            row["sequence_no"],
            row["title"],
            row["content"],
            row.get("learner_context", ""),
            row["scheduled_date"],
            row["start_datetime"],
            row["end_datetime"],
            row["timezone"],
            "planned",
        )
        for row in schedule_rows
    ]

    execute_many(
        """
        INSERT INTO study_schedule (
            user_id,
            study_goal,
            sequence_no,
            title,
            content,
            learner_context,
            scheduled_date,
            start_datetime,
            end_datetime,
            timezone,
            status
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        ON CONFLICT (user_id, sequence_no)
        DO UPDATE SET
            study_goal = EXCLUDED.study_goal,
            title = EXCLUDED.title,
            content = EXCLUDED.content,
            learner_context = EXCLUDED.learner_context,
            scheduled_date = EXCLUDED.scheduled_date,
            start_datetime = EXCLUDED.start_datetime,
            end_datetime = EXCLUDED.end_datetime,
            timezone = EXCLUDED.timezone,
            status = EXCLUDED.status,
            updated_at = NOW();
        """,
        values,
    )


def get_schedule_for_user(user_id: int, *, only_unsynced: bool = False) -> list[dict[str, Any]]:
    query = """
        SELECT id, user_id, study_goal, sequence_no, title, content, learner_context, scheduled_date,
               start_datetime, end_datetime, timezone, calendar_event_id, status
        FROM study_schedule
        WHERE user_id = %s
    """
    if only_unsynced:
        query += " AND calendar_event_id IS NULL"
    query += " ORDER BY sequence_no ASC;"
    return execute_query(query, (user_id,), fetchall=True) or []


def mark_calendar_event_synced(schedule_id: int, event_id: str) -> None:
    execute_query(
        """
        UPDATE study_schedule
        SET calendar_event_id = %s,
            status = 'scheduled',
            updated_at = NOW()
        WHERE id = %s;
        """,
        (event_id, schedule_id),
    )


def get_schedule_item(schedule_id: int, user_id: int) -> Optional[dict[str, Any]]:
    return execute_query(
        """
        SELECT id, user_id, study_goal, sequence_no, title, content, learner_context,
               scheduled_date, start_datetime, end_datetime, timezone, calendar_event_id, status
        FROM study_schedule
        WHERE id = %s AND user_id = %s;
        """,
        (schedule_id, user_id),
        fetchone=True,
    )


def update_schedule_content(schedule_id: int, user_id: int, content: str, learner_context: str) -> None:
    execute_query(
        """
        UPDATE study_schedule
        SET content = %s,
            learner_context = %s,
            updated_at = NOW()
        WHERE id = %s AND user_id = %s;
        """,
        (content, learner_context, schedule_id, user_id),
    )
