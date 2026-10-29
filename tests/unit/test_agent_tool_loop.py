"""Tool-calling protocol tests.

These cover the loop mechanics and the wire format only. They do NOT prove that a real model
chooses the right tool — that needs a live provider and is verified separately.
"""

from __future__ import annotations

import json

import pytest

from logistics_agents.llm import (
    ChatMessage,
    DeepSeekProvider,
    LLMReply,
    LLMSettings,
    ProviderUnavailableError,
    ToolCall,
    _parse_tool_calls,
)
from logistics_agents.service import AgentChatService
from logistics_agents.tools import ToolRegistry, ToolResult, ToolSpec


class ScriptedProvider:
    """Replays a fixed list of replies and records what it was asked."""

    def __init__(self, replies: list[LLMReply]):
        self.replies = list(replies)
        self.calls: list[tuple[ChatMessage, ...]] = []
        self.tools_seen: list[object] = []

    @property
    def configured(self) -> bool:
        return True

    def complete(self, messages, tools=None) -> LLMReply:
        self.calls.append(tuple(messages))
        self.tools_seen.append(tools)
        if not self.replies:
            raise AssertionError("provider called more times than scripted")
        return self.replies.pop(0)


def _call(call_id: str, name: str, arguments: dict | None = None,
          raw: str | None = None) -> ToolCall:
    return ToolCall(id=call_id, name=name,
                    arguments=raw if raw is not None else json.dumps(arguments or {}))


def _registry() -> ToolRegistry:
    registry = ToolRegistry()
    registry.register(ToolSpec(name="job_status", description="read job status",
                               allowed_roles=("operator",),
                               parameters={"type": "object",
                                           "properties": {"job_id": {"type": "string"}},
                                           "required": ["job_id"]}),
                      lambda actor, args: {"job_id": args["job_id"], "status": "done"})
    return registry


def test_loop_executes_tool_then_returns_final_answer():
    provider = ScriptedProvider([
        LLMReply(content="", model="m", tool_calls=(_call("c1", "job_status", {"job_id": "j1"}),)),
        LLMReply(content="任务 j1 已完成。", model="m"),
    ])
    service = AgentChatService(provider)
    registry = _registry()

    run = service.run_with_tools(
        "j1 什么状态", tools=[s.to_openai_tool() for s in registry.specs()],
        executor=lambda name, args: registry.invoke(name, _actor(), args))

    assert run.stopped_reason == "final_answer"
    assert run.reply.content == "任务 j1 已完成。"
    assert len(run.turns) == 1
    assert run.turns[0].name == "job_status"
    assert run.turns[0].ok is True
    assert run.turns[0].content["status"] == "done"

    # 回填的 tool 消息必须带上 tool_call_id，否则真实 provider 会拒绝下一轮
    second_call_messages = provider.calls[1]
    tool_messages = [m for m in second_call_messages if m.role == "tool"]
    assert len(tool_messages) == 1
    assert tool_messages[0].tool_call_id == "c1"
    payload = json.loads(tool_messages[0].content)
    assert payload["ok"] is True and payload["content"]["status"] == "done"


def test_unknown_tool_is_reported_back_not_raised():
    provider = ScriptedProvider([
        LLMReply(content="", model="m",
                 tool_calls=(_call("c1", "drop_database"),)),
        LLMReply(content="该工具不可用。", model="m"),
    ])
    service = AgentChatService(provider)
    registry = _registry()

    run = service.run_with_tools(
        "删库", tools=[s.to_openai_tool() for s in registry.specs()],
        executor=lambda name, args: registry.invoke(name, _actor(), args))

    assert run.turns[0].ok is False
    assert run.turns[0].error_code == "tool_not_found"
    assert run.reply.content == "该工具不可用。"


def test_malformed_arguments_never_reach_the_executor():
    seen: list[str] = []
    provider = ScriptedProvider([
        LLMReply(content="", model="m", tool_calls=(_call("c1", "job_status", raw="{not json"),)),
        LLMReply(content="参数无法解析。", model="m"),
    ])
    service = AgentChatService(provider)

    run = service.run_with_tools(
        "x", tools=[{"type": "function", "function": {"name": "job_status"}}],
        executor=lambda name, args: seen.append(name) or ToolResult(name=name, ok=True, content={}))

    assert seen == []
    assert run.turns[0].ok is False
    assert run.turns[0].error_code == "invalid_arguments"
    assert run.turns[0].arguments is None


def test_loop_stops_at_max_turns_and_says_so():
    looping = LLMReply(content="", model="m",
                       tool_calls=(_call("c1", "job_status", {"job_id": "j1"}),))
    provider = ScriptedProvider([looping, looping, looping])
    service = AgentChatService(provider)

    run = service.run_with_tools(
        "x", tools=[{"type": "function", "function": {"name": "job_status"}}],
        executor=lambda name, args: ToolResult(name=name, ok=True, content={"ok": 1}),
        max_turns=3)

    assert run.stopped_reason == "max_turns"
    assert len(run.turns) == 3
    assert run.reply.tool_calls  # 最后一轮仍是工具调用，不能当成最终答案


def test_failing_executor_does_not_break_the_run():
    def boom(name, args):
        raise RuntimeError("solver crashed")

    provider = ScriptedProvider([
        LLMReply(content="", model="m", tool_calls=(_call("c1", "job_status", {"job_id": "j1"}),)),
        LLMReply(content="工具执行失败。", model="m"),
    ])
    run = AgentChatService(provider).run_with_tools(
        "x", tools=[{"type": "function", "function": {"name": "job_status"}}], executor=boom)

    assert run.turns[0].ok is False
    assert run.turns[0].error_code == "tool_failed"
    assert run.reply.content == "工具执行失败。"


def test_tools_payload_format():
    spec = ToolSpec(name="t", description="d", allowed_roles=("operator",),
                    parameters={"type": "object", "properties": {"a": {"type": "string"}}})
    assert spec.to_openai_tool() == {
        "type": "function",
        "function": {"name": "t", "description": "d",
                     "parameters": {"type": "object", "properties": {"a": {"type": "string"}}}},
    }
    no_args = ToolSpec(name="t2", description="d", allowed_roles=("operator",))
    assert no_args.to_openai_tool()["function"]["parameters"] == {"type": "object", "properties": {}}


def test_tool_spec_rejects_non_object_parameters():
    with pytest.raises(ValueError):
        ToolSpec(name="t", description="d", allowed_roles=("operator",),
                 parameters={"type": "array"})


class _FakeResponse:
    def __init__(self, body: dict):
        self._body = json.dumps(body).encode("utf-8")

    def read(self) -> bytes:
        return self._body

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


def _capture(monkeypatch, reply_body: dict) -> dict:
    captured: dict = {}

    def fake_urlopen(request, timeout=None):
        captured["body"] = json.loads(request.data.decode("utf-8"))
        captured["headers"] = dict(request.headers)
        return _FakeResponse(reply_body)

    monkeypatch.setattr("urllib.request.urlopen", fake_urlopen)
    return captured


def test_request_body_is_unchanged_when_tools_absent(monkeypatch):
    captured = _capture(monkeypatch, {"model": "deepseek-chat",
                                      "choices": [{"message": {"content": "hi"}}]})
    provider = DeepSeekProvider(LLMSettings(api_key="sk-real-key"))
    provider.complete((ChatMessage("system", "s"), ChatMessage("user", "u")))

    assert set(captured["body"]) == {"model", "messages", "temperature"}
    assert "tools" not in captured["body"]


def test_request_body_carries_tools_when_present(monkeypatch):
    captured = _capture(monkeypatch, {"model": "deepseek-chat",
                                      "choices": [{"message": {"content": "ok"}}]})
    provider = DeepSeekProvider(LLMSettings(api_key="sk-real-key"))
    provider.complete((ChatMessage("user", "u"),),
                      tools=[{"type": "function", "function": {"name": "t"}}])

    assert captured["body"]["tool_choice"] == "auto"
    assert captured["body"]["tools"][0]["function"]["name"] == "t"


def test_response_tool_calls_are_parsed(monkeypatch):
    _capture(monkeypatch, {"model": "deepseek-chat", "choices": [{"message": {
        "content": None,
        "tool_calls": [{"id": "c1", "type": "function",
                        "function": {"name": "job_status",
                                     "arguments": "{\"job_id\": \"j1\"}"}}]}}]})
    reply = DeepSeekProvider(LLMSettings(api_key="sk-real-key")).complete(
        (ChatMessage("user", "u"),), tools=[{"type": "function", "function": {"name": "t"}}])

    assert reply.content == ""
    assert len(reply.tool_calls) == 1
    assert reply.tool_calls[0].name == "job_status"
    assert json.loads(reply.tool_calls[0].arguments) == {"job_id": "j1"}


def test_placeholder_key_is_refused_before_any_http_call(monkeypatch):
    def explode(*_a, **_k):
        raise AssertionError("must not reach the network with a placeholder key")

    monkeypatch.setattr("urllib.request.urlopen", explode)
    with pytest.raises(ProviderUnavailableError):
        DeepSeekProvider(LLMSettings.from_env()).complete((ChatMessage("user", "u"),))


def test_malformed_tool_calls_are_dropped_not_fatal():
    assert _parse_tool_calls(None) == ()
    assert _parse_tool_calls([{"id": "c1"}]) == ()
    assert _parse_tool_calls([{"function": {"name": "t"}}]) == ()
    assert len(_parse_tool_calls([{"id": "c1", "function": {"name": "t", "arguments": "{}"}}])) == 1


def test_chat_message_rejects_orphan_tool_role():
    with pytest.raises(ValueError):
        ChatMessage("tool", "result")


def _actor():
    from uuid import uuid4

    from logistics_domain.runtime import ActorContext, ActorRole
    return ActorContext(actor_id=uuid4(), role=ActorRole.OPERATOR, scope_id=uuid4())
