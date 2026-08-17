import pytest

from assistant.permissions import PermissionDenied, check_permission
from assistant.tools.base import Tool


def make_tool(dangerous=False, is_dangerous=None):
    return Tool(
        name="t",
        description="d",
        input_schema={},
        func=lambda **k: "ran",
        dangerous=dangerous,
        is_dangerous=is_dangerous,
    )


def test_safe_tool_never_asks_for_confirmation():
    asked = []
    check_permission(make_tool(dangerous=False), {}, confirm=lambda desc: asked.append(desc) or True)
    assert asked == []


def test_dangerous_tool_allowed_when_confirmed():
    check_permission(make_tool(dangerous=True), {"x": 1}, confirm=lambda desc: True)  # no raise


def test_dangerous_tool_denied_raises_permission_denied():
    with pytest.raises(PermissionDenied):
        check_permission(make_tool(dangerous=True), {"x": 1}, confirm=lambda desc: False)


def test_confirm_receives_readable_description():
    seen = {}

    def confirm(desc):
        seen["desc"] = desc
        return True

    check_permission(make_tool(dangerous=True), {"command": "rm -rf /"}, confirm)
    assert "t" in seen["desc"]
    assert "rm -rf /" in seen["desc"]


def test_per_call_is_dangerous_overrides_static_dangerous_flag():
    tool = make_tool(dangerous=True, is_dangerous=lambda inp: False)

    def confirm(desc):
        raise AssertionError("confirm should not be called for a call classified as safe")

    check_permission(tool, {}, confirm)  # no raise, confirm never invoked
