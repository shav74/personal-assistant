from types import SimpleNamespace

import assistant.agent as agent_module
from assistant.agent import Agent


def text_block(text):
    return SimpleNamespace(type="text", text=text)


def tool_use_block(id_, name, input_):
    return SimpleNamespace(type="tool_use", id=id_, name=name, input=input_)


def make_response(content, stop_reason):
    return SimpleNamespace(content=content, stop_reason=stop_reason)


class FakeMessages:
    def __init__(self, responses):
        self._responses = list(responses)
        self.calls = []

    def create(self, **kwargs):
        self.calls.append(kwargs)
        return self._responses.pop(0)


class FakeClient:
    def __init__(self, responses):
        self.messages = FakeMessages(responses)


def make_agent(monkeypatch, responses, confirm=lambda desc: True):
    fake_client = FakeClient(responses)
    monkeypatch.setattr(agent_module, "Anthropic", lambda api_key: fake_client)
    return Agent(confirm=confirm), fake_client


def test_chat_returns_text_when_model_is_done(monkeypatch):
    responses = [make_response([text_block("hello there")], "end_turn")]
    agent, client = make_agent(monkeypatch, responses)

    assert agent.chat("hi") == "hello there"
    assert len(client.messages.calls) == 1


def test_chat_runs_safe_tool_then_returns_final_text(monkeypatch):
    responses = [
        make_response([tool_use_block("id1", "get_time", {})], "tool_use"),
        make_response([text_block("done")], "end_turn"),
    ]
    agent, client = make_agent(monkeypatch, responses)

    assert agent.chat("what time is it") == "done"
    assert len(client.messages.calls) == 2
    tool_result_msg = agent.messages[-2]
    assert tool_result_msg["role"] == "user"
    assert tool_result_msg["content"][0]["tool_use_id"] == "id1"


def test_chat_reports_denial_back_to_model_without_running_tool(monkeypatch):
    responses = [
        make_response([tool_use_block("id1", "run_shell", {"command": "rm -rf /"})], "tool_use"),
        make_response([text_block("ok, skipped")], "end_turn"),
    ]
    agent, client = make_agent(monkeypatch, responses, confirm=lambda desc: False)

    assert agent.chat("delete everything") == "ok, skipped"
    tool_result_msg = agent.messages[-2]
    assert tool_result_msg["content"][0]["content"] == "The user denied permission for this action."


def test_chat_reports_unknown_tool_as_error(monkeypatch):
    responses = [
        make_response([tool_use_block("id1", "does_not_exist", {})], "tool_use"),
        make_response([text_block("fallback")], "end_turn"),
    ]
    agent, client = make_agent(monkeypatch, responses)

    assert agent.chat("do something weird") == "fallback"
    tool_result_msg = agent.messages[-2]
    assert "unknown tool" in tool_result_msg["content"][0]["content"]


def test_chat_stops_after_max_iterations(monkeypatch):
    responses = [
        make_response([tool_use_block("id1", "get_time", {})], "tool_use") for _ in range(3)
    ]
    agent, client = make_agent(monkeypatch, responses)
    agent.max_iterations = 3

    reply = agent.chat("loop forever")
    assert "tool-use limit" in reply
    assert len(client.messages.calls) == 3
