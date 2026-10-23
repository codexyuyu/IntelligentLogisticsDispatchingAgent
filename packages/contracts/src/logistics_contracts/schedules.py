"""Schedule lifecycle boundary bodies (P16 subset)."""

from __future__ import annotations

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from logistics_contracts.planning import (
    CommitCommandDTO,
    PlanningScopeDTO,
    RouteStopDTO,
    TransportPlanDTO,
)
from logistics_contracts.transport import TransportProblemDTO


class ScheduleCreate(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    schema_version: Literal["2.0.0"] = "2.0.0"
    name: str = Field(min_length=1, max_length=128)
    scope: PlanningScopeDTO


class ScheduleView(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    schema_version: Literal["2.0.0"] = "2.0.0"
    schedule_id: UUID
    name: str
    status: str
    epoch_utc: datetime
    horizon_s: int
    active_version_id: UUID | None


class SchedulePage(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    schema_version: Literal["2.0.0"] = "2.0.0"
    items: tuple[ScheduleView, ...]


class CandidateCreate(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    schema_version: Literal["2.0.0"] = "2.0.0"
    problem: TransportProblemDTO
    plan: TransportPlanDTO
    stops: tuple[RouteStopDTO, ...]
    solver_evidence_refs: tuple[UUID, ...]
    base_version_id: UUID | None = None


class CandidateView(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    schema_version: Literal["2.0.0"] = "2.0.0"
    candidate_id: UUID
    schedule_id: UUID
    snapshot_id: UUID
    content_hash: str
    validation_report_id: UUID
    valid: bool


class CommitRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    schema_version: Literal["2.0.0"] = "2.0.0"
    command: CommitCommandDTO
