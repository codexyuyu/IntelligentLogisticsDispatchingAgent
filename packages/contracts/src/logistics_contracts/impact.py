"""Impact/reschedule boundary boundary projections (P14)."""

from __future__ import annotations

from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, StrictInt

from logistics_contracts.common import EntityRefDTO
from logistics_contracts.events import EventEnvelopeDTO
from logistics_contracts.planning import Record, RouteStopDTO, TransportPlanDTO
from logistics_contracts.runtime import ExecutionLocationDTO
from logistics_domain import impact as domain


class ImpactReasonPathDTO(Record):
    domain_type = domain.ImpactReasonPath
    code: str
    entity_refs: tuple[EntityRefDTO, ...]
    message: str


class ImpactReportDTO(Record):
    domain_type = domain.ImpactReport
    event_ids: tuple[UUID, ...]
    affected_orders: tuple[UUID, ...]
    affected_tasks: tuple[UUID, ...]
    affected_resources: tuple[UUID, ...]
    reason_paths: tuple[ImpactReasonPathDTO, ...]


class VirtualStartDTO(Record):
    domain_type = domain.VirtualStart
    task_id: UUID
    location: ExecutionLocationDTO
    start_s: StrictInt


class ResidualLoadDTO(Record):
    domain_type = domain.ResidualLoad
    cargo_id: UUID
    weight_g: StrictInt
    volume_cm3: StrictInt


class ResourceBlockDTO(Record):
    domain_type = domain.ResourceBlock
    resource_id: UUID
    start_s: StrictInt
    end_s: StrictInt


class RescheduleBoundaryDTO(Record):
    domain_type = domain.RescheduleBoundary
    event_time_s: StrictInt
    frozen_task_ids: tuple[UUID, ...]
    interrupted_task_ids: tuple[UUID, ...]
    virtual_starts: tuple[VirtualStartDTO, ...]
    residual_loads: tuple[ResidualLoadDTO, ...]
    resource_blocks: tuple[ResourceBlockDTO, ...]
    mutable_task_ids: tuple[UUID, ...]
    immutable_hash: str


class ImpactRequestDTO(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    schema_version: Literal["2.0.0"] = "2.0.0"
    event: EventEnvelopeDTO
    plan: TransportPlanDTO
    stops: tuple[RouteStopDTO, ...]
    event_time_s: StrictInt


class ImpactAnalysisDTO(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    schema_version: Literal["2.0.0"] = "2.0.0"
    report: ImpactReportDTO
    boundary: RescheduleBoundaryDTO
