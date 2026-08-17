"""Google Calendar sync, via OAuth2 + the plain Calendar REST API.

Deliberately not using google-api-python-client — it's a heavy dependency
for two REST calls. Just `google-auth-oauthlib` for the OAuth dance and
token refresh, plus `requests` (already a dependency) for the actual API.

One-time setup (by the user, in a browser on this machine):
  1. https://console.cloud.google.com/ -> new project -> enable the
     "Google Calendar API".
  2. Credentials -> Create Credentials -> OAuth client ID -> Desktop app.
  3. Download the JSON, save it to settings.google_credentials_path
     (default ~/.assistant/google_credentials.json).
  4. Run:  python -m assistant.integrations.google_calendar
     This opens a browser for one-time consent and caches a refresh
     token at settings.google_token_path. Tool calls never trigger this
     flow themselves — no browser popping up mid-conversation, and it
     works from a headless context (e.g. the WebSocket server) as long
     as setup already happened once, interactively, beforehand.
"""

from __future__ import annotations

from datetime import datetime, timedelta

import requests
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow

from ..config import settings

_SCOPES = ["https://www.googleapis.com/auth/calendar.events"]
_API_BASE = "https://www.googleapis.com/calendar/v3"
_DEFAULT_EVENT_MINUTES = 30


class GoogleCalendarUnavailable(Exception):
    """Raised when calendar sync can't proceed — not configured, not
    authorized yet, or the API call itself failed."""


def _get_credentials() -> Credentials:
    if not settings.google_credentials_path.exists():
        raise GoogleCalendarUnavailable(
            f"no OAuth client file at {settings.google_credentials_path} "
            "— see assistant/integrations/google_calendar.py for setup steps"
        )
    token_path = settings.google_token_path
    if not token_path.exists():
        raise GoogleCalendarUnavailable(
            "not connected yet — run `python -m assistant.integrations.google_calendar` once"
        )

    creds = Credentials.from_authorized_user_file(str(token_path), _SCOPES)
    if creds.expired and creds.refresh_token:
        creds.refresh(Request())
        token_path.write_text(creds.to_json())
    return creds


def create_event(summary: str, start_iso: str) -> str:
    """Create a calendar event starting at `start_iso`. Returns the event ID."""
    creds = _get_credentials()
    start = datetime.fromisoformat(start_iso)
    end = start + timedelta(minutes=_DEFAULT_EVENT_MINUTES)
    response = requests.post(
        f"{_API_BASE}/calendars/{settings.google_calendar_id}/events",
        headers={"Authorization": f"Bearer {creds.token}"},
        json={
            "summary": summary,
            "start": {"dateTime": start.isoformat()},
            "end": {"dateTime": end.isoformat()},
        },
        timeout=10,
    )
    if not response.ok:
        raise GoogleCalendarUnavailable(f"Google Calendar API error: {response.text}")
    return response.json()["id"]


def delete_event(event_id: str) -> None:
    creds = _get_credentials()
    response = requests.delete(
        f"{_API_BASE}/calendars/{settings.google_calendar_id}/events/{event_id}",
        headers={"Authorization": f"Bearer {creds.token}"},
        timeout=10,
    )
    if not response.ok and response.status_code != 404:  # already gone is fine
        raise GoogleCalendarUnavailable(f"Google Calendar API error: {response.text}")


def main() -> None:
    """One-time interactive setup: run the OAuth consent flow and cache the token."""
    if not settings.google_credentials_path.exists():
        print(f"Put your OAuth client JSON at {settings.google_credentials_path} first.")
        print("(Google Cloud Console -> Credentials -> OAuth client ID -> Desktop app)")
        return

    flow = InstalledAppFlow.from_client_secrets_file(
        str(settings.google_credentials_path), _SCOPES
    )
    creds = flow.run_local_server(port=0)
    settings.google_token_path.write_text(creds.to_json())
    print(f"Connected. Token saved to {settings.google_token_path}")


if __name__ == "__main__":
    main()
