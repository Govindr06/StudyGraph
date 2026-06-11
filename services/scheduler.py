"""Date assignment service for converting module JSON into dated study sessions."""

from __future__ import annotations

import os
from datetime import date, datetime, time, timedelta
from typing import Any
from zoneinfo import ZoneInfo

from dotenv import load_dotenv


load_dotenv()


WEEKDAY_ALIASES = {
    "mon": 0,
    "monday": 0,
    "tue": 1,
    "tues": 1,
    "tuesday": 1,
    "wed": 2,
    "wednesday": 2,
    "thu": 3,
    "thur": 3,
    "thurs": 3,
    "thursday": 3,
    "fri": 4,
    "friday": 4,
    "sat": 5,
    "saturday": 5,
    "sun": 6,
    "sunday": 6,
}


def _normalize_rest_days(rest_days: list[str | date] | None) -> tuple[set[int], set[date]]:
    """Accept weekday names and YYYY-MM-DD dates as extra non-study days."""
    weekday_blocks: set[int] = set()
    date_blocks: set[date] = set()

    for item in rest_days or []:
        if isinstance(item, date):
            date_blocks.add(item)
            continue

        token = str(item).strip().lower()
        if not token:
            continue

        if token in WEEKDAY_ALIASES:
            weekday_blocks.add(WEEKDAY_ALIASES[token])
            continue

        try:
            date_blocks.add(date.fromisoformat(token))
        except ValueError:
            # Invalid rest-day entries are ignored so one typo does not block schedule generation.
            continue

    return weekday_blocks, date_blocks


def _next_study_day(d: date, *, rest_weekdays: set[int], rest_dates: set[date]) -> date:
    """Move forward until the date is not a weekend or user-requested rest day."""
    while d.weekday() >= 5 or d.weekday() in rest_weekdays or d in rest_dates:
        d += timedelta(days=1)
    return d


def build_schedule(
    modules: list[dict[str, Any]],
    *,
    start_date: date | None = None,
    timezone: str | None = None,
    session_start_hour: int | None = None,
    session_start_time: time | None = None,
    session_duration_minutes: int | None = None,
    rest_days: list[str | date] | None = None,
) -> list[dict[str, Any]]:
    """
    Hand-off in: [{sequence_no, title, content}, ...]
    Hand-off out: [{sequence_no, title, content, scheduled_date, start_datetime, end_datetime, timezone}, ...]
    """
    if not modules:
        return []

    tz_name = timezone or os.getenv("DEFAULT_TIMEZONE", "Asia/Kolkata")
    tz = ZoneInfo(tz_name)
    start_hour = session_start_hour or int(os.getenv("DEFAULT_SESSION_START_HOUR", "19"))
    start_time = session_start_time or time(hour=start_hour, minute=0)
    duration = session_duration_minutes or int(os.getenv("DEFAULT_SESSION_DURATION_MINUTES", "90"))
    rest_weekdays, rest_dates = _normalize_rest_days(rest_days)

    cursor = _next_study_day(
        start_date or datetime.now(tz).date(),
        rest_weekdays=rest_weekdays,
        rest_dates=rest_dates,
    )
    rows: list[dict[str, Any]] = []

    for module in sorted(modules, key=lambda x: int(x.get("sequence_no", 0))):
        cursor = _next_study_day(cursor, rest_weekdays=rest_weekdays, rest_dates=rest_dates)

        start_dt = datetime.combine(cursor, start_time, tzinfo=tz)
        end_dt = start_dt + timedelta(minutes=duration)

        rows.append(
            {
                "study_goal": str(module.get("study_goal", "")),
                "sequence_no": int(module["sequence_no"]),
                "title": str(module["title"]),
                "content": str(module.get("content", "")),
                "learner_context": str(module.get("learner_context", "")),
                "scheduled_date": cursor,
                "start_datetime": start_dt,
                "end_datetime": end_dt,
                "timezone": tz_name,
            }
        )

        cursor += timedelta(days=1)

    return rows
