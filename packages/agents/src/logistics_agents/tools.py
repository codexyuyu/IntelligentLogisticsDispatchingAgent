"""Whitelisted, typed tool protocol for agents (P17-01 subset).

The registry is transport-free: a caller supplies an actor and JSON-like arguments, and the
handler returns plain JSON data. Tools are read-only in this subset; no SQL or storage handle
is exposed to the agent layer.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping, Protocol

from logistics_domain.errors import DomainError
from logistics_domain.runtime import ActorContext

__all__ = ["ToolRegistry", "ToolResult", "ToolSpec"]


class ToolHandler(Protocol):
    def __call__(self, actor: ActorContext, arguments: Mapping[str, Any]) -> dict[str, Any]: ...


@dataclass(frozen=True, slots=True)
class ToolSpec:
    name: str
    description: str
    allowed_roles: tuple[str, ...]

    def __post_init__(self) -> None:
        if not self.name or len(self.name) > 64:
            raise ValueError("tool name must be 1..64 characters")
        if not self.description or len(self.description) > 256:
            raise ValueError("tool description must be 1..256 characters")
        if not self.allowed_roles:
            raise ValueError("tool requires at least one allowed role")


@dataclass(frozen=True, slots=True)
class ToolResult:
    name: str
    ok: bool
    content: dict[str, Any]
    error_code: str | None = None


class ToolRegistry:
    def __init__(self) -> None:
        self._handlers: dict[str, tuple[ToolSpec, ToolHandler]] = {}

    def register(self, spec: ToolSpec, handler: ToolHandler) -> None:
        if spec.name in self._handlers:
            raise ValueError(f"duplicate tool {spec.name!r}")
        self._handlers[spec.name] = (spec, handler)

    def specs(self) -> tuple[ToolSpec, ...]:
        return tuple(spec for spec, _ in self._handlers.values())

    def invoke(self, name: str, actor: ActorContext, arguments: Mapping[str, Any]) -> ToolResult:
        entry = self._handlers.get(name)
        if entry is None:
            return ToolResult(name=name, ok=False, content={}, error_code="tool_not_found")
        spec, handler = entry
        if actor.role.value not in spec.allowed_roles:
            return ToolResult(name=name, ok=False, content={}, error_code="tool_forbidden")
        try:
            content = handler(actor, arguments)
        except DomainError as exc:
            return ToolResult(name=name, ok=False, content={}, error_code=exc.code.value)
        except (KeyError, TypeError, ValueError):
            return ToolResult(name=name, ok=False, content={}, error_code="invalid_arguments")
        return ToolResult(name=name, ok=True, content=content)
