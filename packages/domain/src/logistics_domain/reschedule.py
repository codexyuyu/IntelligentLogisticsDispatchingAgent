"""Local reschedule proposals (P15-01 subset).

A proposal is a set of typed adjustments, not a validated schedule. It never claims that a
solution exists; the caller must run the solver and independent validator before commit.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from uuid import UUID

from logistics_domain.errors import InvalidInputError
from logistics_domain.primitives import require_non_negative_int, require_sha256, require_uuid

__all__ = [
    "AdjustmentSpec",
    "ReschedulePolicy",
    "RescheduleProposal",
    "RescheduleStrategy",
]


class RescheduleStrategy(StrEnum):
    DEFER = "defer"
    REASSIGN = "reassign"
    ALTERNATE_RESOURCE = "alternate_resource"
    RESCUE_HANDOFF = "rescue_handoff"
    RETURN_TO_ORIGIN = "return_to_origin"
    MANUAL_REVIEW = "manual_review"


@dataclass(frozen=True, slots=True)
class ReschedulePolicy:
    max_extra_delay_s: int
    allow_scope_expansion: bool

    def __post_init__(self) -> None:
        require_non_negative_int(self.max_extra_delay_s, field="ReschedulePolicy.max_extra_delay_s")
        if not isinstance(self.allow_scope_expansion, bool):
            raise InvalidInputError("ReschedulePolicy.allow_scope_expansion must be bool")


@dataclass(frozen=True, slots=True)
class AdjustmentSpec:
    task_id: UUID
    strategy: RescheduleStrategy
    earliest_start_s: int | None
    note: str

    def __post_init__(self) -> None:
        require_uuid(self.task_id, field="AdjustmentSpec.task_id")
        if not isinstance(self.strategy, RescheduleStrategy):
            raise InvalidInputError("AdjustmentSpec.strategy must be RescheduleStrategy")
        if self.earliest_start_s is not None:
            require_non_negative_int(self.earliest_start_s, field="AdjustmentSpec.earliest_start_s")
        if not isinstance(self.note, str) or not 1 <= len(self.note) <= 256:
            raise InvalidInputError("AdjustmentSpec.note must be 1..256 characters")


@dataclass(frozen=True, slots=True)
class RescheduleProposal:
    id: UUID
    base_plan_hash: str
    event_time_s: int
    adjustments: tuple[AdjustmentSpec, ...]
    requires_manual_review: bool
    rationale: str

    def __post_init__(self) -> None:
        require_uuid(self.id, field="RescheduleProposal.id")
        require_sha256(self.base_plan_hash, field="RescheduleProposal.base_plan_hash")
        require_non_negative_int(self.event_time_s, field="RescheduleProposal.event_time_s")
        if not isinstance(self.adjustments, tuple):
            raise InvalidInputError("RescheduleProposal.adjustments must be a tuple")
        for index, adjustment in enumerate(self.adjustments):
            if not isinstance(adjustment, AdjustmentSpec):
                raise InvalidInputError(f"adjustments[{index}] must be AdjustmentSpec")
        if not isinstance(self.requires_manual_review, bool):
            raise InvalidInputError("RescheduleProposal.requires_manual_review must be bool")
        if not isinstance(self.rationale, str) or not 1 <= len(self.rationale) <= 512:
            raise InvalidInputError("RescheduleProposal.rationale must be 1..512 characters")
