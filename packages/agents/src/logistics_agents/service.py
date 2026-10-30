"""Minimal coordinator-facing chat service (P19/P23 subset)."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Callable, Mapping, Sequence

from logistics_agents.llm import ChatMessage, LLMProvider, LLMReply, ToolCall
from logistics_agents.tools import ToolResult

SYSTEM_PROMPT = (
    "You are the logistics dispatching assistant. You may explain and summarize data, but "
    "you must never invent a schedule, delivery result or inventory fact. If a requested "
    "capability is not enabled, say so explicitly and ask the operator to run the "
    "deterministic solver/validator first."
)

TOOL_SYSTEM_PROMPT = (
    "You are the logistics dispatching assistant. You may call the provided tools to read "
    "facts and to prepare a disposition proposal. Tool results are the only source of truth: "
    "never invent an order, vehicle, delay, solver status or cost. A prepared proposal is "
    "never approved by you — an operator must confirm it. If no tool can answer the question, "
    "say so explicitly instead of guessing."
)

ToolExecutor = Callable[[str, Mapping[str, Any]], ToolResult]


@dataclass(frozen=True, slots=True)
class ToolTurn:
    """One executed tool call, kept for audit and replay."""

    turn: int
    tool_call_id: str
    name: str
    arguments: Mapping[str, Any] | None
    ok: bool
    content: Mapping[str, Any]
    error_code: str | None = None


@dataclass(frozen=True, slots=True)
class AgentRun:
    reply: LLMReply
    turns: tuple[ToolTurn, ...]
    stopped_reason: str  # final_answer | max_turns


class AgentChatService:
    def __init__(self, provider: LLMProvider):
        self.provider = provider

    @property
    def configured(self) -> bool:
        return self.provider.configured

    def reply(self, message: str) -> LLMReply:
        return self.provider.complete((
            ChatMessage("system", SYSTEM_PROMPT),
            ChatMessage("user", message),
        ))

    def run_with_tools(self, message: str, *, tools: Sequence[Mapping[str, Any]],
                       executor: ToolExecutor, max_turns: int = 4,
                       max_tool_calls: int = 12) -> AgentRun:
        """Drive a bounded model -> tool -> model loop.

        The model decides which tool to call; this method only executes what it asks for and
        feeds the result back. It stops at the first assistant turn without tool calls, or when
        ``max_turns`` is exhausted — in the latter case the run is reported as such rather than
        being presented as a completed answer.
        """
        if max_turns < 1 or max_tool_calls < 1:
            raise ValueError("turn and tool-call limits must be positive")
        messages: list[ChatMessage] = [
            ChatMessage("system", TOOL_SYSTEM_PROMPT),
            ChatMessage("user", message),
        ]
        turns: list[ToolTurn] = []
        last_reply = LLMReply(content="", model="")
        for turn in range(1, max_turns + 1):
            last_reply = self.provider.complete(tuple(messages), tools=tools)
            if not last_reply.tool_calls:
                return AgentRun(reply=last_reply, turns=tuple(turns),
                                stopped_reason="final_answer")
            messages.append(ChatMessage("assistant", last_reply.content,
                                        tool_calls=last_reply.tool_calls))
            for call in last_reply.tool_calls:
                if len(turns) >= max_tool_calls:
                    return AgentRun(reply=last_reply, turns=tuple(turns),
                                    stopped_reason="max_turns")
                result, arguments = self._execute(executor, call)
                turns.append(ToolTurn(turn=turn, tool_call_id=call.id, name=call.name,
                                      arguments=arguments, ok=result.ok,
                                      content=result.content, error_code=result.error_code))
                messages.append(ChatMessage("tool", _tool_payload(result),
                                            tool_call_id=call.id, name=call.name))
        return AgentRun(reply=last_reply, turns=tuple(turns), stopped_reason="max_turns")

    @staticmethod
    def _execute(executor: ToolExecutor, call: ToolCall
                 ) -> tuple[ToolResult, Mapping[str, Any] | None]:
        try:
            arguments = json.loads(call.arguments) if call.arguments else {}
        except json.JSONDecodeError:
            return (ToolResult(name=call.name, ok=False, content={},
                               error_code="invalid_arguments"), None)
        if not isinstance(arguments, dict):
            return (ToolResult(name=call.name, ok=False, content={},
                               error_code="invalid_arguments"), None)
        try:
            return executor(call.name, arguments), arguments
        except Exception:  # noqa: BLE001 - a failing tool must not abort the audit trail
            return (ToolResult(name=call.name, ok=False, content={},
                               error_code="tool_failed"), arguments)


def _tool_payload(result: ToolResult) -> str:
    return json.dumps({"ok": result.ok, "content": dict(result.content),
                       "error_code": result.error_code}, ensure_ascii=False, default=str)
