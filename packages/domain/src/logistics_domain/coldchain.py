"""R05 cold-chain snapshot types (ported from the partner contract).

The types are deliberately attached to a ``PlanningSnapshot`` as optional data. A
snapshot without them makes no cold-chain claim; it must not be interpreted as a
zero-exposure plan.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from uuid import UUID

from logistics_domain.errors import InvalidInputError
from logistics_domain.primitives import TimeWindow, require_non_negative_int, require_positive_int, require_uuid


class CapacityUnit(StrEnum):
    WEIGHT_G = "weight_g"
    VOLUME_CM3 = "volume_cm3"
    QUANTITY_UNITS = "quantity_units"


class ExposureScope(StrEnum):
    IN_WAREHOUSE = "in_warehouse"
    WAITING = "waiting"
    LOADING = "loading"
    TRANSPORT = "transport"


@dataclass(frozen=True, slots=True)
class CapacityAmount:
    unit: CapacityUnit
    amount: int

    def __post_init__(self) -> None:
        if not isinstance(self.unit, CapacityUnit):
            raise InvalidInputError("capacity unit must be CapacityUnit")
        require_non_negative_int(self.amount, field="capacity.amount")


def _capacities(values: tuple[CapacityAmount, ...]) -> None:
    if not isinstance(values, tuple) or not values:
        raise InvalidInputError("capacities must be a non-empty tuple")
    units = [item.unit for item in values]
    if len(set(units)) != len(units):
        raise InvalidInputError("capacity units must be unique")


@dataclass(frozen=True, slots=True)
class ColdChainZone:
    zone_id: UUID
    warehouse_id: UUID
    version: int
    setpoint_decic: int
    capacities: tuple[CapacityAmount, ...]

    def __post_init__(self) -> None:
        require_uuid(self.zone_id, field="coldchain.zone_id")
        require_uuid(self.warehouse_id, field="coldchain.zone.warehouse_id")
        require_positive_int(self.version, field="coldchain.zone.version")
        _capacities(self.capacities)


@dataclass(frozen=True, slots=True)
class ColdChainStorageLocation:
    location_id: UUID
    warehouse_id: UUID
    zone_id: UUID
    version: int
    capacities: tuple[CapacityAmount, ...]
    available_windows: tuple[TimeWindow, ...] = ()

    def __post_init__(self) -> None:
        for value, field in ((self.location_id, "location_id"), (self.warehouse_id, "warehouse_id"),
                              (self.zone_id, "zone_id")):
            require_uuid(value, field=f"coldchain.storage.{field}")
        require_positive_int(self.version, field="coldchain.storage.version")
        _capacities(self.capacities)
        if not isinstance(self.available_windows, tuple):
            raise InvalidInputError("available_windows must be a tuple")


@dataclass(frozen=True, slots=True)
class StorageOccupancy:
    occupancy_id: UUID
    batch_id: str
    location_id: UUID
    capacity_use: tuple[CapacityAmount, ...]
    origin: str
    inbound_operation_id: UUID | None = None
    outbound_operation_id: UUID | None = None
    declared_start_s: int | None = None

    def __post_init__(self) -> None:
        require_uuid(self.occupancy_id, field="coldchain.occupancy.occupancy_id")
        require_uuid(self.location_id, field="coldchain.occupancy.location_id")
        if not self.batch_id:
            raise InvalidInputError("occupancy batch_id required")
        _capacities(self.capacity_use)
        if self.origin not in ("initial_stock", "planned_inbound"):
            raise InvalidInputError("occupancy origin is invalid")
        for value in (self.inbound_operation_id, self.outbound_operation_id):
            if value is not None:
                require_uuid(value, field="coldchain.occupancy.operation_id")
        if self.origin == "initial_stock":
            if self.inbound_operation_id is not None:
                raise InvalidInputError("initial stock cannot have inbound operation")
            if self.declared_start_s not in (None, 0):
                raise InvalidInputError("initial stock starts at 0")
        elif self.inbound_operation_id is None and self.declared_start_s is None:
            raise InvalidInputError("planned inbound needs inbound operation or declared start")
        if self.declared_start_s is not None:
            require_non_negative_int(self.declared_start_s, field="occupancy.declared_start_s")


@dataclass(frozen=True, slots=True)
class ChangeoverRule:
    from_class: str
    to_class: str
    duration_s: int

    def __post_init__(self) -> None:
        if not self.from_class or not self.to_class or self.from_class == self.to_class:
            raise InvalidInputError("changeover classes must differ")
        require_non_negative_int(self.duration_s, field="changeover.duration_s")


@dataclass(frozen=True, slots=True)
class ColdChainSetupPolicy:
    policy_id: UUID
    version: str
    rule_version: str
    rendering: str
    rules: tuple[ChangeoverRule, ...]
    default_duration_s: int | None = None

    def __post_init__(self) -> None:
        require_uuid(self.policy_id, field="coldchain.setup.policy_id")
        if not self.version or not self.rule_version:
            raise InvalidInputError("setup policy version required")
        if self.rendering not in ("gap", "explicit_operation"):
            raise InvalidInputError("setup rendering is invalid")
        if not isinstance(self.rules, tuple) or any(not isinstance(v, ChangeoverRule) for v in self.rules):
            raise InvalidInputError("setup rules must be typed")
        pairs = [(rule.from_class, rule.to_class) for rule in self.rules]
        if len(set(pairs)) != len(pairs):
            raise InvalidInputError("setup rules must be unique")
        if self.default_duration_s is not None:
            require_non_negative_int(self.default_duration_s, field="setup.default_duration_s")


@dataclass(frozen=True, slots=True)
class PrecoolRequirement:
    requirement_id: UUID
    batch_id: str
    warehouse_id: UUID
    precool_operation_id: UUID
    loading_operation_ids: tuple[UUID, ...]
    min_duration_s: int
    target_zone: str
    eligible_resource_ids: tuple[UUID, ...]

    def __post_init__(self) -> None:
        for value, field in ((self.requirement_id, "requirement_id"),
                              (self.warehouse_id, "warehouse_id"),
                              (self.precool_operation_id, "precool_operation_id")):
            require_uuid(value, field=f"coldchain.precool.{field}")
        if not self.batch_id or not self.target_zone:
            raise InvalidInputError("precool batch/target zone required")
        require_positive_int(self.min_duration_s, field="precool.min_duration_s")
        for value in (*self.loading_operation_ids, *self.eligible_resource_ids):
            require_uuid(value, field="coldchain.precool.id")
        if not self.eligible_resource_ids:
            raise InvalidInputError("precool needs eligible resources")


@dataclass(frozen=True, slots=True)
class ExposureLimit:
    limit_id: UUID
    batch_id: str
    max_exposure_s: int
    scopes: tuple[ExposureScope, ...]
    rule_version: str
    source: str

    def __post_init__(self) -> None:
        require_uuid(self.limit_id, field="coldchain.exposure.limit_id")
        if not self.batch_id or not self.rule_version or not self.source:
            raise InvalidInputError("exposure limit metadata required")
        require_positive_int(self.max_exposure_s, field="exposure.max_exposure_s")
        if not isinstance(self.scopes, tuple) or not self.scopes:
            raise InvalidInputError("exposure scopes required")
        if len(set(self.scopes)) != len(self.scopes):
            raise InvalidInputError("exposure scopes must be unique")


@dataclass(frozen=True, slots=True)
class ExposureSegment:
    segment_id: UUID
    batch_id: str
    scope: ExposureScope
    start_s: int
    end_s: int
    source_kind: str

    def __post_init__(self) -> None:
        require_uuid(self.segment_id, field="coldchain.exposure.segment_id")
        if not self.batch_id:
            raise InvalidInputError("exposure segment batch required")
        if not isinstance(self.scope, ExposureScope):
            raise InvalidInputError("exposure segment scope invalid")
        require_non_negative_int(self.start_s, field="exposure.start_s")
        require_non_negative_int(self.end_s, field="exposure.end_s")
        if self.end_s <= self.start_s:
            raise InvalidInputError("exposure segment must have positive duration")
        if self.source_kind not in ("declared", "planned", "observed"):
            raise InvalidInputError("exposure source_kind invalid")


@dataclass(frozen=True, slots=True)
class BatchCompatibility:
    batch_id: str
    warehouse_id: UUID
    temperature_zone: str
    min_temperature_decic: int
    max_temperature_decic: int
    compatibility_class: str | None = None

    def __post_init__(self) -> None:
        if not self.batch_id or not self.temperature_zone:
            raise InvalidInputError("batch compatibility metadata required")
        require_uuid(self.warehouse_id, field="batch.warehouse_id")
        if self.min_temperature_decic > self.max_temperature_decic:
            raise InvalidInputError("batch temperature range invalid")


@dataclass(frozen=True, slots=True)
class CompatibilityPolicy:
    policy_id: UUID
    version: str
    rule_version: str
    incompatible_class_pairs: tuple[tuple[str, str], ...] = ()

    def __post_init__(self) -> None:
        require_uuid(self.policy_id, field="compatibility.policy_id")
        if not self.version or not self.rule_version:
            raise InvalidInputError("compatibility policy version required")
        seen = set()
        for left, right in self.incompatible_class_pairs:
            key = tuple(sorted((left, right)))
            if key in seen:
                raise InvalidInputError("incompatible class pairs must be unique")
            seen.add(key)


@dataclass(frozen=True, slots=True)
class ColdChainSnapshot:
    rule_version: str
    horizon_s: int
    zones: tuple[ColdChainZone, ...] = ()
    storage_locations: tuple[ColdChainStorageLocation, ...] = ()
    occupancies: tuple[StorageOccupancy, ...] = ()
    setup_policies: tuple[ColdChainSetupPolicy, ...] = ()
    precool_requirements: tuple[PrecoolRequirement, ...] = ()
    exposure_limits: tuple[ExposureLimit, ...] = ()
    batch_compatibility: tuple[BatchCompatibility, ...] = ()
    compatibility_policy: CompatibilityPolicy | None = None

    def __post_init__(self) -> None:
        if not self.rule_version:
            raise InvalidInputError("coldchain rule_version required")
        require_positive_int(self.horizon_s, field="coldchain.horizon_s")
        groups = (
            ("zones", self.zones, "zone_id"), ("storage_locations", self.storage_locations, "location_id"),
            ("occupancies", self.occupancies, "occupancy_id"), ("setup_policies", self.setup_policies, "policy_id"),
            ("precool_requirements", self.precool_requirements, "requirement_id"),
            ("exposure_limits", self.exposure_limits, "limit_id"),
            ("batch_compatibility", self.batch_compatibility, "batch_id"),
        )
        for name, values, key in groups:
            if not isinstance(values, tuple):
                raise InvalidInputError(f"coldchain.{name} must be a tuple")
            ids = [getattr(item, key) for item in values]
            if len(set(ids)) != len(ids):
                raise InvalidInputError(f"coldchain.{name} repeats {key}")


__all__ = [
    "BatchCompatibility", "CapacityAmount", "CapacityUnit", "ChangeoverRule",
    "ColdChainSetupPolicy", "ColdChainSnapshot", "ColdChainStorageLocation",
    "ColdChainZone", "CompatibilityPolicy", "ExposureLimit", "ExposureScope",
    "ExposureSegment", "PrecoolRequirement", "StorageOccupancy",
]
