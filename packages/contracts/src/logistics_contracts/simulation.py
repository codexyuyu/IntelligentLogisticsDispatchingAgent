"""Simulation boundary projections (P11-01)."""

from __future__ import annotations

from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, StrictInt

from logistics_contracts.planning import (
    Record,
    RouteStopDTO,
    TransportPlanDTO,
)
from logistics_domain import simulation as domain


class SimulationEventDTO(Record):
    domain_type = domain.SimulationEvent
    event_id: UUID
    time_s: StrictInt
    kind: domain.SimulationEventKind
    vehicle_id: UUID | None
    order_id: UUID | None
    stop_id: UUID | None


class SimulationRequestDTO(Record):
    domain_type = domain.SimulationRequest
    plan: TransportPlanDTO
    stops: tuple[RouteStopDTO, ...]
    seed: StrictInt
    until_s: StrictInt


class SimulationResultDTO(Record):
    domain_type = domain.SimulationResult
    status: domain.SimulationStatus
    final_time_s: StrictInt
    events: tuple[SimulationEventDTO, ...]
    delivered_order_ids: tuple[UUID, ...]
    seed: StrictInt


class SimulationView(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    schema_version: Literal["2.0.0"] = "2.0.0"
    simulation_id: UUID
    status: str
    final_time_s: StrictInt
