"""Execution-time pure values (P02-04).

The frozen contract makes this module the single home of the ten ``EventPayload`` branches,
``ExecutionLocation``, ``TwinState``, ``PendingEvent``, ``RngState`` and ``ExecutionSnapshot``.
Later simulation tasks (P11–P13) map their requests onto these values; they do not define a
second copy. ``runtime.py`` imports this module one way only — this module must never import
``runtime``.

All times are integer seconds relative to the scenario/snapshot epoch; occupancy is
``[start_s, end_s)``. No framework, ORM, solver or Pydantic import is allowed here.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, fields
from datetime import datetime
from enum import StrEnum
from typing import Final, Literal, TypeAlias
from uuid import UUID

from logistics_domain.errors import InvalidInputError
from logistics_domain.planning import (
    InventoryEntry,
    PlanningScope,
    ResourceRevision,
    canonical_bytes,
    content_hash,
)
from logistics_domain.primitives import (
    EntityRef,
    Load,
    Rational,
    TimeWindow,
    require_int,
    require_non_negative_int,
    require_positive_int,
    require_sha256,
    require_utc_seconds,
    require_uuid,
)
from logistics_domain.states import (
    CargoCondition,
    EntityKind,
    EntityState,
    ReturnPolicy,
    WeatherProfile,
)

__all__ = [
    "ArcRef",
    "AtNodeLocation",
    "CargoAnomalyPayload",
    "CargoExecution",
    "DemandDecreasePayload",
    "DemandIncreasePayload",
    "EquipmentFailurePayload",
    "EventKind",
    "EventPayload",
    "ExecutionEvent",
    "ExecutionEventPayload",
    "ExecutionLocation",
    "ExecutionSnapshot",
    "OnArcLocation",
    "OrderCancellationPayload",
    "OrderExecution",
    "PendingEvent",
    "RegionRef",
    "ResourceUsage",
    "RngState",
    "TwinState",
    "TrafficDisruptionPayload",
    "TransportDelayPayload",
    "VehicleExecution",
    "VehicleFailurePayload",
    "WarehouseExecution",
    "WarehouseResourceUnavailablePayload",
    "WeatherChangePayload",
]

#: Upper bound of a scenario horizon, reused as the absolute event-time ceiling.
HORIZON_MAX_S: Final[int] = 604800

#: ``entity_ref.kind`` each payload branch is allowed to address (N01-R02 table).
_EVENT_REF_KINDS: Final[dict[str, frozenset[EntityKind]]] = {
    "vehicle_failure": frozenset({EntityKind.VEHICLE}),
    "transport_delay": frozenset({EntityKind.TRANSPORT_TASK}),
    "traffic_disruption": frozenset({EntityKind.TRAVEL_MATRIX}),
    "weather_change": frozenset({EntityKind.REGION}),
    "cargo_anomaly": frozenset({EntityKind.CARGO}),
    "order_cancellation": frozenset({EntityKind.ORDER}),
    "demand_increase": frozenset({EntityKind.ORDER}),
    "demand_decrease": frozenset({EntityKind.ORDER}),
    "equipment_failure": frozenset({EntityKind.EQUIPMENT}),
    "warehouse_resource_unavailable": frozenset(
        {EntityKind.WAREHOUSE, EntityKind.WAREHOUSE_ZONE, EntityKind.STORAGE_LOCATION,
         EntityKind.DOCK, EntityKind.WORKER, EntityKind.EQUIPMENT}
    ),
}


class EventKind(StrEnum):
    """The ten closed execution-event kinds; the value is the payload discriminator."""

    VEHICLE_FAILURE = "vehicle_failure"
    TRANSPORT_DELAY = "transport_delay"
    TRAFFIC_DISRUPTION = "traffic_disruption"
    WEATHER_CHANGE = "weather_change"
    CARGO_ANOMALY = "cargo_anomaly"
    ORDER_CANCELLATION = "order_cancellation"
    DEMAND_INCREASE = "demand_increase"
    DEMAND_DECREASE = "demand_decrease"
    EQUIPMENT_FAILURE = "equipment_failure"
    WAREHOUSE_RESOURCE_UNAVAILABLE = "warehouse_resource_unavailable"


@dataclass(frozen=True, slots=True)
class AtNodeLocation:
    """Vehicle/asset is exactly at a business node."""

    kind: Literal["at_node"]
    node_id: UUID

    def __post_init__(self) -> None:
        if self.kind != "at_node":
            raise InvalidInputError("AtNodeLocation.kind must be 'at_node'")
        require_uuid(self.node_id, field="AtNodeLocation.node_id")


@dataclass(frozen=True, slots=True)
class OnArcLocation:
    """Vehicle is mid-arc; progress is an exact non-negative rational on ``[0,1]``."""

    kind: Literal["on_arc"]
    from_node_id: UUID
    to_node_id: UUID
    departed_at_s: int
    expected_arrival_s: int
    progress_numerator: int
    progress_denominator: int

    def __post_init__(self) -> None:
        if self.kind != "on_arc":
            raise InvalidInputError("OnArcLocation.kind must be 'on_arc'")
        require_uuid(self.from_node_id, field="OnArcLocation.from_node_id")
        require_uuid(self.to_node_id, field="OnArcLocation.to_node_id")
        if self.from_node_id == self.to_node_id:
            raise InvalidInputError("OnArcLocation requires two distinct endpoints")
        require_non_negative_int(self.departed_at_s, field="OnArcLocation.departed_at_s")
        require_non_negative_int(self.expected_arrival_s, field="OnArcLocation.expected_arrival_s")
        if self.departed_at_s >= self.expected_arrival_s:
            raise InvalidInputError("OnArcLocation requires departed_at_s < expected_arrival_s")
        require_non_negative_int(self.progress_numerator, field="OnArcLocation.progress_numerator")
        require_positive_int(self.progress_denominator, field="OnArcLocation.progress_denominator")
        if self.progress_numerator > self.progress_denominator:
            raise InvalidInputError("OnArcLocation progress must stay within [0, 1]")


ExecutionLocation: TypeAlias = AtNodeLocation | OnArcLocation


@dataclass(frozen=True, slots=True)
class ArcRef:
    """Directed arc identity inside one referenced travel matrix."""

    from_node_id: UUID
    to_node_id: UUID

    def __post_init__(self) -> None:
        require_uuid(self.from_node_id, field="ArcRef.from_node_id")
        require_uuid(self.to_node_id, field="ArcRef.to_node_id")
        if self.from_node_id == self.to_node_id:
            raise InvalidInputError("ArcRef must not be a self loop")


@dataclass(frozen=True, slots=True)
class RegionRef:
    """Explicit node group used by weather impact; never a guessed geographic region."""

    region_id: UUID
    node_ids: tuple[UUID, ...]

    def __post_init__(self) -> None:
        require_uuid(self.region_id, field="RegionRef.region_id")
        if not isinstance(self.node_ids, tuple) or not self.node_ids:
            raise InvalidInputError("RegionRef.node_ids must be a nonempty tuple")
        seen: set[UUID] = set()
        for index, node_id in enumerate(self.node_ids):
            require_uuid(node_id, field=f"RegionRef.node_ids[{index}]")
            if node_id in seen:
                raise InvalidInputError("RegionRef.node_ids must be unique")
            seen.add(node_id)


def _validate_event_common(kind: str, entity_ref: EntityRef, effective_at_s: int, reason: str) -> None:
    if not isinstance(entity_ref, EntityRef):
        raise InvalidInputError("event entity_ref must be an EntityRef")
    if entity_ref.kind not in _EVENT_REF_KINDS[kind]:
        raise InvalidInputError(
            f"{kind} entity_ref.kind must be one of "
            f"{sorted(member.value for member in _EVENT_REF_KINDS[kind])}")
    require_non_negative_int(effective_at_s, field=f"{kind}.effective_at_s")
    if effective_at_s > HORIZON_MAX_S:
        raise InvalidInputError(f"{kind}.effective_at_s exceeds the frozen horizon maximum")
    if not isinstance(reason, str) or not 1 <= len(reason) <= 256:
        raise InvalidInputError(f"{kind}.reason must be 1..256 safe characters")


@dataclass(frozen=True, slots=True)
class VehicleFailurePayload:
    """Vehicle becomes unavailable at a known location."""

    kind: Literal["vehicle_failure"]
    entity_ref: EntityRef
    effective_at_s: int
    reason: str
    vehicle_id: UUID
    location: ExecutionLocation
    unavailable_until_s: int | None
    cargo_condition: CargoCondition

    def __post_init__(self) -> None:
        if self.kind != "vehicle_failure":
            raise InvalidInputError("invalid vehicle_failure discriminator")
        _validate_event_common("vehicle_failure", self.entity_ref, self.effective_at_s, self.reason)
        if self.entity_ref.id != self.vehicle_id:
            raise InvalidInputError("vehicle_failure entity_ref.id must equal vehicle_id")
        require_uuid(self.vehicle_id, field="VehicleFailurePayload.vehicle_id")
        if not isinstance(self.location, (AtNodeLocation, OnArcLocation)):
            raise InvalidInputError("VehicleFailurePayload.location must be an ExecutionLocation")
        if self.unavailable_until_s is not None:
            require_non_negative_int(self.unavailable_until_s, field="unavailable_until_s")
            if self.unavailable_until_s < self.effective_at_s:
                raise InvalidInputError("unavailable_until_s must not precede effective_at_s")
        if not isinstance(self.cargo_condition, CargoCondition):
            raise InvalidInputError("VehicleFailurePayload.cargo_condition must be a CargoCondition")


@dataclass(frozen=True, slots=True)
class TransportDelayPayload:
    """A transport task gains a strictly positive delay."""

    kind: Literal["transport_delay"]
    entity_ref: EntityRef
    effective_at_s: int
    reason: str
    transport_task_id: UUID
    additional_seconds: int

    def __post_init__(self) -> None:
        if self.kind != "transport_delay":
            raise InvalidInputError("invalid transport_delay discriminator")
        _validate_event_common("transport_delay", self.entity_ref, self.effective_at_s, self.reason)
        if self.entity_ref.id != self.transport_task_id:
            raise InvalidInputError("transport_delay entity_ref.id must equal transport_task_id")
        require_uuid(self.transport_task_id, field="TransportDelayPayload.transport_task_id")
        require_positive_int(self.additional_seconds, field="additional_seconds")


@dataclass(frozen=True, slots=True)
class TrafficDisruptionPayload:
    """One or more directed arcs are closed or slowed; a new matrix version is required."""

    kind: Literal["traffic_disruption"]
    entity_ref: EntityRef
    effective_at_s: int
    reason: str
    arc_refs: tuple[ArcRef, ...]
    closure: bool
    travel_multiplier: Rational | None
    new_matrix_version: int

    def __post_init__(self) -> None:
        if self.kind != "traffic_disruption":
            raise InvalidInputError("invalid traffic_disruption discriminator")
        _validate_event_common("traffic_disruption", self.entity_ref, self.effective_at_s, self.reason)
        if not isinstance(self.arc_refs, tuple) or not self.arc_refs:
            raise InvalidInputError("traffic_disruption.arc_refs must be a nonempty tuple")
        seen: set[tuple[UUID, UUID]] = set()
        for index, arc in enumerate(self.arc_refs):
            if not isinstance(arc, ArcRef):
                raise InvalidInputError(f"arc_refs[{index}] must be an ArcRef")
            key = (arc.from_node_id, arc.to_node_id)
            if key in seen:
                raise InvalidInputError("traffic_disruption repeats a directed arc")
            seen.add(key)
        if not isinstance(self.closure, bool):
            raise InvalidInputError("traffic_disruption.closure must be a bool")
        if self.closure:
            if self.travel_multiplier is not None:
                raise InvalidInputError("a closed arc cannot carry a travel multiplier")
        else:
            if not isinstance(self.travel_multiplier, Rational):
                raise InvalidInputError("an open disruption requires a positive rational multiplier")
        require_positive_int(self.new_matrix_version, field="new_matrix_version")
        if self.entity_ref.revision is None:
            raise InvalidInputError("traffic_disruption entity_ref.revision must name the matrix version")
        if self.new_matrix_version <= self.entity_ref.revision:
            raise InvalidInputError("new_matrix_version must exceed the referenced matrix version")


@dataclass(frozen=True, slots=True)
class WeatherChangePayload:
    """Weather profile changes over an explicit region and a new matrix version is emitted."""

    kind: Literal["weather_change"]
    entity_ref: EntityRef
    effective_at_s: int
    reason: str
    region_ref: RegionRef
    profile: WeatherProfile
    travel_multiplier: Rational
    new_matrix_version: int

    def __post_init__(self) -> None:
        if self.kind != "weather_change":
            raise InvalidInputError("invalid weather_change discriminator")
        _validate_event_common("weather_change", self.entity_ref, self.effective_at_s, self.reason)
        if self.entity_ref.revision is not None:
            raise InvalidInputError("weather_change region references carry no row revision")
        if not isinstance(self.region_ref, RegionRef):
            raise InvalidInputError("weather_change.region_ref must be a RegionRef")
        if self.entity_ref.id != self.region_ref.region_id:
            raise InvalidInputError("weather_change entity_ref.id must equal region_ref.region_id")
        if not isinstance(self.profile, WeatherProfile):
            raise InvalidInputError("weather_change.profile must be a WeatherProfile")
        if not isinstance(self.travel_multiplier, Rational):
            raise InvalidInputError("weather_change.travel_multiplier must be a Rational")
        require_positive_int(self.new_matrix_version, field="new_matrix_version")


@dataclass(frozen=True, slots=True)
class CargoAnomalyPayload:
    """Cargo condition change with an exact affected quantity."""

    kind: Literal["cargo_anomaly"]
    entity_ref: EntityRef
    effective_at_s: int
    reason: str
    cargo_id: UUID
    condition: CargoCondition
    quantity_units: int
    measured_temp_decic: int | None

    def __post_init__(self) -> None:
        if self.kind != "cargo_anomaly":
            raise InvalidInputError("invalid cargo_anomaly discriminator")
        _validate_event_common("cargo_anomaly", self.entity_ref, self.effective_at_s, self.reason)
        if self.entity_ref.id != self.cargo_id:
            raise InvalidInputError("cargo_anomaly entity_ref.id must equal cargo_id")
        require_uuid(self.cargo_id, field="cargo_anomaly.cargo_id")
        if not isinstance(self.condition, CargoCondition) or self.condition == CargoCondition.INTACT:
            raise InvalidInputError("cargo_anomaly.condition must be a non-intact CargoCondition")
        require_positive_int(self.quantity_units, field="cargo_anomaly.quantity_units")
        if self.condition == CargoCondition.TEMPERATURE_EXCURSION:
            if self.measured_temp_decic is None:
                raise InvalidInputError("temperature_excursion requires measured_temp_decic")
            require_int(self.measured_temp_decic, field="measured_temp_decic")
        elif self.measured_temp_decic is not None:
            raise InvalidInputError("measured_temp_decic is only valid for temperature_excursion")


@dataclass(frozen=True, slots=True)
class OrderCancellationPayload:
    """Order cancellation with an explicit disposition policy."""

    kind: Literal["order_cancellation"]
    entity_ref: EntityRef
    effective_at_s: int
    reason: str
    order_id: UUID
    disposition_policy: ReturnPolicy

    def __post_init__(self) -> None:
        if self.kind != "order_cancellation":
            raise InvalidInputError("invalid order_cancellation discriminator")
        _validate_event_common("order_cancellation", self.entity_ref, self.effective_at_s, self.reason)
        if self.entity_ref.id != self.order_id:
            raise InvalidInputError("order_cancellation entity_ref.id must equal order_id")
        require_uuid(self.order_id, field="order_cancellation.order_id")
        if not isinstance(self.disposition_policy, ReturnPolicy):
            raise InvalidInputError("order_cancellation.disposition_policy must be a ReturnPolicy")


@dataclass(frozen=True, slots=True)
class DemandIncreasePayload:
    """Demand increase; all deltas are strictly positive."""

    kind: Literal["demand_increase"]
    entity_ref: EntityRef
    effective_at_s: int
    reason: str
    order_id: UUID
    delta_quantity: int
    delta_weight_g: int
    delta_volume_cm3: int

    def __post_init__(self) -> None:
        if self.kind != "demand_increase":
            raise InvalidInputError("invalid demand_increase discriminator")
        _validate_event_common("demand_increase", self.entity_ref, self.effective_at_s, self.reason)
        if self.entity_ref.id != self.order_id:
            raise InvalidInputError("demand_increase entity_ref.id must equal order_id")
        require_uuid(self.order_id, field="demand_increase.order_id")
        for name in ("delta_quantity", "delta_weight_g", "delta_volume_cm3"):
            require_positive_int(getattr(self, name), field=f"demand_increase.{name}")


@dataclass(frozen=True, slots=True)
class DemandDecreasePayload:
    """Demand decrease; the delta is positive, the applied total must not go negative."""

    kind: Literal["demand_decrease"]
    entity_ref: EntityRef
    effective_at_s: int
    reason: str
    order_id: UUID
    delta_quantity: int
    delta_weight_g: int
    delta_volume_cm3: int

    def __post_init__(self) -> None:
        if self.kind != "demand_decrease":
            raise InvalidInputError("invalid demand_decrease discriminator")
        _validate_event_common("demand_decrease", self.entity_ref, self.effective_at_s, self.reason)
        if self.entity_ref.id != self.order_id:
            raise InvalidInputError("demand_decrease entity_ref.id must equal order_id")
        require_uuid(self.order_id, field="demand_decrease.order_id")
        for name in ("delta_quantity", "delta_weight_g", "delta_volume_cm3"):
            require_positive_int(getattr(self, name), field=f"demand_decrease.{name}")


@dataclass(frozen=True, slots=True)
class EquipmentFailurePayload:
    """Equipment capacity drops to a known remaining amount."""

    kind: Literal["equipment_failure"]
    entity_ref: EntityRef
    effective_at_s: int
    reason: str
    equipment_id: UUID
    unavailable_until_s: int | None
    remaining_capacity_units: int

    def __post_init__(self) -> None:
        if self.kind != "equipment_failure":
            raise InvalidInputError("invalid equipment_failure discriminator")
        _validate_event_common("equipment_failure", self.entity_ref, self.effective_at_s, self.reason)
        if self.entity_ref.id != self.equipment_id:
            raise InvalidInputError("equipment_failure entity_ref.id must equal equipment_id")
        require_uuid(self.equipment_id, field="equipment_failure.equipment_id")
        if self.unavailable_until_s is not None:
            require_non_negative_int(self.unavailable_until_s, field="unavailable_until_s")
            if self.unavailable_until_s < self.effective_at_s:
                raise InvalidInputError("unavailable_until_s must not precede effective_at_s")
        require_non_negative_int(self.remaining_capacity_units, field="remaining_capacity_units")


@dataclass(frozen=True, slots=True)
class WarehouseResourceUnavailablePayload:
    """A warehouse resource loses capacity during a closed start window."""

    kind: Literal["warehouse_resource_unavailable"]
    entity_ref: EntityRef
    effective_at_s: int
    reason: str
    resource_ref: EntityRef
    unavailable_window: TimeWindow
    remaining_capacity_units: int

    def __post_init__(self) -> None:
        if self.kind != "warehouse_resource_unavailable":
            raise InvalidInputError("invalid warehouse_resource_unavailable discriminator")
        _validate_event_common("warehouse_resource_unavailable", self.entity_ref,
                               self.effective_at_s, self.reason)
        if not isinstance(self.resource_ref, EntityRef):
            raise InvalidInputError("warehouse_resource_unavailable.resource_ref must be an EntityRef")
        if (self.entity_ref.kind, self.entity_ref.id, self.entity_ref.revision) != (
                self.resource_ref.kind, self.resource_ref.id, self.resource_ref.revision):
            raise InvalidInputError("entity_ref and resource_ref must be identical")
        if not isinstance(self.unavailable_window, TimeWindow):
            raise InvalidInputError("unavailable_window must be a TimeWindow")
        require_non_negative_int(self.remaining_capacity_units, field="remaining_capacity_units")


EventPayload: TypeAlias = (
    VehicleFailurePayload
    | TransportDelayPayload
    | TrafficDisruptionPayload
    | WeatherChangePayload
    | CargoAnomalyPayload
    | OrderCancellationPayload
    | DemandIncreasePayload
    | DemandDecreasePayload
    | EquipmentFailurePayload
    | WarehouseResourceUnavailablePayload
)

#: Contract synonym used by ``PendingEvent``; the concrete union is the same object.
ExecutionEventPayload: TypeAlias = EventPayload


@dataclass(frozen=True, slots=True)
class ExecutionEvent:
    """An event applied to the digital twin at a relative second."""

    event_id: UUID
    kind: EventKind
    occurred_at_s: int
    payload: EventPayload

    def __post_init__(self) -> None:
        require_uuid(self.event_id, field="ExecutionEvent.event_id")
        if not isinstance(self.kind, EventKind):
            raise InvalidInputError("ExecutionEvent.kind must be an EventKind")
        require_non_negative_int(self.occurred_at_s, field="ExecutionEvent.occurred_at_s")
        if not isinstance(self.payload, (VehicleFailurePayload, TransportDelayPayload,
                                         TrafficDisruptionPayload, WeatherChangePayload,
                                         CargoAnomalyPayload, OrderCancellationPayload,
                                         DemandIncreasePayload, DemandDecreasePayload,
                                         EquipmentFailurePayload,
                                         WarehouseResourceUnavailablePayload)):
            raise InvalidInputError("ExecutionEvent.payload must be one of the ten payloads")
        if self.kind.value != self.payload.kind:
            raise InvalidInputError("ExecutionEvent.kind must equal payload.kind")


@dataclass(frozen=True, slots=True)
class PendingEvent:
    """Deterministic event-queue entry: time, priority, insertion order."""

    event_id: UUID
    time_s: int
    priority: int
    insertion_seq: int
    payload: EventPayload

    def __post_init__(self) -> None:
        require_uuid(self.event_id, field="PendingEvent.event_id")
        require_non_negative_int(self.time_s, field="PendingEvent.time_s")
        require_non_negative_int(self.priority, field="PendingEvent.priority")
        require_non_negative_int(self.insertion_seq, field="PendingEvent.insertion_seq")
        if not isinstance(self.payload, (VehicleFailurePayload, TransportDelayPayload,
                                         TrafficDisruptionPayload, WeatherChangePayload,
                                         CargoAnomalyPayload, OrderCancellationPayload,
                                         DemandIncreasePayload, DemandDecreasePayload,
                                         EquipmentFailurePayload,
                                         WarehouseResourceUnavailablePayload)):
            raise InvalidInputError("PendingEvent.payload must be one of the ten payloads")


@dataclass(frozen=True, slots=True)
class RngState:
    """One named deterministic RNG stream snapshot; never a pickled generator."""

    stream_name: str
    algorithm_version: str
    state: int
    draw_count: int

    def __post_init__(self) -> None:
        for name in ("stream_name", "algorithm_version"):
            value = getattr(self, name)
            if not isinstance(value, str) or not 1 <= len(value) <= 64:
                raise InvalidInputError(f"RngState.{name} must be 1..64 characters")
        require_non_negative_int(self.state, field="RngState.state")
        require_non_negative_int(self.draw_count, field="RngState.draw_count")


@dataclass(frozen=True, slots=True)
class CargoExecution:
    """Physical cargo fact inside the twin."""

    cargo_id: UUID
    location_id: UUID | None
    quantity_units: int
    condition: CargoCondition
    uncontrolled_exposure_s: int

    def __post_init__(self) -> None:
        require_uuid(self.cargo_id, field="CargoExecution.cargo_id")
        if self.location_id is not None:
            require_uuid(self.location_id, field="CargoExecution.location_id")
        require_non_negative_int(self.quantity_units, field="CargoExecution.quantity_units")
        if not isinstance(self.condition, CargoCondition):
            raise InvalidInputError("CargoExecution.condition must be a CargoCondition")
        require_non_negative_int(self.uncontrolled_exposure_s,
                                 field="CargoExecution.uncontrolled_exposure_s")


@dataclass(frozen=True, slots=True)
class OrderExecution:
    """Order fact projection inside the twin."""

    order_id: UUID
    status: EntityState
    cargo_ids: tuple[UUID, ...]

    def __post_init__(self) -> None:
        require_uuid(self.order_id, field="OrderExecution.order_id")
        if not isinstance(self.status, EntityState):
            raise InvalidInputError("OrderExecution.status must be an EntityState")
        if not isinstance(self.cargo_ids, tuple) or not self.cargo_ids:
            raise InvalidInputError("OrderExecution.cargo_ids must be a nonempty tuple")
        if len(set(self.cargo_ids)) != len(self.cargo_ids):
            raise InvalidInputError("OrderExecution.cargo_ids must be unique")
        for index, cargo_id in enumerate(self.cargo_ids):
            require_uuid(cargo_id, field=f"OrderExecution.cargo_ids[{index}]")


@dataclass(frozen=True, slots=True)
class VehicleExecution:
    """Vehicle fact projection inside the twin."""

    vehicle_id: UUID
    status: EntityState
    location: ExecutionLocation
    driver_id: UUID | None
    load: Load

    def __post_init__(self) -> None:
        require_uuid(self.vehicle_id, field="VehicleExecution.vehicle_id")
        if not isinstance(self.status, EntityState):
            raise InvalidInputError("VehicleExecution.status must be an EntityState")
        if not isinstance(self.location, (AtNodeLocation, OnArcLocation)):
            raise InvalidInputError("VehicleExecution.location must be an ExecutionLocation")
        if self.driver_id is not None:
            require_uuid(self.driver_id, field="VehicleExecution.driver_id")
        if not isinstance(self.load, Load):
            raise InvalidInputError("VehicleExecution.load must be a Load")


@dataclass(frozen=True, slots=True)
class ResourceUsage:
    """Cumulative resource usage over a half-open interval."""

    resource_id: UUID
    used_units: int
    start_s: int
    end_s: int

    def __post_init__(self) -> None:
        require_uuid(self.resource_id, field="ResourceUsage.resource_id")
        require_non_negative_int(self.used_units, field="ResourceUsage.used_units")
        require_non_negative_int(self.start_s, field="ResourceUsage.start_s")
        require_non_negative_int(self.end_s, field="ResourceUsage.end_s")
        if self.start_s >= self.end_s:
            raise InvalidInputError("ResourceUsage requires start_s < end_s")


@dataclass(frozen=True, slots=True)
class WarehouseExecution:
    """Warehouse fact projection inside the twin."""

    warehouse_id: UUID
    status: EntityState
    resource_usage: tuple[ResourceUsage, ...]

    def __post_init__(self) -> None:
        require_uuid(self.warehouse_id, field="WarehouseExecution.warehouse_id")
        if not isinstance(self.status, EntityState):
            raise InvalidInputError("WarehouseExecution.status must be an EntityState")
        if not isinstance(self.resource_usage, tuple):
            raise InvalidInputError("WarehouseExecution.resource_usage must be a tuple")
        for index, usage in enumerate(self.resource_usage):
            if not isinstance(usage, ResourceUsage):
                raise InvalidInputError(f"resource_usage[{index}] must be a ResourceUsage")


@dataclass(frozen=True, slots=True)
class TwinState:
    """Complete execution fact state at one simulation second."""

    time_s: int
    orders: tuple[OrderExecution, ...]
    vehicles: tuple[VehicleExecution, ...]
    warehouses: tuple[WarehouseExecution, ...]
    inventory: tuple[InventoryEntry, ...]
    resource_usage: tuple[ResourceUsage, ...]
    last_event_seq: int

    def __post_init__(self) -> None:
        require_non_negative_int(self.time_s, field="TwinState.time_s")
        for name, expected in (("orders", OrderExecution), ("vehicles", VehicleExecution),
                               ("warehouses", WarehouseExecution), ("inventory", InventoryEntry),
                               ("resource_usage", ResourceUsage)):
            value = getattr(self, name)
            if not isinstance(value, tuple):
                raise InvalidInputError(f"TwinState.{name} must be a tuple")
            for index, item in enumerate(value):
                if not isinstance(item, expected):
                    raise InvalidInputError(f"TwinState.{name}[{index}] must be {expected.__name__}")
        require_non_negative_int(self.last_event_seq, field="TwinState.last_event_seq")
        for name in ("orders", "vehicles", "warehouses"):
            ids = [getattr(item, f"{name[:-1]}_id") for item in getattr(self, name)]
            if len(set(ids)) != len(ids):
                raise InvalidInputError(f"TwinState.{name} must have unique ids")


def twin_state_hash(state: TwinState) -> str:
    """Canonical hash of a twin state, used by simulation snapshots."""
    return hashlib.sha256(canonical_bytes(state)).hexdigest()


@dataclass(frozen=True, slots=True)
class ExecutionSnapshot:
    """Immutable execution fact snapshot at one instant."""

    id: UUID
    status: Literal["recorded"]
    created_at: datetime
    updated_at: datetime
    row_version: int
    schema_version: Literal["2.0.0"]
    created_by: UUID
    time_s: int
    state: TwinState
    source_version_id: UUID
    revisions: tuple[ResourceRevision, ...]
    content_hash: str

    def __post_init__(self) -> None:
        require_uuid(self.id, field="ExecutionSnapshot.id")
        if self.status != "recorded":
            raise InvalidInputError("ExecutionSnapshot.status must be 'recorded'")
        require_utc_seconds(self.created_at, field="ExecutionSnapshot.created_at")
        require_utc_seconds(self.updated_at, field="ExecutionSnapshot.updated_at")
        if self.updated_at != self.created_at:
            raise InvalidInputError("a recorded snapshot keeps created_at == updated_at")
        require_non_negative_int(self.row_version, field="ExecutionSnapshot.row_version")
        if self.row_version != 0:
            raise InvalidInputError("a recorded snapshot starts at row_version 0")
        if self.schema_version != "2.0.0":
            raise InvalidInputError("ExecutionSnapshot.schema_version must be 2.0.0")
        require_uuid(self.created_by, field="ExecutionSnapshot.created_by")
        require_non_negative_int(self.time_s, field="ExecutionSnapshot.time_s")
        if not isinstance(self.state, TwinState):
            raise InvalidInputError("ExecutionSnapshot.state must be a TwinState")
        if self.state.time_s != self.time_s:
            raise InvalidInputError("ExecutionSnapshot.time_s must equal state.time_s")
        require_uuid(self.source_version_id, field="ExecutionSnapshot.source_version_id")
        if not isinstance(self.revisions, tuple):
            raise InvalidInputError("ExecutionSnapshot.revisions must be a tuple")
        for index, revision in enumerate(self.revisions):
            if not isinstance(revision, ResourceRevision):
                raise InvalidInputError(f"revisions[{index}] must be a ResourceRevision")
        require_sha256(self.content_hash, field="ExecutionSnapshot.content_hash")
        expected = content_hash({field.name: getattr(self, field.name)
                                 for field in fields(self)
                                 if field.name not in ("content_hash", "id")})
        if expected != self.content_hash:
            raise InvalidInputError("ExecutionSnapshot.content_hash does not match its content")
