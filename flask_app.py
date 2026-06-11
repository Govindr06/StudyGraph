"""Alternative Flask UI for StudyGraph that leaves the Streamlit app untouched."""

from __future__ import annotations

import os
from datetime import datetime, time
from typing import Any

from dotenv import load_dotenv
from flask import Flask, jsonify, redirect, render_template, request, session, url_for
from google_auth_oauthlib.flow import Flow

from agent.graph import generate_module_content, run_study_graph
from database.db_helper import (
    clear_schedule_for_user,
    get_schedule_item,
    get_schedule_for_user,
    insert_study_schedule,
    update_schedule_content,
    upsert_user,
)
from services.calendar_service import push_schedule_to_calendar
from services.scheduler import build_schedule


load_dotenv()

# Local OAuth callbacks on localhost use HTTP during development.
os.environ.setdefault("OAUTHLIB_INSECURE_TRANSPORT", "1")

app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET_KEY", "studygraph-dev-secret")
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"


def _parse_scopes() -> list[str]:
    scopes = os.getenv("GOOGLE_CALENDAR_SCOPES", "https://www.googleapis.com/auth/calendar")
    return [scope.strip() for scope in scopes.split(",") if scope.strip()]


def _build_oauth_flow(state: str | None = None) -> Flow:
    client_id = os.getenv("GOOGLE_CLIENT_ID")
    client_secret = os.getenv("GOOGLE_CLIENT_SECRET")
    redirect_uri = os.getenv(
        "FLASK_GOOGLE_REDIRECT_URI",
        os.getenv("GOOGLE_REDIRECT_URI", "http://localhost:5000/auth/callback"),
    )

    if not client_id or not client_secret:
        raise RuntimeError("GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET are required in .env")

    flow = Flow.from_client_config(
        {
            "web": {
                "client_id": client_id,
                "client_secret": client_secret,
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": os.getenv("GOOGLE_TOKEN_URI", "https://oauth2.googleapis.com/token"),
            }
        },
        scopes=_parse_scopes(),
        state=state,
    )
    flow.redirect_uri = redirect_uri
    return flow


def _infer_start_date(goal: str):
    return datetime.now().date()


def _split_rest_days(value: str) -> list[str]:
    return [item.strip() for item in value.replace("\n", ",").split(",") if item.strip()]


def _parse_study_time(value: str) -> time:
    normalized = value.strip().upper().replace(".", "")
    if not normalized:
        return time(hour=19, minute=0)

    formats = ("%H:%M", "%H", "%I:%M %p", "%I %p")
    for fmt in formats:
        try:
            return datetime.strptime(normalized, fmt).time()
        except ValueError:
            continue
    raise ValueError("Usual study time must look like 19:30, 7:30 PM, or 7 PM.")


def _build_planner_brief(payload: dict[str, Any]) -> tuple[str, int, list[str], time]:
    topic = str(payload.get("topic", "")).strip()
    duration_raw = str(payload.get("duration_days", "")).strip()
    focus_topic = str(payload.get("focus_topic", "")).strip()
    rest_days_raw = str(payload.get("rest_days", "")).strip()
    study_time_raw = str(payload.get("study_time", "")).strip()

    # Backward compatibility for any old client still sending one goal string.
    legacy_goal = str(payload.get("goal", "")).strip()
    if legacy_goal and not topic:
        topic = legacy_goal

    if not topic:
        raise ValueError("Topic name is required.")

    try:
        duration_days = int(duration_raw or "10")
    except ValueError as exc:
        raise ValueError("Learning duration must be a number of days.") from exc

    duration_days = max(1, min(duration_days, 30))
    rest_days = _split_rest_days(rest_days_raw)
    study_time = _parse_study_time(study_time_raw)
    focus_line = focus_topic or "No special focus area. Build a balanced beginner-to-practical path."
    rest_line = ", ".join(rest_days) if rest_days else "Only skip Saturdays and Sundays."

    goal = (
        f"Teach me {topic} in {duration_days} study modules.\n"
        f"Topic: {topic}\n"
        f"Duration: {duration_days} study days/modules.\n"
        f"Special focus area: {focus_line}\n"
        f"Extra rest days besides weekends: {rest_line}.\n"
        f"Usual study availability time: {study_time.strftime('%H:%M')}."
    )
    return goal, duration_days, rest_days, study_time


def _serialize_schedule(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    serialized: list[dict[str, Any]] = []
    for row in rows:
        serialized.append(
            {
                "id": row["id"],
                "study_goal": row.get("study_goal", ""),
                "sequence_no": row["sequence_no"],
                "title": row["title"],
                "content": row["content"],
                "learner_context": row.get("learner_context", ""),
                "scheduled_date": row["scheduled_date"].isoformat(),
                "start_datetime": row["start_datetime"].isoformat(),
                "end_datetime": row["end_datetime"].isoformat(),
                "timezone": row["timezone"],
                "calendar_event_id": row["calendar_event_id"],
                "status": row.get("status", "planned"),
            }
        )
    return serialized


def _session_tokens_ready() -> bool:
    tokens = session.get("tokens")
    return bool(tokens and tokens.get("access_token") and tokens.get("refresh_token"))


@app.errorhandler(Exception)
def handle_api_exception(exc: Exception):
    if request.path.startswith("/api/"):
        return jsonify({"error": str(exc)}), 500
    raise exc


@app.get("/")
def index():
    return render_template("index.html")


@app.get("/planner-tools")
def planner_tools():
    return render_template("planner_tools.html")


@app.get("/auth/google")
def google_login():
    flow = _build_oauth_flow()
    auth_url, state = flow.authorization_url(
        access_type="offline",
        include_granted_scopes="true",
        prompt="consent",
    )
    session["oauth_state"] = state
    return redirect(auth_url)


@app.get("/auth/callback")
def google_callback():
    flow = _build_oauth_flow(state=session.get("oauth_state"))
    flow.fetch_token(authorization_response=request.url)
    creds = flow.credentials

    session["tokens"] = {
        "access_token": creds.token,
        "refresh_token": creds.refresh_token,
        "expiry": creds.expiry.isoformat() if creds.expiry else None,
        "email": session.get("tokens", {}).get("email"),
    }
    return redirect(url_for("index", auth="success"))


@app.get("/api/session")
def session_status():
    tokens = session.get("tokens") or {}
    return jsonify(
        {
            "connected": _session_tokens_ready(),
            "email": tokens.get("email"),
            "has_email": bool(tokens.get("email")),
        }
    )


@app.post("/api/session/email")
def save_email():
    payload = request.get_json(silent=True) or {}
    email = str(payload.get("email", "")).strip().lower()

    if not _session_tokens_ready():
        return jsonify({"error": "Complete Google OAuth first."}), 400
    if not email:
        return jsonify({"error": "Email is required."}), 400

    tokens = session["tokens"]
    tokens["email"] = email
    session["tokens"] = tokens
    return jsonify({"message": "Email saved.", "email": email})


@app.post("/api/generate-plan")
def generate_plan():
    payload = request.get_json(silent=True) or {}

    if not _session_tokens_ready():
        return jsonify({"error": "Complete Google OAuth first."}), 400

    email = session["tokens"].get("email")
    if not email:
        return jsonify({"error": "Save your email first."}), 400

    try:
        goal, duration_days, rest_days, study_time = _build_planner_brief(payload)
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400

    modules = run_study_graph(goal, module_count=duration_days)
    modules = [
        {
            **module,
            "study_goal": goal,
            "content": "",
            "learner_context": "",
        }
        for module in modules
    ]
    user = upsert_user(
        email=email,
        access_token=session["tokens"]["access_token"],
        refresh_token=session["tokens"]["refresh_token"],
        token_expiry=datetime.fromisoformat(session["tokens"]["expiry"])
        if session["tokens"].get("expiry")
        else None,
    )

    scheduled_rows = build_schedule(
        modules,
        start_date=_infer_start_date(goal),
        rest_days=rest_days,
        session_start_time=study_time,
    )
    clear_schedule_for_user(user["id"])
    insert_study_schedule(user["id"], scheduled_rows)

    saved_rows = get_schedule_for_user(user["id"], only_unsynced=False)
    return jsonify(
        {
            "message": (
                f"Saved {len(saved_rows)} schedule rows for {user['email']}. "
                "Only the syllabus was generated. Lesson content will be created on demand."
            ),
            "schedule": _serialize_schedule(saved_rows),
        }
    )


@app.post("/api/push-calendar")
def push_calendar():
    if not _session_tokens_ready():
        return jsonify({"error": "Complete Google OAuth first."}), 400

    email = session["tokens"].get("email")
    if not email:
        return jsonify({"error": "Save your email first."}), 400

    created = push_schedule_to_calendar(email)
    user = upsert_user(
        email=email,
        access_token=session["tokens"]["access_token"],
        refresh_token=session["tokens"]["refresh_token"],
        token_expiry=datetime.fromisoformat(session["tokens"]["expiry"])
        if session["tokens"].get("expiry")
        else None,
    )
    rows = get_schedule_for_user(user["id"], only_unsynced=False)
    return jsonify(
        {
            "message": f"Created {created} new Google Calendar event(s).",
            "schedule": _serialize_schedule(rows),
        }
    )


@app.get("/api/schedule")
def get_schedule():
    if not _session_tokens_ready():
        return jsonify({"error": "Complete Google OAuth first."}), 400

    email = session["tokens"].get("email")
    if not email:
        return jsonify({"error": "Save your email first."}), 400

    user = upsert_user(
        email=email,
        access_token=session["tokens"]["access_token"],
        refresh_token=session["tokens"]["refresh_token"],
        token_expiry=datetime.fromisoformat(session["tokens"]["expiry"])
        if session["tokens"].get("expiry")
        else None,
    )
    rows = get_schedule_for_user(user["id"], only_unsynced=False)
    return jsonify({"schedule": _serialize_schedule(rows)})


@app.post("/api/generate-content")
def generate_content():
    if not _session_tokens_ready():
        return jsonify({"error": "Complete Google OAuth first."}), 400

    email = session["tokens"].get("email")
    if not email:
        return jsonify({"error": "Save your email first."}), 400

    payload = request.get_json(silent=True) or {}
    schedule_id = payload.get("schedule_id")
    progress_prompt = str(payload.get("progress_prompt", "")).strip()
    content_style = str(payload.get("content_style", "Detailed and practical")).strip()

    if not schedule_id:
        return jsonify({"error": "A schedule item is required."}), 400

    user = upsert_user(
        email=email,
        access_token=session["tokens"]["access_token"],
        refresh_token=session["tokens"]["refresh_token"],
        token_expiry=datetime.fromisoformat(session["tokens"]["expiry"])
        if session["tokens"].get("expiry")
        else None,
    )

    schedule_item = get_schedule_item(int(schedule_id), user["id"])
    if not schedule_item:
        return jsonify({"error": "Scheduled module not found."}), 404

    previous_modules = [
        {"title": row["title"], "sequence_no": row["sequence_no"]}
        for row in get_schedule_for_user(user["id"], only_unsynced=False)
        if int(row["sequence_no"]) < int(schedule_item["sequence_no"])
    ]

    content = generate_module_content(
        goal=schedule_item["study_goal"],
        sequence_no=int(schedule_item["sequence_no"]),
        title=schedule_item["title"],
        progress_context=(
            f"{progress_prompt}\n\nPreferred lesson style for this generated lesson: "
            f"{content_style or 'Detailed and practical'}"
        ).strip(),
        previous_modules=previous_modules,
    )
    update_schedule_content(int(schedule_id), user["id"], content, progress_prompt)

    rows = get_schedule_for_user(user["id"], only_unsynced=False)
    updated_item = next((row for row in rows if int(row["id"]) == int(schedule_id)), None)
    return jsonify(
        {
            "message": f"Generated lesson content for Day {schedule_item['sequence_no']}.",
            "item": _serialize_schedule([updated_item])[0] if updated_item else None,
            "schedule": _serialize_schedule(rows),
        }
    )


if __name__ == "__main__":
    app.run(debug=True, port=5000)
