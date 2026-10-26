"""SHARED R05 cold-chain contracts (contract 0.2.0).

Ownership: SHARED. 乙方 (PARTNER) is the serial integrator of this module; DSH
consumes it and must not define parallel DTOs.

Frozen semantics (contract version 0.2.0, see contracts/changes/
20261023-partner-r05-freeze.md):

* All times are integer scenario seconds relative to ``PlanningSnapshot.origin_at``.
* Every storage interval is half-open ``[start_s, end_s)``: a location is
  released at ``end_s`` before the next occupant starts at the same second.
* Capacities are never mixed.  A location declares one entry per capacity
  dimension it tracks, and every occupancy consuming it uses the same units.
* Missing data is not zero.  Absent changeover rules, unknown compatibility
  classes and unchecked exposure coverage must surface as ``not_checked`` or a
  violation, never as a passed check.
"""
from typing import Literal
from pydantic import StrictStr, model_validator
from app.contracts.common import ContractModel, Id, NonNegativeInt, PositiveInt, Source, TimeWindow
from app.domain.states import TemperatureZone

#: Capacity dimensions a storage location may track.  A location may track more
#: than one, but an occupancy must use the same dimension it consumes.
CapacityUnit = Literal['weight_g', 'volume_cm3', 'quantity_units']

#: Where a cargo batch can accumulate exposure time.
ExposureScope = Literal['in_warehouse', 'waiting', 'loading', 'transport']


class CapacityAmount(ContractModel):
    """One integer capacity amount in exactly one dimension."""

    unit: CapacityUnit
    amount: NonNegativeInt


def _unique_units(items: tuple[CapacityAmount, ...]) -> bool:
    return len({item.unit for item in items}) == len(items)


class WarehouseZone(ContractModel):
    """A cold zone: temperature class plus its set point and nominal capacity."""

    zone_id: Id
    warehouse_id: Id
    version: PositiveInt
    temperature_zone: TemperatureZone
    setpoint_decic: int
    capacities: tuple[CapacityAmount, ...]

    @model_validator(mode='after')
    def coherent(self):
        if not self.capacities or not _unique_units(self.capacities):
            raise ValueError('zone capacities must be non-empty with unique units')
        return self


class StorageLocation(ContractModel):
    """A physical storage location (cold room / rack slot) inside one zone.

    ``available_windows`` empty means "no calendar restriction declared"; it is
    not a claim that the location is available at all times.
    """

    location_id: Id
    warehouse_id: Id
    zone_id: Id
    version: PositiveInt
    capacities: tuple[CapacityAmount, ...]
    available_windows: tuple[TimeWindow, ...] = ()

    @model_validator(mode='after')
    def coherent(self):
        if not self.capacities or not _unique_units(self.capacities):
            raise ValueError('location capacities must be non-empty with unique units')
        return self


class StorageOccupancy(ContractModel):
    """Declared claim of one batch on one location.

    The planned interval is derived, not stored:

    * it starts at ``outbound``-independent ``declared_start_s`` (``0`` for
      initial stock) or at the end of ``inbound_operation_id``;
    * it ends at the start of ``outbound_operation_id`` or at ``horizon_s`` when
      the batch is still stored at the end of the planning horizon.

    Solver output resolves this into :class:`ScheduledOccupancy`.
    """

    occupancy_id: Id
    batch_id: Id
    location_id: Id
    capacity_use: tuple[CapacityAmount, ...]
    origin: Literal['initial_stock', 'planned_inbound']
    inbound_operation_id: Id | None = None
    outbound_operation_id: Id | None = None
    declared_start_s: NonNegativeInt | None = None

    @model_validator(mode='after')
    def coherent(self):
        if not self.capacity_use or not _unique_units(self.capacity_use):
            raise ValueError('occupancy capacity_use must be non-empty with unique units')
        if self.origin == 'initial_stock':
            if self.inbound_operation_id is not None:
                raise ValueError('initial stock cannot have an inbound operation')
            if self.declared_start_s not in (None, 0):
                raise ValueError('initial stock starts at 0')
        else:
            if self.inbound_operation_id is None and self.declared_start_s is None:
                raise ValueError('planned_inbound needs inbound_operation_id or declared_start_s')
        return self


class ScheduledOccupancy(ContractModel):
    """Resolved storage occupancy for one planned interval ``[start_s, end_s)``."""

    occupancy_id: Id
    batch_id: Id
    location_id: Id
    capacity_use: tuple[CapacityAmount, ...]
    start_s: NonNegativeInt
    end_s: NonNegativeInt

    @model_validator(mode='after')
    def coherent(self):
        if self.end_s <= self.start_s:
            raise ValueError('occupancy end_s must be after start_s')
        if not self.capacity_use or not _unique_units(self.capacity_use):
            raise ValueError('occupancy capacity_use must be non-empty with unique units')
        return self


class ResourceRequirement(ContractModel):
    """One named resource need of an operation.

    ``fixed`` requires exactly one eligible resource.  ``choose_one`` lets the
    solver pick any eligible resource.  ``quantity_units`` is how many units of
    that resource the operation holds for its whole interval.
    """

    requirement_id: Id
    requirement_kind: StrictStr
    eligible_resource_ids: tuple[Id, ...]
    quantity_units: PositiveInt = 1
    selection: Literal['fixed', 'choose_one'] = 'fixed'

    @model_validator(mode='after')
    def coherent(self):
        if not self.eligible_resource_ids:
            raise ValueError('requirement needs at least one eligible resource')
        if self.selection == 'fixed' and len(self.eligible_resource_ids) != 1:
            raise ValueError('fixed requirement must name exactly one resource')
        if len(set(self.eligible_resource_ids)) != len(self.eligible_resource_ids):
            raise ValueError('eligible resource ids must be unique')
        return self


class ResourceAssignment(ContractModel):
    """Actual resource chosen for one ``ResourceRequirement``."""

    requirement_id: Id
    resource_id: Id
    quantity_units: PositiveInt = 1


class ChangeoverRule(ContractModel):
    """Clean/quarantine changeover duration between two setup classes."""

    from_class: StrictStr
    to_class: StrictStr
    duration_s: NonNegativeInt


class SetupPolicy(ContractModel):
    """Sequence-dependent changeover policy bound to resources by id.

    ``rendering`` fixes how a changeover appears in solver output:

    * ``gap``: the gap between the two adjacent operations on the same resource
      must be at least the rule duration; accepting a shorter gap is a failure.
    * ``explicit_operation``: a setup operation occupying the resource (and any
      personnel/equipment it needs) must be emitted between the two operations.

    ``default_duration_s is None`` means an unlisted class pair is unknown, so
    the changeover cannot be zero: it is infeasible or unvalidated, never free.
    """

    policy_id: Id
    version: StrictStr
    rule_version: StrictStr
    rendering: Literal['gap', 'explicit_operation']
    rules: tuple[ChangeoverRule, ...]
    default_duration_s: NonNegativeInt | None = None

    @model_validator(mode='after')
    def coherent(self):
        pairs = [(rule.from_class, rule.to_class) for rule in self.rules]
        if len(set(pairs)) != len(pairs):
            raise ValueError('changeover rules must be unique per class pair')
        return self


class PrecoolRequirement(ContractModel):
    """Pre-cooling step that must finish before the batch may be loaded."""

    requirement_id: Id
    batch_id: Id
    warehouse_id: Id
    precool_operation_id: Id
    loading_operation_ids: tuple[Id, ...] = ()
    min_duration_s: PositiveInt
    target_temperature_zone: TemperatureZone
    eligible_resource_ids: tuple[Id, ...]

    @model_validator(mode='after')
    def coherent(self):
        if not self.eligible_resource_ids:
            raise ValueError('precool requirement needs at least one eligible resource')
        return self


class ExposureLimit(ContractModel):
    """Maximum cumulative exposure time allowed for one batch."""

    limit_id: Id
    batch_id: Id
    max_exposure_s: PositiveInt
    scopes: tuple[ExposureScope, ...]
    rule_version: StrictStr
    source: Source

    @model_validator(mode='after')
    def coherent(self):
        if not self.scopes:
            raise ValueError('exposure limit needs at least one scope')
        if len(set(self.scopes)) != len(self.scopes):
            raise ValueError('exposure scopes must be unique')
        return self


class ExposureSegment(ContractModel):
    """One observed/planned exposure interval ``[start_s, end_s)`` of a batch.

    Segments of the same batch and scope are merged as a union before
    comparison: overlapping observations are never double counted.  Coverage
    that the producer cannot evidence must be reported as ``not_checked``.
    """

    segment_id: Id
    batch_id: Id
    scope: ExposureScope
    start_s: NonNegativeInt
    end_s: NonNegativeInt
    source_kind: Literal['declared', 'planned', 'observed']

    @model_validator(mode='after')
    def coherent(self):
        if self.end_s <= self.start_s:
            raise ValueError('exposure segment end_s must be after start_s')
        return self


class BatchCompatibility(ContractModel):
    """Batch facts needed to check temperature and mixed-load compatibility."""

    batch_id: Id
    warehouse_id: Id
    temperature_zone: TemperatureZone
    min_temperature_decic: int
    max_temperature_decic: int
    compatibility_class: StrictStr | None = None

    @model_validator(mode='after')
    def coherent(self):
        if self.min_temperature_decic > self.max_temperature_decic:
            raise ValueError('min_temperature_decic must not exceed max_temperature_decic')
        return self


class CompatibilityPolicy(ContractModel):
    """Versioned rule for batches that must never overlap in one location."""

    policy_id: Id
    version: StrictStr
    rule_version: StrictStr
    incompatible_class_pairs: tuple[tuple[StrictStr, StrictStr], ...] = ()

    def forbidden(self, left: StrictStr, right: StrictStr) -> bool:
        """Symmetric lookup; a pair forbids overlap in both directions."""
        for a, b in self.incompatible_class_pairs:
            if (a == left and b == right) or (a == right and b == left):
                return True
        return False

    @model_validator(mode='after')
    def coherent(self):
        seen = set()
        for left, right in self.incompatible_class_pairs:
            key = (left, right) if left <= right else (right, left)
            if key in seen:
                raise ValueError('incompatible class pairs must be unique')
            seen.add(key)
        return self


class ColdChainSnapshot(ContractModel):
    """All R05 inputs of one planning snapshot.

    Attached as ``PlanningSnapshot.coldchain``; ``None`` there means the scenario
    makes no R05 claim and every R05 rule is not_checked.
    """

    rule_version: StrictStr
    horizon_s: PositiveInt
    zones: tuple[WarehouseZone, ...] = ()
    storage_locations: tuple[StorageLocation, ...] = ()
    occupancies: tuple[StorageOccupancy, ...] = ()
    setup_policies: tuple[SetupPolicy, ...] = ()
    precool_requirements: tuple[PrecoolRequirement, ...] = ()
    exposure_limits: tuple[ExposureLimit, ...] = ()
    batch_compatibility: tuple[BatchCompatibility, ...] = ()
    compatibility_policy: CompatibilityPolicy | None = None

    @model_validator(mode='after')
    def unique_ids(self):
        for name in ('zones', 'storage_locations', 'occupancies', 'setup_policies',
                     'precool_requirements', 'exposure_limits', 'batch_compatibility'):
            items = getattr(self, name)
            key = {
                'zones': 'zone_id',
                'storage_locations': 'location_id',
                'occupancies': 'occupancy_id',
                'setup_policies': 'policy_id',
                'precool_requirements': 'requirement_id',
                'exposure_limits': 'limit_id',
                'batch_compatibility': 'batch_id',
            }[name]
            ids = [getattr(item, key) for item in items]
            if len(set(ids)) != len(ids):
                raise ValueError(f'{name} must have unique {key}')
        return self


class ScheduledChangeover(ContractModel):
    """Resolved changeover between two adjacent operations of one resource."""

    changeover_id: Id
    resource_id: Id
    from_class: StrictStr
    to_class: StrictStr
    duration_s: NonNegativeInt
    after_operation_id: Id
    before_operation_id: Id
    #: Present when the policy rendering is ``explicit_operation``.
    setup_operation_id: Id | None = None


class ColdChainPlan(ContractModel):
    """R05 output of one warehouse schedule (evidence, not a certificate)."""

    rule_version: StrictStr
    occupancies: tuple[ScheduledOccupancy, ...] = ()
    exposure_segments: tuple[ExposureSegment, ...] = ()
    changeovers: tuple[ScheduledChangeover, ...] = ()

    @model_validator(mode='after')
    def unique_ids(self):
        occupancy_ids = [item.occupancy_id for item in self.occupancies]
        if len(set(occupancy_ids)) != len(occupancy_ids):
            raise ValueError('occupancies must have unique occupancy_id')
        segment_ids = [item.segment_id for item in self.exposure_segments]
        if len(set(segment_ids)) != len(segment_ids):
            raise ValueError('exposure segments must have unique segment_id')
        changeover_ids = [item.changeover_id for item in self.changeovers]
        if len(set(changeover_ids)) != len(changeover_ids):
            raise ValueError('changeovers must have unique changeover_id')
        return self
