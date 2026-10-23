"""Tool-call audit records (P17/P19 subset)."""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from logistics_domain.errors import InvalidInputError
from logistics_domain.orders import Entity
from logistics_domain.primitives import require_non_negative_int, require_uuid

__all__ = ["ToolCall"]


@dataclass(frozen=True, slots=True)
class ToolCall(Entity):
    lifecycle = "tool_call"

    run_id: UUID | None
    tool_name: str
    arguments_json: str
    result_json: str | None
    error_code: str | None
    duration_ms: int
    trace_id: UUID

    def __post_init__(self) -> None:
        Entity.__post_init__(self)
        if self.run_id is not None:
            require_uuid(self.run_id, field="ToolCall.run_id")
        if not isinstance(self.tool_name, str) or not 1 <= len(self.tool_name) <= 64:
            raise InvalidInputError("ToolCall.tool_name must be 1..64 characters")
        if not isinstance(self.arguments_json, str):
            raise InvalidInputError("ToolCall.arguments_json must be a string")
        if self.result_json is not None and not isinstance(self.result_json, str):
            raise InvalidInputError("ToolCall.result_json must be a string")
        if self.error_code is not None and (not isinstance(self.error_code, str)
                                            or len(self.error_code) > 64):
            raise InvalidInputError("ToolCall.error_code must be <= 64 characters")
        require_non_negative_int(self.duration_ms, field="ToolCall.duration_ms")
        require_uuid(self.trace_id, field="ToolCall.trace_id")
