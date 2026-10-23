"""Simulation request/result values (P11-01 subset)."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from uuid import UUID

from logistics_domain.errors import InvalidInputError
from logistics_domain.planning import RouteStop, TransportPlan
from logistics_domain.primitives import require_non_negative_int, require_uuid

__all__ = [
    "SimulationEvent",
    "SimulationEventKind",
    "SimulationRequest",
    "SimulationResult",
    "SimulationStatus",
]


class SimulationStatus(StrEnum):
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    FAILED = "failed"


class SimulationEventKind(StrEnum):
    ARRIVAL = "arrival"
    SERVICE_START = "service_start"
    DEPARTURE = "departure"
    DELIVERED = "delivered"


@dataclass(frozen=True, slots=True)
class SimulationEvent:
    event_id: UUID
    time_s: int
    kind: SimulationEventKind
    vehicle_id: UUID | None
    order_id: UUID | None
    stop_id: UUID | None

    def __post_init__(self) -> None:
        require_uuid(self.event_id, field="SimulationEvent.event_id")
        require_non_negative_int(self.time_s, field="SimulationEvent.time_s")
        if not isinstance(self.kind, SimulationEventKind):
            raise InvalidInputError("SimulationEvent.kind must be SimulationEventKind")
        for name in ("vehicle_id", "order_id", "stop_id"):
            value = getattr(self, name)
            if value is not None:
                require_uuid(value, field=f"SimulationEvent.{name}")


@dataclass(frozen=True, slots=True)
class SimulationRequest:
    plan: TransportPlan
    stops: tuple[RouteStop, ...]
    seed: int
    until_s: int

    def __post_init__(self) -> None:
        if not isinstance(self.plan, TransportPlan):
            raise InvalidInputError("SimulationRequest.plan must be TransportPlan")
        if not isinstance(self.stops, tuple) or not self.stops:
            raise InvalidInputError("SimulationRequest.stops must be a nonempty tuple")
        route_ids = {route.id for route in self.plan.routes}
        for stop in self.stops:
            if not isinstance(stop, RouteStop):
                raise InvalidInputError("SimulationRequest.stops must contain RouteStop values")
            if stop.route_id not in route_ids:
                raise InvalidInputError("simulation stop references a route outside the plan")
        require_non_negative_int(self.seed, field="SimulationRequest.seed")
        require_non_negative_int(self.until_s, field="SimulationRequest.until_s")


@dataclass(frozen=True, slots=True)
class SimulationResult:
    status: SimulationStatus
    final_time_s: int
    events: tuple[SimulationEvent, ...]
    delivered_order_ids: tuple[UUID, ...]
    seed: int

    def __post_init__(self) -> None:
        if not isinstance(self.status, SimulationStatus):
            raise InvalidInputError("SimulationResult.status must be SimulationStatus")
        require_non_negative_int(self.final_time_s, field="SimulationResult.final_time_s")
        if not isinstance(self.events, tuple) or not isinstance(self.delivered_order_ids, tuple):
            raise InvalidInputError("SimulationResult events/delivered ids must be tuples")
        require_non_negative_int(self.seed, field="SimulationResult.seed")
