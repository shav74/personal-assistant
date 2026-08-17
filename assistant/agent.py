"""The core agent loop.

This is the heart of the assistant: a loop that sends conversation state to
the LLM, executes any tool calls it makes (subject to the permission layer),
feeds results back, and repeats until the model produces a final answer.

Deliberately hand-rolled (no LangChain/LangGraph) so every step is visible
and explainable.
"""

from __future__ import annotations

from typing import Callable

from anthropic import Anthropic

from .config import settings
from .memory.store import MemoryStore
from .permissions import PermissionDenied, check_permission
from .tools import registry


SYSTEM_PROMPT = """You are {name}, a personal assistant running on your \
user's own machine. You are concise, practical, and honest.

You have access to tools. Use them when they help; don't use them when you
can answer directly. If a tool fails, say so plainly and suggest a fix.

Facts you remember about the user:
{memories}
"""


class Agent:
    """Orchestrates the conversation between user, LLM, and tools."""

    def __init__(
        self,
        confirm: Callable[[str], bool],
        model: str | None = None,
        max_iterations: int = 10,
    ):
        """
        Args:
            confirm: Callback invoked before any dangerous tool runs.
                Receives a human-readable description of the action and
                returns True to allow it. The CLI passes a y/n prompt;
                a voice frontend could pass a spoken confirmation. Keeping
                this as a callback keeps the agent interface-agnostic.
            model: Anthropic model ID. Defaults to config.
            max_iterations: Safety valve against infinite tool loops.
        """
        self.client = Anthropic(api_key=settings.anthropic_api_key)
        self.model = model or settings.model
        self.confirm = confirm
        self.max_iterations = max_iterations
        self.memory = MemoryStore(settings.db_path)
        self.messages: list[dict] = []  # running conversation history
        self._current_query = ""  # this turn's user text, for memory recall

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def chat(self, user_input: str) -> str:
        """Process one user turn and return the assistant's final reply."""
        self._current_query = user_input
        self.messages.append({"role": "user", "content": user_input})

        for _ in range(self.max_iterations):
            response = self._call_llm()

            # Collect any text the model produced this step.
            text_parts = [b.text for b in response.content if b.type == "text"]

            if response.stop_reason != "tool_use":
                # Model is done — record its reply and return it.
                self.messages.append(
                    {"role": "assistant", "content": response.content}
                )
                return "\n".join(text_parts).strip()

            # Model wants to use tools: record its request, run each tool,
            # then send the results back as the next user message.
            self.messages.append(
                {"role": "assistant", "content": response.content}
            )
            tool_results = []
            for block in response.content:
                if block.type != "tool_use":
                    continue
                result = self._execute_tool(block.name, block.input)
                tool_results.append(
                    {
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": result,
                    }
                )
            self.messages.append({"role": "user", "content": tool_results})

        return "I hit my tool-use limit for a single request — something is likely looping. Try rephrasing."

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------
    def _call_llm(self):
        memories = self.memory.format_for_prompt(self._current_query) or "(nothing yet)"
        return self.client.messages.create(
            model=self.model,
            max_tokens=4096,
            system=SYSTEM_PROMPT.format(
                name=settings.assistant_name, memories=memories
            ),
            tools=registry.schemas(),
            messages=self.messages,
        )

    def _execute_tool(self, name: str, tool_input: dict) -> str:
        tool = registry.get(name)
        if tool is None:
            return f"Error: unknown tool '{name}'"
        try:
            check_permission(tool, tool_input, self.confirm)
            return str(tool.run(**tool_input))
        except PermissionDenied:
            return "The user denied permission for this action."
        except Exception as exc:  # surface errors to the model, don't crash
            return f"Error running {name}: {exc}"
