"""Boundary projections for the optional R05 cold-chain snapshot."""

from __future__ import annotations

from uuid import UUID

from pydantic import StrictInt, StrictStr

from logistics_contracts.planning import Record
from logistics_domain import coldchain as domain


class CapacityAmountDTO(Record):
    domain_type = domain.CapacityAmount
    unit: domain.CapacityUnit
    amount: StrictInt


class CapacityPeriodDTO(Record):
    domain_type = domain.CapacityPeriod
    start_s: StrictInt
    end_s: StrictInt
    capacities: tuple[CapacityAmountDTO, ...]


class ColdChainZoneDTO(Record):
    domain_type = domain.ColdChainZone
    zone_id: UUID
    warehouse_id: UUID
    version: StrictInt
    setpoint_decic: StrictInt
    capacities: tuple[CapacityAmountDTO, ...]


class ColdChainStorageLocationDTO(Record):
    domain_type = domain.ColdChainStorageLocation
    location_id: UUID
    warehouse_id: UUID
    zone_id: UUID
    version: StrictInt
    capacities: tuple[CapacityAmountDTO, ...]
    available_windows: tuple[TimeWindowDTO, ...] = ()
    capacity_periods: tuple[CapacityPeriodDTO, ...] = ()


class StorageOccupancyDTO(Record):
    domain_type = domain.StorageOccupancy
    occupancy_id: UUID
    batch_id: StrictStr
    location_id: UUID
    capacity_use: tuple[CapacityAmountDTO, ...]
    origin: StrictStr
    inbound_operation_id: UUID | None = None
    outbound_operation_id: UUID | None = None
    declared_start_s: StrictInt | None = None


class ChangeoverRuleDTO(Record):
    domain_type = domain.ChangeoverRule
    from_class: StrictStr
    to_class: StrictStr
    duration_s: StrictInt


class ColdChainSetupPolicyDTO(Record):
    domain_type = domain.ColdChainSetupPolicy
    policy_id: UUID
    version: StrictStr
    rule_version: StrictStr
    rendering: StrictStr
    rules: tuple[ChangeoverRuleDTO, ...]
    default_duration_s: StrictInt | None = None


class PrecoolRequirementDTO(Record):
    domain_type = domain.PrecoolRequirement
    requirement_id: UUID
    batch_id: StrictStr
    warehouse_id: UUID
    precool_operation_id: UUID
    loading_operation_ids: tuple[UUID, ...]
    min_duration_s: StrictInt
    target_zone: StrictStr
    eligible_resource_ids: tuple[UUID, ...]


class ExposureLimitDTO(Record):
    domain_type = domain.ExposureLimit
    limit_id: UUID
    batch_id: StrictStr
    max_exposure_s: StrictInt
    scopes: tuple[domain.ExposureScope, ...]
    rule_version: StrictStr
    source: StrictStr


class ExposureSegmentDTO(Record):
    domain_type = domain.ExposureSegment
    segment_id: UUID
    batch_id: StrictStr
    scope: domain.ExposureScope
    start_s: StrictInt
    end_s: StrictInt
    source_kind: StrictStr


class ReuseRuleDTO(Record):
    domain_type = domain.ReuseRule
    location_id: UUID
    max_batch_age_s: StrictInt = 604800
    min_gap_s: StrictInt = 0


class BatchCompatibilityDTO(Record):
    domain_type = domain.BatchCompatibility
    batch_id: StrictStr
    warehouse_id: UUID
    temperature_zone: StrictStr
    min_temperature_decic: StrictInt
    max_temperature_decic: StrictInt
    compatibility_class: StrictStr | None = None


class CompatibilityPolicyDTO(Record):
    domain_type = domain.CompatibilityPolicy
    policy_id: UUID
    version: StrictStr
    rule_version: StrictStr
    incompatible_class_pairs: tuple[tuple[StrictStr, StrictStr], ...] = ()


class ColdChainSnapshotDTO(Record):
    domain_type = domain.ColdChainSnapshot
    rule_version: StrictStr
    horizon_s: StrictInt
    zones: tuple[ColdChainZoneDTO, ...] = ()
    storage_locations: tuple[ColdChainStorageLocationDTO, ...] = ()
    occupancies: tuple[StorageOccupancyDTO, ...] = ()
    setup_policies: tuple[ColdChainSetupPolicyDTO, ...] = ()
    precool_requirements: tuple[PrecoolRequirementDTO, ...] = ()
    exposure_limits: tuple[ExposureLimitDTO, ...] = ()
    batch_compatibility: tuple[BatchCompatibilityDTO, ...] = ()
    reuse_rules: tuple[ReuseRuleDTO, ...] = ()
    compatibility_policy: CompatibilityPolicyDTO | None = None


from logistics_contracts.entities import TimeWindowDTO  # noqa: E402

ColdChainStorageLocationDTO.model_rebuild()

from logistics_contracts.planning import PlanningSnapshotDTO  # noqa: E402

PlanningSnapshotDTO.model_rebuild()
