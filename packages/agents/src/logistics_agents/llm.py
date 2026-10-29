"""Provider-neutral LLM client (P18 subset).

Only this module knows the OpenAI-compatible HTTP shape. A placeholder key is accepted by
configuration but the provider refuses to call an external endpoint with it, so a missing key
produces an explicit 503 rather than a fake assistant answer.

Tool calling (OpenAI-compatible ``tools`` / ``tool_calls``) is opt-in: when ``tools`` is
omitted the request body is byte-for-byte the pre-tool-calling shape, so single-turn chat
callers keep their existing behaviour.
"""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Any, Mapping, Protocol, Sequence

from logistics_domain.errors import DomainError
from logistics_domain.states import ErrorCode


class ProviderUnavailableError(DomainError):
    code = ErrorCode.PROVIDER_UNAVAILABLE

    def __init__(self, message: str):
        super().__init__(message)


@dataclass(frozen=True, slots=True)
class LLMSettings:
    api_key: str
    base_url: str = "https://api.deepseek.com"
    model: str = "deepseek-chat"
    timeout_s: int = 30

    @property
    def configured(self) -> bool:
        return bool(self.api_key) and not self.api_key.startswith("sk-placeholder")

    @classmethod
    def from_env(cls) -> "LLMSettings":
        return cls(api_key=os.environ.get("DEEPSEEK_API_KEY", "sk-placeholder"),
                   base_url=os.environ.get("DEEPSEEK_BASE_URL", "https://api.deepseek.com"),
                   model=os.environ.get("DEEPSEEK_MODEL", "deepseek-chat"),
                   timeout_s=int(os.environ.get("DEEPSEEK_TIMEOUT_S", "30")))


@dataclass(frozen=True, slots=True)
class ToolCall:
    """A model-requested tool invocation.

    ``arguments`` keeps the provider's raw JSON text on purpose: parsing is the caller's job so
    that malformed arguments surface as an explicit ``invalid_arguments`` result rather than
    being silently coerced into an empty mapping.
    """

    id: str
    name: str
    arguments: str

    def __post_init__(self) -> None:
        if not self.id:
            raise ValueError("tool call id must not be empty")
        if not self.name:
            raise ValueError("tool call name must not be empty")


@dataclass(frozen=True, slots=True)
class ChatMessage:
    role: str
    content: str = ""
    tool_calls: tuple[ToolCall, ...] = ()
    tool_call_id: str | None = None
    name: str | None = None

    def __post_init__(self) -> None:
        if self.role not in ("system", "user", "assistant", "tool"):
            raise ValueError("chat role must be system/user/assistant/tool")
        if self.role == "tool" and not self.tool_call_id:
            raise ValueError("tool messages require tool_call_id")
        if not self.content and not self.tool_calls and self.role != "tool":
            raise ValueError("chat content must not be empty")

    def to_wire(self) -> dict[str, Any]:
        body: dict[str, Any] = {"role": self.role}
        if self.content:
            body["content"] = self.content
        elif self.tool_calls:
            # OpenAI-compatible providers expect an explicit null content alongside tool calls.
            body["content"] = None
        if self.tool_calls:
            body["tool_calls"] = [
                {"id": call.id, "type": "function",
                 "function": {"name": call.name, "arguments": call.arguments}}
                for call in self.tool_calls
            ]
        if self.tool_call_id is not None:
            body["tool_call_id"] = self.tool_call_id
        if self.name is not None:
            body["name"] = self.name
        return body


@dataclass(frozen=True, slots=True)
class LLMReply:
    content: str
    model: str
    tool_calls: tuple[ToolCall, ...] = ()


class LLMProvider(Protocol):
    @property
    def configured(self) -> bool: ...

    def complete(self, messages: "tuple[ChatMessage, ...]",
                 tools: "Sequence[Mapping[str, Any]] | None" = None) -> LLMReply: ...


class DeepSeekProvider:
    def __init__(self, settings: LLMSettings):
        self.settings = settings

    @property
    def configured(self) -> bool:
        return self.settings.configured

    def complete(self, messages: tuple[ChatMessage, ...],
                 tools: Sequence[Mapping[str, Any]] | None = None) -> LLMReply:
        if not self.settings.configured:
            raise ProviderUnavailableError(
                "LLM provider key is a placeholder; set DEEPSEEK_API_KEY before using chat")
        body: dict[str, Any] = {
            "model": self.settings.model,
            "messages": [item.to_wire() for item in messages],
            "temperature": 0,
        }
        if tools:
            body["tools"] = list(tools)
            body["tool_choice"] = "auto"
        payload = json.dumps(body).encode("utf-8")
        request = urllib.request.Request(
            f"{self.settings.base_url.rstrip('/')}/chat/completions", data=payload,
            headers={"Content-Type": "application/json",
                     "Authorization": f"Bearer {self.settings.api_key}"},
            method="POST")
        try:
            with urllib.request.urlopen(request, timeout=self.settings.timeout_s) as response:
                reply_body = json.loads(response.read().decode("utf-8"))
        except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, OSError) as exc:
            raise ProviderUnavailableError("LLM provider request failed") from exc
        try:
            message = reply_body["choices"][0]["message"]
            model = reply_body.get("model", self.settings.model)
        except (KeyError, IndexError, TypeError) as exc:
            raise ProviderUnavailableError("LLM provider returned an unexpected response") from exc
        content = message.get("content") or ""
        tool_calls = _parse_tool_calls(message.get("tool_calls"))
        if not tool_calls and (not isinstance(content, str) or not content.strip()):
            raise ProviderUnavailableError("LLM provider returned an empty answer")
        if not isinstance(content, str):
            content = ""
        return LLMReply(content=content, model=model, tool_calls=tool_calls)


def _parse_tool_calls(raw: Any) -> tuple[ToolCall, ...]:
    """Tolerate a malformed tool_calls entry by dropping it rather than crashing the run.

    Dropping is safe: if every entry is malformed the reply falls back to empty tool_calls and
    the caller treats it as a final answer, which the loop surfaces as ``no_tool_call``.
    """
    if not raw or not isinstance(raw, list):
        return ()
    calls: list[ToolCall] = []
    for item in raw:
        if not isinstance(item, Mapping):
            continue
        function = item.get("function")
        if not isinstance(function, Mapping):
            continue
        call_id = item.get("id")
        name = function.get("name")
        arguments = function.get("arguments") or "{}"
        if not isinstance(call_id, str) or not isinstance(name, str):
            continue
        if not isinstance(arguments, str):
            arguments = json.dumps(arguments, ensure_ascii=False)
        try:
            calls.append(ToolCall(id=call_id, name=name, arguments=arguments))
        except ValueError:
            continue
    return tuple(calls)
