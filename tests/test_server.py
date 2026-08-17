import assistant.agent as agent_module
from fastapi.testclient import TestClient

from assistant.interfaces.server import app

from .fakes import FakeClient, make_response, text_block, tool_use_block


def fake_agent_backend(monkeypatch, responses):
    fake_client = FakeClient(responses)
    monkeypatch.setattr(agent_module, "Anthropic", lambda api_key: fake_client)
    return fake_client


def test_health_endpoint():
    resp = TestClient(app).get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


def test_ws_chat_simple_reply(monkeypatch):
    fake_agent_backend(monkeypatch, [make_response([text_block("hi there")], "end_turn")])

    with TestClient(app).websocket_connect("/ws/chat") as ws:
        ws.send_json({"type": "user_message", "text": "hello"})
        reply = ws.receive_json()

    assert reply == {"type": "assistant_message", "text": "hi there"}


def test_ws_chat_confirm_flow_allow(monkeypatch):
    responses = [
        make_response([tool_use_block("id1", "run_shell", {"command": "rm -rf /"})], "tool_use"),
        make_response([text_block("done")], "end_turn"),
    ]
    fake_agent_backend(monkeypatch, responses)

    with TestClient(app).websocket_connect("/ws/chat") as ws:
        ws.send_json({"type": "user_message", "text": "delete stuff"})
        confirm_req = ws.receive_json()
        assert confirm_req["type"] == "confirm_request"
        assert "run_shell" in confirm_req["description"]

        ws.send_json({"type": "confirm_response", "allow": True})
        reply = ws.receive_json()

    assert reply == {"type": "assistant_message", "text": "done"}


def test_ws_chat_confirm_flow_deny(monkeypatch):
    responses = [
        make_response([tool_use_block("id1", "run_shell", {"command": "rm -rf /"})], "tool_use"),
        make_response([text_block("skipped")], "end_turn"),
    ]
    fake_agent_backend(monkeypatch, responses)

    with TestClient(app).websocket_connect("/ws/chat") as ws:
        ws.send_json({"type": "user_message", "text": "delete stuff"})
        ws.receive_json()  # confirm_request

        ws.send_json({"type": "confirm_response", "allow": False})
        reply = ws.receive_json()

    assert reply == {"type": "assistant_message", "text": "skipped"}


def test_ws_chat_unknown_message_type_reports_error(monkeypatch):
    fake_agent_backend(monkeypatch, [])

    with TestClient(app).websocket_connect("/ws/chat") as ws:
        ws.send_json({"type": "bogus"})
        reply = ws.receive_json()

    assert reply["type"] == "error"
