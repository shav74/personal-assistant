from types import SimpleNamespace

import pytest

import assistant.integrations.google_calendar as gcal_module
from assistant.config import Settings
from assistant.integrations.google_calendar import (
    GoogleCalendarUnavailable,
    create_event,
    delete_event,
)


def fake_response(ok=True, status_code=200, json_data=None, text=""):
    return SimpleNamespace(
        ok=ok, status_code=status_code, json=lambda: json_data or {}, text=text
    )


def test_create_event_not_configured_raises(monkeypatch, tmp_path):
    monkeypatch.setattr(gcal_module, "settings", Settings(data_dir=tmp_path))
    with pytest.raises(GoogleCalendarUnavailable, match="no OAuth client file"):
        create_event("test", "2026-09-01T09:00:00")


def test_create_event_credentials_present_but_not_authorized_raises(monkeypatch, tmp_path):
    (tmp_path / "google_credentials.json").write_text("{}")
    monkeypatch.setattr(gcal_module, "settings", Settings(data_dir=tmp_path))
    with pytest.raises(GoogleCalendarUnavailable, match="not connected yet"):
        create_event("test", "2026-09-01T09:00:00")


def test_create_event_adds_timezone_for_naive_datetime(monkeypatch, tmp_path):
    monkeypatch.setattr(gcal_module, "settings", Settings(data_dir=tmp_path))
    monkeypatch.setattr(gcal_module, "_get_credentials", lambda: SimpleNamespace(token="tok"))
    captured = {}

    def fake_post(url, headers=None, json=None, timeout=None):
        captured.update(json)
        return fake_response(json_data={"id": "evt-1"})

    monkeypatch.setattr(gcal_module.requests, "post", fake_post)
    event_id = create_event("Collect the guitar", "2026-08-18T16:00:00")

    assert event_id == "evt-1"
    assert captured["start"]["timeZone"] == gcal_module.settings.timezone
    assert captured["end"]["timeZone"] == gcal_module.settings.timezone


def test_create_event_respects_explicit_offset(monkeypatch, tmp_path):
    monkeypatch.setattr(gcal_module, "settings", Settings(data_dir=tmp_path))
    monkeypatch.setattr(gcal_module, "_get_credentials", lambda: SimpleNamespace(token="tok"))
    captured = {}

    def fake_post(url, headers=None, json=None, timeout=None):
        captured.update(json)
        return fake_response(json_data={"id": "evt-2"})

    monkeypatch.setattr(gcal_module.requests, "post", fake_post)
    create_event("Meeting", "2026-08-18T16:00:00+01:00")

    assert "timeZone" not in captured["start"]
    assert "timeZone" not in captured["end"]


def test_create_event_raises_on_api_error(monkeypatch, tmp_path):
    monkeypatch.setattr(gcal_module, "settings", Settings(data_dir=tmp_path))
    monkeypatch.setattr(gcal_module, "_get_credentials", lambda: SimpleNamespace(token="tok"))
    monkeypatch.setattr(
        gcal_module.requests, "post",
        lambda *a, **k: fake_response(ok=False, status_code=400, text="bad request"),
    )
    with pytest.raises(GoogleCalendarUnavailable, match="bad request"):
        create_event("test", "2026-09-01T09:00:00")


def test_delete_event_treats_404_as_success(monkeypatch, tmp_path):
    monkeypatch.setattr(gcal_module, "settings", Settings(data_dir=tmp_path))
    monkeypatch.setattr(gcal_module, "_get_credentials", lambda: SimpleNamespace(token="tok"))
    monkeypatch.setattr(
        gcal_module.requests, "delete",
        lambda *a, **k: fake_response(ok=False, status_code=404),
    )
    delete_event("gone-already")  # should not raise


def test_delete_event_raises_on_other_errors(monkeypatch, tmp_path):
    monkeypatch.setattr(gcal_module, "settings", Settings(data_dir=tmp_path))
    monkeypatch.setattr(gcal_module, "_get_credentials", lambda: SimpleNamespace(token="tok"))
    monkeypatch.setattr(
        gcal_module.requests, "delete",
        lambda *a, **k: fake_response(ok=False, status_code=500, text="server error"),
    )
    with pytest.raises(GoogleCalendarUnavailable, match="server error"):
        delete_event("some-id")
