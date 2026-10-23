"""Provider-neutral LLM client (P18 subset).

Only this module knows the OpenAI-compatible HTTP shape. A placeholder key is accepted by
configuration but the provider refuses to call an external endpoint with it, so a missing key
produces an explicit 503 rather than a fake assistant answer.
"""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Protocol

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
class ChatMessage:
    role: str
    content: str

    def __post_init__(self) -> None:
        if self.role not in ("system", "user", "assistant"):
            raise ValueError("chat role must be system/user/assistant")
        if not self.content:
            raise ValueError("chat content must not be empty")


@dataclass(frozen=True, slots=True)
class LLMReply:
    content: str
    model: str


class LLMProvider(Protocol):
    @property
    def configured(self) -> bool: ...

    def complete(self, messages: tuple[ChatMessage, ...]) -> LLMReply: ...


class DeepSeekProvider:
    def __init__(self, settings: LLMSettings):
        self.settings = settings

    @property
    def configured(self) -> bool:
        return self.settings.configured

    def complete(self, messages: tuple[ChatMessage, ...]) -> LLMReply:
        if not self.settings.configured:
            raise ProviderUnavailableError(
                "LLM provider key is a placeholder; set DEEPSEEK_API_KEY before using chat")
        payload = json.dumps({
            "model": self.settings.model,
            "messages": [{"role": item.role, "content": item.content} for item in messages],
            "temperature": 0,
        }).encode("utf-8")
        request = urllib.request.Request(
            f"{self.settings.base_url.rstrip('/')}/chat/completions", data=payload,
            headers={"Content-Type": "application/json",
                     "Authorization": f"Bearer {self.settings.api_key}"},
            method="POST")
        try:
            with urllib.request.urlopen(request, timeout=self.settings.timeout_s) as response:
                body = json.loads(response.read().decode("utf-8"))
        except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, OSError) as exc:
            raise ProviderUnavailableError("LLM provider request failed") from exc
        try:
            content = body["choices"][0]["message"]["content"]
            model = body.get("model", self.settings.model)
        except (KeyError, IndexError, TypeError) as exc:
            raise ProviderUnavailableError("LLM provider returned an unexpected response") from exc
        if not isinstance(content, str) or not content.strip():
            raise ProviderUnavailableError("LLM provider returned an empty answer")
        return LLMReply(content=content, model=model)
