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
from logistics_contracts.warehouse import WarehouseProblemDTO, WarehouseSolutionDTO


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
    warehouse_problem: WarehouseProblemDTO | None = None
    warehouse_solution: WarehouseSolutionDTO | None = None


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


class ScheduleVersionView(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    schema_version: Literal["2.0.0"] = "2.0.0"
    version_id: UUID
    schedule_id: UUID
    version_no: int
    status: str
    content_hash: str
    parent_version_id: UUID | None
    snapshot_id: UUID
    validation_report_ref: UUID
    committed_at: datetime


class ScheduleVersionPage(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    schema_version: Literal["2.0.0"] = "2.0.0"
    items: tuple[ScheduleVersionView, ...]


class ScheduleTaskView(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    schema_version: Literal["2.0.0"] = "2.0.0"
    task_id: UUID
    task_kind: str
    assigned_resource_ids: tuple[UUID, ...]
    planned_start_s: int
    planned_end_s: int
    sequence: int | None
    status: str


class ScheduleVersionDetailView(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    schema_version: Literal["2.0.0"] = "2.0.0"
    version: ScheduleVersionView
    tasks: tuple[ScheduleTaskView, ...]


class ScheduleTaskChange(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    schema_version: Literal["2.0.0"] = "2.0.0"
    task_id: UUID
    before_start_s: int
    before_end_s: int
    after_start_s: int
    after_end_s: int
    before_resource_ids: tuple[UUID, ...]
    after_resource_ids: tuple[UUID, ...]


class ScheduleDiffView(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    schema_version: Literal["2.0.0"] = "2.0.0"
    schedule_id: UUID
    base_version_id: UUID
    candidate_version_id: UUID
    base_hash: str
    candidate_hash: str
    added_task_ids: tuple[UUID, ...]
    removed_task_ids: tuple[UUID, ...]
    changed_tasks: tuple[ScheduleTaskChange, ...]
    unchanged_count: int
