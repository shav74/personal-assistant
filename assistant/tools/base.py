"""Tool definition and registry.

A Tool bundles:
  - the JSON schema the LLM sees (name, description, input_schema)
  - the Python function that actually runs
  - a `dangerous` flag consumed by the permission layer

Register tools with the @tool decorator; the registry converts them to the
Anthropic API's tool format automatically.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable


@dataclass
class Tool:
    name: str
    description: str
    input_schema: dict
    func: Callable[..., Any]
    dangerous: bool = False  # dangerous tools require user confirmation

    def run(self, **kwargs) -> Any:
        return self.func(**kwargs)


class ToolRegistry:
    def __init__(self):
        self._tools: dict[str, Tool] = {}

    def register(self, tool: Tool) -> None:
        if tool.name in self._tools:
            raise ValueError(f"Duplicate tool name: {tool.name}")
        self._tools[tool.name] = tool

    def get(self, name: str) -> Tool | None:
        return self._tools.get(name)

    def schemas(self) -> list[dict]:
        """Tool definitions in the format the Anthropic API expects."""
        return [
            {
                "name": t.name,
                "description": t.description,
                "input_schema": t.input_schema,
            }
            for t in self._tools.values()
        ]


registry = ToolRegistry()


def tool(
    name: str,
    description: str,
    input_schema: dict | None = None,
    dangerous: bool = False,
):
    """Decorator: turn a function into a registered tool.

    Example:
        @tool("get_time", "Get the current date and time.")
        def get_time() -> str:
            ...
    """

    def wrapper(func: Callable) -> Callable:
        registry.register(
            Tool(
                name=name,
                description=description,
                input_schema=input_schema
                or {"type": "object", "properties": {}, "required": []},
                func=func,
                dangerous=dangerous,
            )
        )
        return func

    return wrapper
