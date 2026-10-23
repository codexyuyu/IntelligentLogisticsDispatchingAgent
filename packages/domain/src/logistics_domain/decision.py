"""Agent decision records (P19/P23 audit subset)."""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from logistics_domain.errors import InvalidInputError
from logistics_domain.orders import Entity
from logistics_domain.primitives import require_uuid

__all__ = ["DecisionRecord"]


@dataclass(frozen=True, slots=True)
class DecisionRecord(Entity):
    lifecycle = "decision_record"

    run_id: UUID | None
    tool_call_id: UUID | None
    decision_type: str
    payload_json: str
    rationale: str
    confidence: float
    evidence_refs: tuple[UUID, ...]

    def __post_init__(self) -> None:
        Entity.__post_init__(self)
        for name in ("run_id", "tool_call_id"):
            value = getattr(self, name)
            if value is not None:
                require_uuid(value, field=f"DecisionRecord.{name}")
        if not isinstance(self.decision_type, str) or not 1 <= len(self.decision_type) <= 64:
            raise InvalidInputError("DecisionRecord.decision_type must be 1..64 characters")
        if not isinstance(self.payload_json, str):
            raise InvalidInputError("DecisionRecord.payload_json must be a string")
        if not isinstance(self.rationale, str) or not 1 <= len(self.rationale) <= 2000:
            raise InvalidInputError("DecisionRecord.rationale must be 1..2000 characters")
        if not isinstance(self.confidence, (int, float)) or isinstance(self.confidence, bool):
            raise InvalidInputError("DecisionRecord.confidence must be numeric")
        if not 0 <= float(self.confidence) <= 1:
            raise InvalidInputError("DecisionRecord.confidence must be within [0,1]")
        if not isinstance(self.evidence_refs, tuple):
            raise InvalidInputError("DecisionRecord.evidence_refs must be a tuple")
        for index, reference in enumerate(self.evidence_refs):
            require_uuid(reference, field=f"DecisionRecord.evidence_refs[{index}]")
