"""Resource vocabulary; see CHG-20261023-master-data-types."""

from enum import StrEnum
from dataclasses import dataclass
from typing import Literal, TypeAlias
from uuid import UUID

from logistics_domain.errors import InvalidInputError
from logistics_domain.orders import Cargo, CargoType, Entity
from logistics_domain.primitives import ResourceCalendar, TimeWindow, require_non_negative_int, require_positive_int, require_sha256


class Qualification(str):
    """Exact master-data qualification code, not a legal certification claim."""

    def __new__(cls, value: str) -> "Qualification":
        if not isinstance(value, str) or not value or value != value.strip():
            raise InvalidInputError("Qualification requires a nonempty, unpadded code")
        return super().__new__(cls, value)


class Skill(str):
    """Exact master-data skill code; no implicit operation authorization."""

    def __new__(cls, value: str) -> "Skill":
        if not isinstance(value, str) or not value or value != value.strip():
            raise InvalidInputError("Skill requires a nonempty, unpadded code")
        return super().__new__(cls, value)


class OperationKind(StrEnum):
    RECEIVE = "receive"
    DISPATCH = "dispatch"
    SORT = "sort"
    LOAD = "load"
    UNLOAD = "unload"
    SETUP = "setup"


class EquipmentKind(StrEnum):
    SORTING = "sorting"
    HANDLING = "handling"


@dataclass(frozen=True, kw_only=True)
class Vehicle(Entity):
    lifecycle = "vehicle"
    code: str
    capacity_weight_g: int
    capacity_volume_cm3: int
    setpoint_decic: int
    allowed_cargo_types: tuple[CargoType, ...]
    start_node_id: UUID
    end_node_id: UUID
    calendar: ResourceCalendar
    driver_id: UUID | None
    fixed_cost_cents: int
    rate_cents_per_km: int

    def __post_init__(self) -> None:
        super().__post_init__()
        require_positive_int(self.capacity_weight_g, field="capacity_weight_g")
        require_positive_int(self.capacity_volume_cm3, field="capacity_volume_cm3")
        require_non_negative_int(self.fixed_cost_cents, field="fixed_cost_cents")
        require_non_negative_int(self.rate_cents_per_km, field="rate_cents_per_km")

    def can_carry(self, cargo: tuple[Cargo, ...]) -> bool:
        return (sum(c.weight_g for c in cargo) <= self.capacity_weight_g
                and sum(c.volume_cm3 for c in cargo) <= self.capacity_volume_cm3
                and all(c.cargo_type in self.allowed_cargo_types
                        and c.min_temp_decic <= self.setpoint_decic <= c.max_temp_decic for c in cargo))


@dataclass(frozen=True, kw_only=True)
class Driver(Entity):
    lifecycle = "driver"
    code: str
    qualifications: tuple[Qualification, ...]
    shift: TimeWindow
    max_drive_s: int
    max_work_s: int

    def __post_init__(self) -> None:
        super().__post_init__()
        require_positive_int(self.max_drive_s, field="max_drive_s")
        require_positive_int(self.max_work_s, field="max_work_s")
        if self.max_drive_s > self.max_work_s:
            raise InvalidInputError("drive limit exceeds work limit")


@dataclass(frozen=True, kw_only=True)
class Warehouse(Entity):
    lifecycle = "warehouse"
    code: str
    name: str
    node_id: UUID
    timezone: str
    calendar: ResourceCalendar


@dataclass(frozen=True, kw_only=True)
class WarehouseZone(Entity):
    lifecycle = "warehouse_zone"
    warehouse_id: UUID
    code: str
    setpoint_decic: int
    capacity_weight_g: int
    capacity_volume_cm3: int
    allowed_cargo_types: tuple[CargoType, ...]

    def __post_init__(self) -> None:
        super().__post_init__()
        require_non_negative_int(self.capacity_weight_g, field="capacity_weight_g")
        require_non_negative_int(self.capacity_volume_cm3, field="capacity_volume_cm3")


@dataclass(frozen=True, kw_only=True)
class StorageLocation(Entity):
    lifecycle = "storage_location"
    zone_id: UUID
    code: str
    capacity_weight_g: int
    capacity_volume_cm3: int
    calendar: ResourceCalendar

    def __post_init__(self) -> None:
        super().__post_init__()
        require_non_negative_int(self.capacity_weight_g, field="capacity_weight_g")
        require_non_negative_int(self.capacity_volume_cm3, field="capacity_volume_cm3")


@dataclass(frozen=True, kw_only=True)
class Dock(Entity):
    lifecycle = "dock"
    warehouse_id: UUID
    code: str
    supported_operations: tuple[OperationKind, ...]
    allowed_zone_ids: tuple[UUID, ...]
    calendar: ResourceCalendar


@dataclass(frozen=True, kw_only=True)
class Worker(Entity):
    lifecycle = "worker"
    warehouse_id: UUID
    skills: tuple[Skill, ...]
    allowed_zone_ids: tuple[UUID, ...]
    calendar: ResourceCalendar
    pool_id: UUID | None


@dataclass(frozen=True, kw_only=True)
class Equipment(Entity):
    lifecycle = "equipment"
    warehouse_id: UUID
    kind: EquipmentKind
    quantity_capacity: int
    allowed_zone_ids: tuple[UUID, ...]
    calendar: ResourceCalendar

    def __post_init__(self) -> None:
        super().__post_init__()
        require_positive_int(self.quantity_capacity, field="quantity_capacity")


@dataclass(frozen=True)
class ZoneResource:
    kind: Literal["zone"]
    value: WarehouseZone

    def __post_init__(self) -> None:
        if self.kind != "zone" or not isinstance(self.value, WarehouseZone):
            raise InvalidInputError("zone resource kind/value mismatch")


@dataclass(frozen=True)
class LocationResource:
    kind: Literal["location"]
    value: StorageLocation

    def __post_init__(self) -> None:
        if self.kind != "location" or not isinstance(self.value, StorageLocation):
            raise InvalidInputError("location resource kind/value mismatch")


@dataclass(frozen=True)
class DockResource:
    kind: Literal["dock"]
    value: Dock

    def __post_init__(self) -> None:
        if self.kind != "dock" or not isinstance(self.value, Dock):
            raise InvalidInputError("dock resource kind/value mismatch")


@dataclass(frozen=True)
class WorkerResource:
    kind: Literal["worker"]
    value: Worker

    def __post_init__(self) -> None:
        if self.kind != "worker" or not isinstance(self.value, Worker):
            raise InvalidInputError("worker resource kind/value mismatch")


@dataclass(frozen=True)
class EquipmentResource:
    kind: Literal["equipment"]
    value: Equipment

    def __post_init__(self) -> None:
        if self.kind != "equipment" or not isinstance(self.value, Equipment):
            raise InvalidInputError("equipment resource kind/value mismatch")


Resource: TypeAlias = ZoneResource | LocationResource | DockResource | WorkerResource | EquipmentResource


@dataclass(frozen=True)
class ResourceCalendarBinding:
    resource_id: UUID
    source_calendar: ResourceCalendar
    source_hash: str
    calendar: ResourceCalendar

    def __post_init__(self) -> None:
        require_sha256(self.source_hash, field="source_hash")
        if not isinstance(self.source_calendar, ResourceCalendar) or not isinstance(self.calendar, ResourceCalendar):
            raise InvalidInputError("calendar binding requires two ResourceCalendar values")
        # The projected calendar is a clipped/re-based view of the immutable source, so the
        # two are not required to be equal; both versions must agree with the source revision.
        if self.calendar.version != self.source_calendar.version:
            raise InvalidInputError("projected calendar version differs from its source")


@dataclass(frozen=True)
class ResourceBundle:
    warehouses: tuple[Warehouse, ...]
    zones: tuple[WarehouseZone, ...]
    locations: tuple[StorageLocation, ...]
    docks: tuple[Dock, ...]
    workers: tuple[Worker, ...]
    equipment: tuple[Equipment, ...]
    calendars: tuple[ResourceCalendarBinding, ...]

    def __post_init__(self) -> None:
        warehouses = {v.id for v in self.warehouses}
        zones = {v.id: v for v in self.zones}
        all_resources = (*self.warehouses, *self.zones, *self.locations, *self.docks, *self.workers, *self.equipment)
        if len({r.id for r in all_resources}) != len(all_resources):
            raise InvalidInputError("duplicate resource IDs")
        for resource in (*self.zones, *self.docks, *self.workers, *self.equipment):
            if resource.warehouse_id not in warehouses:
                raise InvalidInputError("unknown warehouse")
        if any(location.zone_id not in zones for location in self.locations):
            raise InvalidInputError("unknown location zone")
        for resource in (*self.docks, *self.workers, *self.equipment):
            if any(z not in zones or zones[z].warehouse_id != resource.warehouse_id for z in resource.allowed_zone_ids):
                raise InvalidInputError("zone outside resource warehouse")
        bindings = {b.resource_id: b for b in self.calendars}
        if len(bindings) != len(self.calendars):
            raise InvalidInputError("duplicate calendar binding")
        for resource in (*self.warehouses, *self.locations, *self.docks, *self.workers, *self.equipment):
            if resource.id not in bindings or bindings[resource.id].calendar != resource.calendar:
                raise InvalidInputError("missing or mismatched calendar binding")
