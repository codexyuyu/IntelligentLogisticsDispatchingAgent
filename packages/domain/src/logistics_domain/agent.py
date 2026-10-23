"""Agent run audit records (P19/P23 subset)."""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from logistics_domain.errors import InvalidInputError
from logistics_domain.orders import Entity
from logistics_domain.primitives import require_non_negative_int, require_uuid

__all__ = ["AgentRun"]


@dataclass(frozen=True, slots=True)
class AgentRun(Entity):
    lifecycle = "agent_run"

    session_id: UUID | None
    prompt: str
    reply: str | None
    model: str | None
    provider_configured: bool
    latency_ms: int
    trace_id: UUID

    def __post_init__(self) -> None:
        Entity.__post_init__(self)
        if self.session_id is not None:
            require_uuid(self.session_id, field="AgentRun.session_id")
        if not isinstance(self.prompt, str) or not 1 <= len(self.prompt) <= 4000:
            raise InvalidInputError("AgentRun.prompt must be 1..4000 characters")
        if self.reply is not None and (not isinstance(self.reply, str) or len(self.reply) > 20000):
            raise InvalidInputError("AgentRun.reply must be <= 20000 characters")
        if self.model is not None and (not isinstance(self.model, str) or len(self.model) > 128):
            raise InvalidInputError("AgentRun.model must be <= 128 characters")
        if not isinstance(self.provider_configured, bool):
            raise InvalidInputError("AgentRun.provider_configured must be bool")
        require_non_negative_int(self.latency_ms, field="AgentRun.latency_ms")
        require_uuid(self.trace_id, field="AgentRun.trace_id")
