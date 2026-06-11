"""Google Calendar sync service reading user tokens and schedule rows from PostgreSQL."""

from __future__ import annotations

import os
from datetime import datetime
from typing import Any

from dotenv import load_dotenv
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

from database.db_helper import (
    get_schedule_for_user,
    get_user_by_email,
    mark_calendar_event_synced,
    update_user_tokens,
)


load_dotenv()


def _build_credentials_from_db(user_row: dict[str, Any]) -> Credentials:
    scopes = [
        s.strip()
        for s in os.getenv("GOOGLE_CALENDAR_SCOPES", "https://www.googleapis.com/auth/calendar").split(",")
        if s.strip()
    ]

    creds = Credentials(
        token=user_row["google_access_token"],
        refresh_token=user_row["google_refresh_token"],
        token_uri=os.getenv("GOOGLE_TOKEN_URI", "https://oauth2.googleapis.com/token"),
        client_id=os.getenv("GOOGLE_CLIENT_ID"),
        client_secret=os.getenv("GOOGLE_CLIENT_SECRET"),
        scopes=scopes,
    )

    if creds.expired and creds.refresh_token:
        creds.refresh(Request())

    return creds


def _format_calendar_datetime(value: datetime) -> str:
    # Required format: YYYY-MM-DDTHH:MM:SS
    return value.strftime("%Y-%m-%dT%H:%M:%S")


def push_schedule_to_calendar(email: str) -> int:
    """
    Pulls tokens + unsynced schedule rows from PostgreSQL and inserts Google Calendar events.
    Returns the number of successfully created events.
    """
    user = get_user_by_email(email)
    if not user:
        raise ValueError(f"No user found for email: {email}")

    creds = _build_credentials_from_db(user)
    if creds.token:
        update_user_tokens(user["id"], creds.token, creds.refresh_token, creds.expiry)

    service = build("calendar", "v3", credentials=creds)
    rows = get_schedule_for_user(user["id"], only_unsynced=True)

    created = 0
    for row in rows:
        start_dt = row["start_datetime"]
        end_dt = row["end_datetime"]

        event_body = {
            "summary": f"StudyGraph Day {row['sequence_no']}: {row['title']}",
            "description": (
                row["content"][:6000]
                if row["content"]
                else "Open StudyGraph to generate the lesson content for this session."
            ),
            "start": {
                "dateTime": _format_calendar_datetime(start_dt),
                "timeZone": "Asia/Kolkata",
            },
            "end": {
                "dateTime": _format_calendar_datetime(end_dt),
                "timeZone": "Asia/Kolkata",
            },
        }

        event = service.events().insert(calendarId="primary", body=event_body).execute()
        mark_calendar_event_synced(int(row["id"]), str(event["id"]))
        created += 1

    return created


if __name__ == "__main__":
    target_email = os.getenv("STUDYGRAPH_EMAIL")
    if not target_email:
        raise SystemExit("Set STUDYGRAPH_EMAIL in environment to push calendar events.")
    count = push_schedule_to_calendar(target_email)
    print(f"Created {count} Google Calendar events for {target_email}")
