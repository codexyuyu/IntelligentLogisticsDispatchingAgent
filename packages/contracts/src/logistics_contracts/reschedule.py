"""Local reschedule proposal DTOs (P15-01 subset)."""

from __future__ import annotations

from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, StrictInt

from logistics_contracts.impact import ImpactRequestDTO
from logistics_contracts.planning import Record
from logistics_domain import reschedule as domain


class ReschedulePolicyDTO(Record):
    domain_type = domain.ReschedulePolicy
    max_extra_delay_s: StrictInt
    allow_scope_expansion: bool


class AdjustmentSpecDTO(Record):
    domain_type = domain.AdjustmentSpec
    task_id: UUID
    strategy: domain.RescheduleStrategy
    earliest_start_s: StrictInt | None
    note: str


class RescheduleProposalDTO(Record):
    domain_type = domain.RescheduleProposal
    id: UUID
    base_plan_hash: str
    event_time_s: StrictInt
    adjustments: tuple[AdjustmentSpecDTO, ...]
    requires_manual_review: bool
    rationale: str


class RescheduleProposalRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    schema_version: Literal["2.0.0"] = "2.0.0"
    impact: ImpactRequestDTO
    policy: ReschedulePolicyDTO
