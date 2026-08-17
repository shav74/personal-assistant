"""Permission layer for agent tool use.

Design principle: the LLM never has unilateral access to side effects.
Tools are classified as safe (read-only: auto-run) or dangerous (writes,
deletes, shell execution, anything that changes the world: require explicit
user confirmation).

The confirmation mechanism is a callback supplied by the interface (CLI,
web, voice), so this module stays interface-agnostic.
"""

from __future__ import annotations

import json
from typing import Callable

from .tools.base import Tool


class PermissionDenied(Exception):
    """Raised when the user refuses a dangerous action."""


def check_permission(
    tool: Tool,
    tool_input: dict,
    confirm: Callable[[str], bool],
) -> None:
    """Raise PermissionDenied unless the action is safe or user-approved."""
    if not tool.check_dangerous(tool_input):
        return

    description = (
        f"The assistant wants to run '{tool.name}' with input:\n"
        f"{json.dumps(tool_input, indent=2)}"
    )
    if not confirm(description):
        raise PermissionDenied(tool.name)
