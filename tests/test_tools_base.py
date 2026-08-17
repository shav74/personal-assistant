import pytest

from assistant.tools.base import Tool, ToolRegistry
from assistant.tools import base as base_module


def test_tool_run_calls_underlying_func():
    t = Tool(name="x", description="d", input_schema={}, func=lambda a: a + 1)
    assert t.run(a=1) == 2


def test_check_dangerous_uses_static_flag_by_default():
    safe = Tool(name="s", description="d", input_schema={}, func=lambda: None)
    dangerous = Tool(name="d", description="d", input_schema={}, func=lambda: None, dangerous=True)
    assert safe.check_dangerous({}) is False
    assert dangerous.check_dangerous({}) is True


def test_check_dangerous_per_call_override_wins_over_static_flag():
    t = Tool(
        name="t",
        description="d",
        input_schema={},
        func=lambda: None,
        dangerous=True,
        is_dangerous=lambda inp: inp.get("x") == "boom",
    )
    assert t.check_dangerous({"x": "safe"}) is False
    assert t.check_dangerous({"x": "boom"}) is True


def test_registry_register_and_get():
    reg = ToolRegistry()
    t = Tool(name="foo", description="d", input_schema={"type": "object"}, func=lambda: "ok")
    reg.register(t)
    assert reg.get("foo") is t
    assert reg.get("missing") is None


def test_registry_rejects_duplicate_names():
    reg = ToolRegistry()
    reg.register(Tool(name="foo", description="d", input_schema={}, func=lambda: None))
    with pytest.raises(ValueError):
        reg.register(Tool(name="foo", description="d", input_schema={}, func=lambda: None))


def test_registry_schemas_shape():
    reg = ToolRegistry()
    reg.register(
        Tool(
            name="foo",
            description="desc",
            input_schema={"type": "object", "properties": {}},
            func=lambda: None,
        )
    )
    assert reg.schemas() == [
        {"name": "foo", "description": "desc", "input_schema": {"type": "object", "properties": {}}}
    ]


def test_tool_decorator_registers_and_builds_schema(monkeypatch):
    fresh_registry = ToolRegistry()
    monkeypatch.setattr(base_module, "registry", fresh_registry)

    @base_module.tool(
        "greet",
        "Say hi",
        input_schema={
            "type": "object",
            "properties": {"name": {"type": "string"}},
            "required": ["name"],
        },
    )
    def greet(name):
        return f"hi {name}"

    registered = fresh_registry.get("greet")
    assert registered is not None
    assert registered.run(name="Bob") == "hi Bob"


def test_tool_decorator_default_schema(monkeypatch):
    fresh_registry = ToolRegistry()
    monkeypatch.setattr(base_module, "registry", fresh_registry)

    @base_module.tool("noop", "does nothing")
    def noop():
        return None

    assert fresh_registry.get("noop").input_schema == {
        "type": "object",
        "properties": {},
        "required": [],
    }
