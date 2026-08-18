import json

import pytest

import voice_frontend.backend_client as backend_client_module
from voice_frontend.backend_client import BackendClient, BackendError

from .fakes import FakeWS


def make_client(monkeypatch, script):
    fake_ws = FakeWS(script=[json.dumps(m) for m in script])
    monkeypatch.setattr(backend_client_module, "connect", lambda url: fake_ws)
    client = BackendClient("ws://fake/ws/chat")
    client.connect()
    return client, fake_ws


def test_send_command_returns_assistant_reply(monkeypatch):
    client, fake_ws = make_client(
        monkeypatch, [{"type": "assistant_message", "text": "hello there"}]
    )
    reply = client.send_command("hi", on_confirm=lambda desc: True)
    assert reply == "hello there"
    assert json.loads(fake_ws.sent[0]) == {"type": "user_message", "text": "hi"}


def test_send_command_handles_confirm_request_round_trip(monkeypatch):
    client, fake_ws = make_client(
        monkeypatch,
        [
            {"type": "confirm_request", "description": "run rm -rf /"},
            {"type": "assistant_message", "text": "done"},
        ],
    )
    seen_descriptions = []

    def on_confirm(description):
        seen_descriptions.append(description)
        return True

    reply = client.send_command("delete stuff", on_confirm=on_confirm)

    assert reply == "done"
    assert seen_descriptions == ["run rm -rf /"]
    assert json.loads(fake_ws.sent[1]) == {"type": "confirm_response", "allow": True}


def test_send_command_handles_multiple_confirm_requests_in_one_turn(monkeypatch):
    client, fake_ws = make_client(
        monkeypatch,
        [
            {"type": "confirm_request", "description": "first"},
            {"type": "confirm_request", "description": "second"},
            {"type": "assistant_message", "text": "all done"},
        ],
    )
    calls = []
    reply = client.send_command("do two things", on_confirm=lambda d: calls.append(d) or True)

    assert reply == "all done"
    assert calls == ["first", "second"]


def test_send_command_raises_backend_error_on_error_message(monkeypatch):
    client, _fake_ws = make_client(monkeypatch, [{"type": "error", "detail": "bad request"}])
    with pytest.raises(BackendError, match="bad request"):
        client.send_command("hi", on_confirm=lambda d: True)


def test_close_closes_the_socket(monkeypatch):
    client, fake_ws = make_client(monkeypatch, [])
    client.close()
    assert fake_ws.closed is True
