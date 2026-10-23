"""Planning aggregates and the pure values they own (business contract 2.0.0).

Scope matches task P02-03 and the frozen tables in ``DATA_CONTRACTS.md``: planning scope,
T1/W1 planning tasks, routes/stops, schedules/tasks/versions, optimization request/result,
candidate plans, budgets, objective policy, validation reports and travel matrices. The
values are immutable: a plan version never overwrites its content, and status changes are
append-only projections recorded by the application layer.

This module is pure domain code. It imports only the standard library and earlier domain
modules (``primitives``, ``states``, ``orders``, ``resources``); it never imports contracts,
SQLAlchemy, Pydantic, FastAPI or a solver engine.

Two frozen vocabularies are not enumerated anywhere in the contract inputs:
``TaskKind`` (the two base planning task families, derived from ``EntityKind`` values) and
``VersionReason`` (a validated opaque reason code). ``Constraint`` is deliberately **not**
implemented here because the frozen inputs name ``ConstraintCode``/``ConstraintParameters``
without publishing a single member or parameter shape; inventing one would fabricate
contract data. Both gaps are recorded in the task reports instead of being hidden behind an
``Any`` or a free-form dict.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, fields, is_dataclass
from datetime import datetime, timedelta, timezone
from enum import Enum, StrEnum
from typing import Final, NewType, TypeAlias
from uuid import UUID

from logistics_domain.errors import InvalidInputError
from logistics_domain.orders import Cargo, Entity, Order
from logistics_domain.primitives import (
    HORIZON_MAX_S,
    EntityRef,
    Load,
    Money,
    ResourceCalendar,
    TimeWindow,
    require_int,
    require_non_negative_int,
    require_positive_int,
    require_sha256,
    require_utc_seconds,
    require_uuid,
)
from logistics_domain.resources import (
    Driver,
    OperationKind,
    ResourceBundle,
    ResourceCalendarBinding,
    Vehicle,
)
from logistics_domain.states import (
    ConstraintCode,
    EntityKind,
    LIFECYCLE_TRANSITIONS,
    ResourceKind,
)

__all__ = [
    "CandidatePlan",
    "CommitCommand",
    "CommitReceipt",
    "ConstraintCode",
    "CostBreakdown",
    "DisturbanceWeights",
    "EngineMetadata",
    "InventoryEntry",
    "MatrixRef",
    "ObjectiveBreakdown",
    "ObjectivePolicy",
    "OperationAssignment",
    "OptimizationKind",
    "OptimizationRequest",
    "OptimizationResult",
    "PlanningScope",
    "PlanningSnapshot",
    "ResourceRequirement",
    "ResourceRevision",
    "Route",
    "RouteStop",
    "Schedule",
    "ScheduleTask",
    "ScheduleVersion",
    "Severity",
    "SetupOperation",
    "SolveBudget",
    "SolveStatus",
    "SolverEvidence",
    "StorageInterval",
    "TaskKind",
    "TransportPlan",
    "TransportTask",
    "TravelMatrix",
    "ValidationReport",
    "VersionReason",
    "Violation",
    "WarehousePlan",
    "WarehouseTask",
    "canonical_bytes",
    "content_hash",
    "project_calendar",
]

#: Fractional-weight bound kept explicit: money and penalty fields are int64 here.
INT64_MAX: Final[int] = 2**63 - 1

#: Opaque but validated version reason code; no member list is published by the contract.
VersionReason = NewType("VersionReason", str)


class TaskKind(StrEnum):
    """Base planning task family. Values match the ``EntityKind`` addressees."""

    TRANSPORT = "transport_task"
    WAREHOUSE = "warehouse_task"


class OptimizationKind(StrEnum):
    """Optimization family carried by an ``OptimizationRequest``."""

    TRANSPORT = "transport"
    WAREHOUSE = "warehouse"
    JOINT = "joint"


class Severity(StrEnum):
    """Constraint / violation severity; hard violations invalidate a candidate."""

    HARD = "hard"
    SOFT = "soft"


class SolveStatus(StrEnum):
    """Typed solver completion; INFEASIBLE/TIMEOUT are results, not HTTP 500 errors."""

    OPTIMAL = "optimal"
    FEASIBLE = "feasible"
    INFEASIBLE = "infeasible"
    TIMEOUT = "timeout"
    UNKNOWN = "unknown"
    INVALID_INPUT = "invalid_input"
    ERROR = "error"
    CANCELLED = "cancelled"


def _require_uuid_tuple(value: object, *, field: str, allow_empty: bool = True) -> tuple[UUID, ...]:
    if not isinstance(value, tuple):
        raise InvalidInputError(f"{field} must be a tuple, got {type(value).__name__}")
    if not allow_empty and not value:
        raise InvalidInputError(f"{field} must not be empty")
    seen: set[UUID] = set()
    for index, item in enumerate(value):
        require_uuid(item, field=f"{field}[{index}]")
        if item in seen:
            raise InvalidInputError(f"{field} contains duplicate UUID {item}")
        seen.add(item)
    return value


def _require_optional_uuid(value: object, *, field: str) -> UUID | None:
    if value is None:
        return None
    return require_uuid(value, field=field)


def _require_safe_code(value: object, *, field: str, maximum: int = 128) -> str:
    if not isinstance(value, str) or not 1 <= len(value) <= maximum or value != value.strip():
        raise InvalidInputError(f"{field} must be 1..{maximum} unpadded characters")
    return value


def _require_version_text(value: object, *, field: str) -> str:
    if not isinstance(value, str):
        raise InvalidInputError(f"{field} must be a string")
    parts = value.split(".")
    if len(parts) != 3 or any(not part.isdecimal() for part in parts):
        raise InvalidInputError(f"{field} must be an exact major.minor.patch version, got {value!r}")
    return value


def _require_int64(value: object, *, field: str, minimum: int = 0) -> int:
    return require_int(value, field=field, minimum=minimum, maximum=INT64_MAX)


# ------------------------------------------------------------------------- canonical


def _canonical_value(value: object) -> object:
    """Deterministic JSON-compatible projection used for content hashes.

    Seconds are rendered as fixed UTC ``YYYY-MM-DDTHH:MM:SSZ``; UUIDs in canonical lowercase;
    enums by value; dataclasses and tuples in declaration order. Unknown values are rejected
    rather than stringified, so a hash can never depend on ``repr`` or dict ordering.
    """
    if value is None or isinstance(value, (str, bool, int)):
        return value
    if isinstance(value, float):
        raise InvalidInputError("canonical planning content must not contain floats")
    if isinstance(value, StrEnum):
        return value.value
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, UUID):
        return str(value)
    if isinstance(value, datetime):
        return value.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    if isinstance(value, (tuple, list)):
        return [_canonical_value(item) for item in value]
    if isinstance(value, dict):
        if any(not isinstance(key, str) for key in value):
            raise InvalidInputError("canonical map keys must be strings")
        return {key: _canonical_value(item) for key, item in value.items()}
    if is_dataclass(value) and not isinstance(value, type):
        return {field.name: _canonical_value(getattr(value, field.name)) for field in fields(value)}
    raise InvalidInputError(f"unsupported canonical value of type {type(value).__name__}")


def canonical_bytes(value: object) -> bytes:
    """UTF-8 canonical JSON: sorted keys, compact separators, explicit nulls, no NaN."""
    return json.dumps(_canonical_value(value), sort_keys=True, separators=(",", ":"),
                      ensure_ascii=False, allow_nan=False).encode("utf-8")


def content_hash(value: object) -> str:
    """``sha256`` of :func:`canonical_bytes`; the only plan identity used by P03/P16."""
    return hashlib.sha256(canonical_bytes(value)).hexdigest()


# --------------------------------------------------------------------------- values


@dataclass(frozen=True, slots=True)
class PlanningScope:
    """The exact master-data window a snapshot may read."""

    order_ids: tuple[UUID, ...]
    warehouse_ids: tuple[UUID, ...]
    vehicle_ids: tuple[UUID, ...]
    epoch_utc: datetime
    horizon_s: int

    def __post_init__(self) -> None:
        _require_uuid_tuple(self.order_ids, field="PlanningScope.order_ids")
        _require_uuid_tuple(self.warehouse_ids, field="PlanningScope.warehouse_ids")
        _require_uuid_tuple(self.vehicle_ids, field="PlanningScope.vehicle_ids")
        require_utc_seconds(self.epoch_utc, field="PlanningScope.epoch_utc")
        require_int(self.horizon_s, field="PlanningScope.horizon_s", minimum=1,
                    maximum=HORIZON_MAX_S)

    @property
    def ends_at_utc(self) -> datetime:
        return self.epoch_utc + timedelta(seconds=self.horizon_s)


@dataclass(frozen=True, slots=True)
class InventoryEntry:
    """One physical stock position; per-unit weight/volume are derived from ``Cargo``."""

    cargo_id: UUID
    location_id: UUID
    quantity_units: int
    weight_g: int
    volume_cm3: int

    def __post_init__(self) -> None:
        require_uuid(self.cargo_id, field="InventoryEntry.cargo_id")
        require_uuid(self.location_id, field="InventoryEntry.location_id")
        require_non_negative_int(self.quantity_units, field="InventoryEntry.quantity_units")
        require_non_negative_int(self.weight_g, field="InventoryEntry.weight_g")
        require_non_negative_int(self.volume_cm3, field="InventoryEntry.volume_cm3")
        if self.quantity_units == 0 and (self.weight_g or self.volume_cm3):
            raise InvalidInputError("zero-units inventory must not carry weight or volume")


@dataclass(frozen=True, slots=True)
class ResourceRevision:
    """One entry of the row-revision vector a snapshot was read at."""

    entity_ref: EntityRef
    row_version: int

    def __post_init__(self) -> None:
        if not isinstance(self.entity_ref, EntityRef):
            raise InvalidInputError("ResourceRevision.entity_ref must be an EntityRef")
        require_non_negative_int(self.row_version, field="ResourceRevision.row_version")
        if self.entity_ref.kind in (EntityKind.TRAVEL_MATRIX, EntityKind.REGION):
            raise InvalidInputError("matrix versions are not row revisions; region has no row")
        if self.entity_ref.revision is not None and self.entity_ref.revision != self.row_version:
            raise InvalidInputError("EntityRef.revision must equal ResourceRevision.row_version")


@dataclass(frozen=True, slots=True)
class ResourceRequirement:
    """Cumulative requirement over an explicit eligible resource set."""

    resource_kind: ResourceKind
    eligible_ids: tuple[UUID, ...]
    units: int

    def __post_init__(self) -> None:
        if not isinstance(self.resource_kind, ResourceKind):
            raise InvalidInputError("ResourceRequirement.resource_kind must be a ResourceKind")
        _require_uuid_tuple(self.eligible_ids, field="ResourceRequirement.eligible_ids", allow_empty=False)
        require_positive_int(self.units, field="ResourceRequirement.units")


@dataclass(frozen=True, slots=True)
class TransportTask(Entity):
    """One pickup→delivery leg; the task id is stable across plan versions."""

    lifecycle = "transport_task"

    order_id: UUID
    leg_no: int
    pickup_node_id: UUID
    delivery_node_id: UUID
    cargo_ids: tuple[UUID, ...]
    predecessor_ids: tuple[UUID, ...]
    service_s: int

    def __post_init__(self) -> None:
        Entity.__post_init__(self)
        require_uuid(self.order_id, field="TransportTask.order_id")
        require_uuid(self.pickup_node_id, field="TransportTask.pickup_node_id")
        require_uuid(self.delivery_node_id, field="TransportTask.delivery_node_id")
        require_positive_int(self.leg_no, field="TransportTask.leg_no")
        require_non_negative_int(self.service_s, field="TransportTask.service_s")
        _require_uuid_tuple(self.cargo_ids, field="TransportTask.cargo_ids", allow_empty=False)
        _require_uuid_tuple(self.predecessor_ids, field="TransportTask.predecessor_ids")
        if self.id in self.predecessor_ids:
            raise InvalidInputError("TransportTask cannot depend on itself")


@dataclass(frozen=True, slots=True)
class WarehouseTask(Entity):
    """One warehouse operation; ``setup`` tasks are explicit derived tasks."""

    lifecycle = "warehouse_task"

    order_id: UUID | None
    warehouse_id: UUID
    kind: OperationKind
    duration_s: int
    window: TimeWindow
    predecessor_ids: tuple[UUID, ...]
    requirements: tuple[ResourceRequirement, ...]
    setup_class: str

    def __post_init__(self) -> None:
        Entity.__post_init__(self)
        _require_optional_uuid(self.order_id, field="WarehouseTask.order_id")
        require_uuid(self.warehouse_id, field="WarehouseTask.warehouse_id")
        if not isinstance(self.kind, OperationKind):
            raise InvalidInputError("WarehouseTask.kind must be an OperationKind")
        require_non_negative_int(self.duration_s, field="WarehouseTask.duration_s")
        if not isinstance(self.window, TimeWindow):
            raise InvalidInputError("WarehouseTask.window must be a TimeWindow")
        _require_uuid_tuple(self.predecessor_ids, field="WarehouseTask.predecessor_ids")
        if self.id in self.predecessor_ids:
            raise InvalidInputError("WarehouseTask cannot depend on itself")
        if not isinstance(self.requirements, tuple):
            raise InvalidInputError("WarehouseTask.requirements must be a tuple")
        for index, requirement in enumerate(self.requirements):
            if not isinstance(requirement, ResourceRequirement):
                raise InvalidInputError(
                    f"WarehouseTask.requirements[{index}] must be a ResourceRequirement")
        _require_safe_code(self.setup_class, field="WarehouseTask.setup_class")


@dataclass(frozen=True, slots=True)
class TravelMatrix:
    """Versioned distance/travel matrix; ``None`` means unreachable on both layers."""

    id: UUID
    version: int
    node_ids: tuple[UUID, ...]
    distance_m: tuple[tuple[int | None, ...], ...]
    travel_s: tuple[tuple[int | None, ...], ...]
    source: str
    observed_at: datetime
    hash: str

    def __post_init__(self) -> None:
        require_uuid(self.id, field="TravelMatrix.id")
        require_positive_int(self.version, field="TravelMatrix.version")
        _require_uuid_tuple(self.node_ids, field="TravelMatrix.node_ids", allow_empty=False)
        size = len(self.node_ids)
        for name, matrix in (("distance_m", self.distance_m), ("travel_s", self.travel_s)):
            if not isinstance(matrix, tuple) or len(matrix) != size:
                raise InvalidInputError(f"TravelMatrix.{name} must have {size} rows")
            for row_index, row in enumerate(matrix):
                if not isinstance(row, tuple) or len(row) != size:
                    raise InvalidInputError(f"TravelMatrix.{name}[{row_index}] must have {size} cells")
                for cell in row:
                    if cell is not None:
                        require_non_negative_int(cell, field=f"TravelMatrix.{name}")
        for row_index in range(size):
            for column_index in range(size):
                if (self.distance_m[row_index][column_index] is None) != (
                        self.travel_s[row_index][column_index] is None):
                    raise InvalidInputError("unreachable arcs must be None on distance and travel")
        _require_safe_code(self.source, field="TravelMatrix.source", maximum=64)
        require_utc_seconds(self.observed_at, field="TravelMatrix.observed_at")
        require_sha256(self.hash, field="TravelMatrix.hash")


@dataclass(frozen=True, slots=True)
class MatrixRef:
    """Pinned reference to one immutable matrix revision."""

    matrix_id: UUID
    version: int
    hash: str

    def __post_init__(self) -> None:
        require_uuid(self.matrix_id, field="MatrixRef.matrix_id")
        require_positive_int(self.version, field="MatrixRef.version")
        require_sha256(self.hash, field="MatrixRef.hash")


@dataclass(frozen=True, slots=True)
class CostBreakdown:
    """Actual transport cost in fen; every component is counted exactly once."""

    distance_cents: int
    fixed_vehicle_cents: int
    service_cents: int
    overtime_cents: int
    setup_cents: int
    total_cents: int

    def __post_init__(self) -> None:
        for name in ("distance_cents", "fixed_vehicle_cents", "service_cents",
                     "overtime_cents", "setup_cents", "total_cents"):
            _require_int64(getattr(self, name), field=f"CostBreakdown.{name}")
        components = (self.distance_cents + self.fixed_vehicle_cents + self.service_cents
                      + self.overtime_cents + self.setup_cents)
        if components != self.total_cents:
            raise InvalidInputError(
                f"CostBreakdown.total_cents={self.total_cents} != component sum {components}")


@dataclass(frozen=True, slots=True)
class ObjectiveBreakdown:
    """Business cost plus explicit penalty terms; never presented as transport cost."""

    business_cost_cents: int
    optional_unserved_penalty: int
    soft_late_penalty: int
    disturbance_penalty: int
    makespan_penalty: int
    objective_total: int

    def __post_init__(self) -> None:
        for name in ("business_cost_cents", "optional_unserved_penalty", "soft_late_penalty",
                     "disturbance_penalty", "makespan_penalty", "objective_total"):
            _require_int64(getattr(self, name), field=f"ObjectiveBreakdown.{name}")
        terms = (self.business_cost_cents + self.optional_unserved_penalty
                 + self.soft_late_penalty + self.disturbance_penalty + self.makespan_penalty)
        if terms != self.objective_total:
            raise InvalidInputError(
                f"ObjectiveBreakdown.objective_total={self.objective_total} != term sum {terms}")


@dataclass(frozen=True, slots=True)
class DisturbanceWeights:
    """Integer weights applied to the four normalized disturbance ratios.

    The frozen contract fixes only the *unit* (non-negative int64) and the fact that the
    weights belong to ``ObjectivePolicy``. The four names mirror ``METRICS_CONTRACT`` and are
    recorded as a decision gap; no ratio math is implemented in this domain task.
    """

    assignment_change: int
    time_shift: int
    order_change: int
    membership_change: int

    def __post_init__(self) -> None:
        for name in ("assignment_change", "time_shift", "order_change", "membership_change"):
            _require_int64(getattr(self, name), field=f"DisturbanceWeights.{name}")


@dataclass(frozen=True, slots=True)
class ObjectivePolicy:
    """Weighted objective inputs; penalties stay separate from real cost."""

    version: str
    optional_unserved_penalty_cents: int
    soft_late_cents_per_s: int
    makespan_cents_per_s: int
    disturbance_weights: DisturbanceWeights

    def __post_init__(self) -> None:
        _require_version_text(self.version, field="ObjectivePolicy.version")
        for name in ("optional_unserved_penalty_cents", "soft_late_cents_per_s",
                     "makespan_cents_per_s"):
            _require_int64(getattr(self, name), field=f"ObjectivePolicy.{name}")
        if not isinstance(self.disturbance_weights, DisturbanceWeights):
            raise InvalidInputError("ObjectivePolicy.disturbance_weights must be DisturbanceWeights")


@dataclass(frozen=True, slots=True)
class SolveBudget:
    """Bounded solve budget; the wall clock is server-enforced and never client-extended."""

    wall_time_ms: int
    deadline_utc: datetime
    max_candidates: int
    seed: int
    worker_count: int = 1
    deterministic_test_mode: bool = False

    def __post_init__(self) -> None:
        require_int(self.wall_time_ms, field="SolveBudget.wall_time_ms", minimum=1, maximum=60000)
        require_utc_seconds(self.deadline_utc, field="SolveBudget.deadline_utc")
        require_int(self.max_candidates, field="SolveBudget.max_candidates", minimum=1, maximum=10)
        require_int(self.seed, field="SolveBudget.seed", minimum=0, maximum=INT64_MAX)
        require_positive_int(self.worker_count, field="SolveBudget.worker_count")
        if not isinstance(self.deterministic_test_mode, bool):
            raise InvalidInputError("SolveBudget.deterministic_test_mode must be a bool")


@dataclass(frozen=True, slots=True)
class EngineMetadata:
    """Original engine facts retained next to an optimization result."""

    name: str
    version: str
    configuration_hash: str
    seed: int
    workers: int
    input_hash: str
    solve_ms: int
    build_ms: int
    engine_status: str
    incumbent_exists: bool
    best_bound: int | None
    optimality_gap: float | None

    def __post_init__(self) -> None:
        _require_safe_code(self.name, field="EngineMetadata.name", maximum=64)
        _require_safe_code(self.version, field="EngineMetadata.version", maximum=64)
        require_sha256(self.configuration_hash, field="EngineMetadata.configuration_hash")
        require_int(self.seed, field="EngineMetadata.seed", minimum=0, maximum=INT64_MAX)
        require_positive_int(self.workers, field="EngineMetadata.workers")
        require_sha256(self.input_hash, field="EngineMetadata.input_hash")
        require_non_negative_int(self.solve_ms, field="EngineMetadata.solve_ms")
        require_non_negative_int(self.build_ms, field="EngineMetadata.build_ms")
        _require_safe_code(self.engine_status, field="EngineMetadata.engine_status", maximum=64)
        if not isinstance(self.incumbent_exists, bool):
            raise InvalidInputError("EngineMetadata.incumbent_exists must be a bool")
        if self.best_bound is not None:
            require_int(self.best_bound, field="EngineMetadata.best_bound")
        if self.optimality_gap is not None:
            gap = self.optimality_gap
            if not isinstance(gap, float) or gap != gap or gap in (float("inf"), float("-inf")) or gap < 0:
                raise InvalidInputError("EngineMetadata.optimality_gap must be a finite non-negative float")


@dataclass(frozen=True, slots=True)
class SolverEvidence:
    """Typed evidence that a real engine produced an assignment for a trusted job."""

    id: UUID
    engine_name: str
    engine_version: str
    input_hash: str
    assignment_hash: str
    configuration_hash: str
    solve_status: SolveStatus
    trusted_job_id: UUID | None

    def __post_init__(self) -> None:
        require_uuid(self.id, field="SolverEvidence.id")
        if self.engine_name not in ("routing", "cp_sat"):
            raise InvalidInputError("SolverEvidence.engine_name must be routing or cp_sat")
        _require_safe_code(self.engine_version, field="SolverEvidence.engine_version", maximum=64)
        for name in ("input_hash", "assignment_hash", "configuration_hash"):
            require_sha256(getattr(self, name), field=f"SolverEvidence.{name}")
        if not isinstance(self.solve_status, SolveStatus):
            raise InvalidInputError("SolverEvidence.solve_status must be SolveStatus")
        if self.trusted_job_id is not None:
            require_uuid(self.trusted_job_id, field="SolverEvidence.trusted_job_id")


@dataclass(frozen=True, slots=True)
class Violation:
    """One independently recomputed constraint violation."""

    code: ConstraintCode
    severity: Severity
    entity_refs: tuple[EntityRef, ...]
    field_path: str
    actual: str
    expected: str
    message: str

    def __post_init__(self) -> None:
        if not isinstance(self.code, str) or not self.code:
            raise InvalidInputError("Violation.code must be a nonempty constraint code")
        if not isinstance(self.severity, Severity):
            raise InvalidInputError("Violation.severity must be a Severity")
        if not isinstance(self.entity_refs, tuple):
            raise InvalidInputError("Violation.entity_refs must be a tuple")
        for index, reference in enumerate(self.entity_refs):
            if not isinstance(reference, EntityRef):
                raise InvalidInputError(f"Violation.entity_refs[{index}] must be an EntityRef")
        for name in ("field_path", "actual", "expected", "message"):
            value = getattr(self, name)
            if not isinstance(value, str) or not 1 <= len(value) <= 512:
                raise InvalidInputError(f"Violation.{name} must be 1..512 characters")


@dataclass(frozen=True, slots=True)
class ValidationReport:
    """Deterministic hard-validation outcome bound to candidate and snapshot hashes."""

    id: UUID
    candidate_hash: str
    snapshot_hash: str
    rules_version: str
    valid: bool
    required_codes: tuple[ConstraintCode, ...]
    checked_codes: tuple[ConstraintCode, ...]
    unsupported_codes: tuple[ConstraintCode, ...]
    violations: tuple[Violation, ...]
    validated_at: datetime

    def __post_init__(self) -> None:
        require_uuid(self.id, field="ValidationReport.id")
        require_sha256(self.candidate_hash, field="ValidationReport.candidate_hash")
        require_sha256(self.snapshot_hash, field="ValidationReport.snapshot_hash")
        _require_version_text(self.rules_version, field="ValidationReport.rules_version")
        if not isinstance(self.valid, bool):
            raise InvalidInputError("ValidationReport.valid must be a bool")
        for name in ("required_codes", "checked_codes", "unsupported_codes"):
            value = getattr(self, name)
            if not isinstance(value, tuple) or any(not isinstance(code, str) for code in value):
                raise InvalidInputError(f"ValidationReport.{name} must be a tuple of codes")
            if len(set(value)) != len(value):
                raise InvalidInputError(f"ValidationReport.{name} must not repeat a code")
        if not set(self.unsupported_codes) <= set(self.required_codes):
            raise InvalidInputError("unsupported codes must be a subset of required codes")
        if not isinstance(self.violations, tuple):
            raise InvalidInputError("ValidationReport.violations must be a tuple")
        for index, violation in enumerate(self.violations):
            if not isinstance(violation, Violation):
                raise InvalidInputError(f"ValidationReport.violations[{index}] must be a Violation")
        require_utc_seconds(self.validated_at, field="ValidationReport.validated_at")
        if self.unsupported_codes and self.valid:
            raise InvalidInputError("a report with unsupported rules cannot be valid")
        if self.valid and any(v.severity == Severity.HARD for v in self.violations):
            raise InvalidInputError("a report with a hard violation cannot be valid")
        if self.valid and not set(self.required_codes) <= set(self.checked_codes):
            raise InvalidInputError("a valid report must have checked every required code")


@dataclass(frozen=True, slots=True)
class OperationAssignment:
    """One warehouse task assignment over an interval."""

    task_id: UUID
    resource_id: UUID
    start_s: int
    end_s: int
    units: int

    def __post_init__(self) -> None:
        require_uuid(self.task_id, field="OperationAssignment.task_id")
        require_uuid(self.resource_id, field="OperationAssignment.resource_id")
        require_non_negative_int(self.start_s, field="OperationAssignment.start_s")
        require_non_negative_int(self.end_s, field="OperationAssignment.end_s")
        if self.start_s >= self.end_s:
            raise InvalidInputError("OperationAssignment requires start_s < end_s")
        require_positive_int(self.units, field="OperationAssignment.units")


@dataclass(frozen=True, slots=True)
class StorageInterval:
    """Stock held at one location for a half-open interval."""

    cargo_id: UUID
    location_id: UUID
    start_s: int
    end_s: int
    quantity_units: int
    weight_g: int
    volume_cm3: int

    def __post_init__(self) -> None:
        require_uuid(self.cargo_id, field="StorageInterval.cargo_id")
        require_uuid(self.location_id, field="StorageInterval.location_id")
        require_non_negative_int(self.start_s, field="StorageInterval.start_s")
        require_non_negative_int(self.end_s, field="StorageInterval.end_s")
        if self.start_s >= self.end_s:
            raise InvalidInputError("StorageInterval requires start_s < end_s")
        require_non_negative_int(self.quantity_units, field="StorageInterval.quantity_units")
        require_non_negative_int(self.weight_g, field="StorageInterval.weight_g")
        require_non_negative_int(self.volume_cm3, field="StorageInterval.volume_cm3")


@dataclass(frozen=True, slots=True)
class SetupOperation:
    """Explicit setup transition between two setup classes."""

    resource_id: UUID
    from_class: str
    to_class: str
    start_s: int
    end_s: int
    cost_cents: int

    def __post_init__(self) -> None:
        require_uuid(self.resource_id, field="SetupOperation.resource_id")
        _require_safe_code(self.from_class, field="SetupOperation.from_class")
        _require_safe_code(self.to_class, field="SetupOperation.to_class")
        if self.from_class == self.to_class:
            raise InvalidInputError("SetupOperation must change the setup class")
        require_non_negative_int(self.start_s, field="SetupOperation.start_s")
        require_non_negative_int(self.end_s, field="SetupOperation.end_s")
        if self.start_s >= self.end_s:
            raise InvalidInputError("SetupOperation requires start_s < end_s")
        _require_int64(self.cost_cents, field="SetupOperation.cost_cents")


@dataclass(frozen=True, slots=True)
class TransportPlan:
    """Pure transport plan content; never a free-form route dict."""

    routes: tuple[Route, ...]
    unserved_order_ids: tuple[UUID, ...]
    cost: CostBreakdown

    def __post_init__(self) -> None:
        if not isinstance(self.routes, tuple):
            raise InvalidInputError("TransportPlan.routes must be a tuple")
        for index, route in enumerate(self.routes):
            if not isinstance(route, Route):
                raise InvalidInputError(f"TransportPlan.routes[{index}] must be a Route")
        _require_uuid_tuple(self.unserved_order_ids, field="TransportPlan.unserved_order_ids")
        if not isinstance(self.cost, CostBreakdown):
            raise InvalidInputError("TransportPlan.cost must be a CostBreakdown")


@dataclass(frozen=True, slots=True)
class WarehousePlan:
    """Pure warehouse plan content with explicit setup and storage intervals."""

    assignments: tuple[OperationAssignment, ...]
    storage_intervals: tuple[StorageInterval, ...]
    setup_operations: tuple[SetupOperation, ...]
    cost: CostBreakdown

    def __post_init__(self) -> None:
        for name, expected in (("assignments", OperationAssignment),
                               ("storage_intervals", StorageInterval),
                               ("setup_operations", SetupOperation)):
            value = getattr(self, name)
            if not isinstance(value, tuple):
                raise InvalidInputError(f"WarehousePlan.{name} must be a tuple")
            for index, item in enumerate(value):
                if not isinstance(item, expected):
                    raise InvalidInputError(f"WarehousePlan.{name}[{index}] must be {expected.__name__}")
        if not isinstance(self.cost, CostBreakdown):
            raise InvalidInputError("WarehousePlan.cost must be a CostBreakdown")


@dataclass(frozen=True, slots=True)
class Route(Entity):
    """Immutable published route for one vehicle/driver pair."""

    lifecycle = "route"

    version_id: UUID
    vehicle_id: UUID
    driver_id: UUID
    start_node_id: UUID
    end_node_id: UUID
    total_distance_m: int
    cost: CostBreakdown
    matrix_ref: MatrixRef

    def __post_init__(self) -> None:
        Entity.__post_init__(self)
        for name in ("version_id", "vehicle_id", "driver_id", "start_node_id", "end_node_id"):
            require_uuid(getattr(self, name), field=f"Route.{name}")
        require_non_negative_int(self.total_distance_m, field="Route.total_distance_m")
        if not isinstance(self.cost, CostBreakdown):
            raise InvalidInputError("Route.cost must be a CostBreakdown")
        if not isinstance(self.matrix_ref, MatrixRef):
            raise InvalidInputError("Route.matrix_ref must be a MatrixRef")


@dataclass(frozen=True, slots=True)
class RouteStop(Entity):
    """One ordered route stop with half-open service occupancy."""

    lifecycle = "route_stop"

    route_id: UUID
    sequence: int
    node_id: UUID
    task_ids: tuple[UUID, ...]
    arrival_s: int
    service_start_s: int
    departure_s: int
    load_before: Load
    load_after: Load

    def __post_init__(self) -> None:
        Entity.__post_init__(self)
        require_uuid(self.route_id, field="RouteStop.route_id")
        require_uuid(self.node_id, field="RouteStop.node_id")
        require_non_negative_int(self.sequence, field="RouteStop.sequence")
        _require_uuid_tuple(self.task_ids, field="RouteStop.task_ids", allow_empty=False)
        for name in ("arrival_s", "service_start_s", "departure_s"):
            require_non_negative_int(getattr(self, name), field=f"RouteStop.{name}")
        if not self.arrival_s <= self.service_start_s <= self.departure_s:
            raise InvalidInputError("RouteStop requires arrival_s <= service_start_s <= departure_s")
        if not isinstance(self.load_before, Load) or not isinstance(self.load_after, Load):
            raise InvalidInputError("RouteStop loads must be Load values")


@dataclass(frozen=True, slots=True)
class Schedule(Entity):
    """Stable schedule identity; the active version is a separate CAS pointer."""

    lifecycle = "schedule"

    name: str
    scope: PlanningScope
    active_version_id: UUID | None
    epoch_utc: datetime
    horizon_s: int

    def __post_init__(self) -> None:
        Entity.__post_init__(self)
        _require_safe_code(self.name, field="Schedule.name")
        if not isinstance(self.scope, PlanningScope):
            raise InvalidInputError("Schedule.scope must be a PlanningScope")
        _require_optional_uuid(self.active_version_id, field="Schedule.active_version_id")
        require_utc_seconds(self.epoch_utc, field="Schedule.epoch_utc")
        require_int(self.horizon_s, field="Schedule.horizon_s", minimum=1, maximum=HORIZON_MAX_S)
        if self.scope.epoch_utc != self.epoch_utc or self.scope.horizon_s != self.horizon_s:
            raise InvalidInputError("Schedule epoch/horizon must equal its PlanningScope")


@dataclass(frozen=True, slots=True)
class ScheduleTask(Entity):
    """Assignment of one stable planning task inside a concrete plan version."""

    lifecycle = "schedule_task"

    version_id: UUID
    task_id: UUID
    task_kind: TaskKind
    assigned_resource_ids: tuple[UUID, ...]
    planned_start_s: int
    planned_end_s: int
    sequence: int | None

    def __post_init__(self) -> None:
        Entity.__post_init__(self)
        require_uuid(self.version_id, field="ScheduleTask.version_id")
        require_uuid(self.task_id, field="ScheduleTask.task_id")
        if not isinstance(self.task_kind, TaskKind):
            raise InvalidInputError("ScheduleTask.task_kind must be a TaskKind")
        _require_uuid_tuple(self.assigned_resource_ids, field="ScheduleTask.assigned_resource_ids")
        require_non_negative_int(self.planned_start_s, field="ScheduleTask.planned_start_s")
        require_non_negative_int(self.planned_end_s, field="ScheduleTask.planned_end_s")
        if self.planned_start_s >= self.planned_end_s:
            raise InvalidInputError("ScheduleTask requires planned_start_s < planned_end_s")
        if self.sequence is not None:
            require_non_negative_int(self.sequence, field="ScheduleTask.sequence")


@dataclass(frozen=True, slots=True)
class ScheduleVersion(Entity):
    """Append-only plan version; content is immutable after creation."""

    lifecycle = "schedule_version"

    schedule_id: UUID
    version_no: int
    parent_version_id: UUID | None
    snapshot_id: UUID
    content_hash: str
    reason: VersionReason
    event_id: UUID | None
    task_refs: tuple[UUID, ...]
    validation_report_ref: UUID

    def __post_init__(self) -> None:
        Entity.__post_init__(self)
        require_uuid(self.schedule_id, field="ScheduleVersion.schedule_id")
        require_positive_int(self.version_no, field="ScheduleVersion.version_no")
        _require_optional_uuid(self.parent_version_id, field="ScheduleVersion.parent_version_id")
        require_uuid(self.snapshot_id, field="ScheduleVersion.snapshot_id")
        require_sha256(self.content_hash, field="ScheduleVersion.content_hash")
        _require_safe_code(str(self.reason), field="ScheduleVersion.reason", maximum=64)
        _require_optional_uuid(self.event_id, field="ScheduleVersion.event_id")
        _require_uuid_tuple(self.task_refs, field="ScheduleVersion.task_refs")
        require_uuid(self.validation_report_ref, field="ScheduleVersion.validation_report_ref")
        if self.parent_version_id == self.id:
            raise InvalidInputError("ScheduleVersion cannot be its own parent")
        if self.parent_version_id == self.schedule_id:
            raise InvalidInputError("ScheduleVersion parent must be a version id, not a schedule id")


@dataclass(frozen=True, slots=True)
class OptimizationRequest(Entity):
    """Immutable optimization request bound 1:1 to a durable Job."""

    lifecycle = "optimization_request"

    kind: OptimizationKind
    snapshot_id: UUID
    policy: ObjectivePolicy
    budget: SolveBudget
    request_hash: str
    job_id: UUID

    def __post_init__(self) -> None:
        Entity.__post_init__(self)
        if not isinstance(self.kind, OptimizationKind):
            raise InvalidInputError("OptimizationRequest.kind must be an OptimizationKind")
        require_uuid(self.snapshot_id, field="OptimizationRequest.snapshot_id")
        if not isinstance(self.policy, ObjectivePolicy):
            raise InvalidInputError("OptimizationRequest.policy must be an ObjectivePolicy")
        if not isinstance(self.budget, SolveBudget):
            raise InvalidInputError("OptimizationRequest.budget must be a SolveBudget")
        require_sha256(self.request_hash, field="OptimizationRequest.request_hash")
        require_uuid(self.job_id, field="OptimizationRequest.job_id")


@dataclass(frozen=True, slots=True)
class OptimizationResult(Entity):
    """Recorded solver result; absent incumbent means no candidate/objective content."""

    lifecycle = "optimization_result"

    request_id: UUID
    solve_status: SolveStatus
    engine_status: str
    candidate_id: UUID | None
    validation: ValidationReport | None
    objective: ObjectiveBreakdown | None
    engine_metadata: EngineMetadata

    def __post_init__(self) -> None:
        Entity.__post_init__(self)
        require_uuid(self.request_id, field="OptimizationResult.request_id")
        if not isinstance(self.solve_status, SolveStatus):
            raise InvalidInputError("OptimizationResult.solve_status must be a SolveStatus")
        _require_safe_code(self.engine_status, field="OptimizationResult.engine_status", maximum=64)
        _require_optional_uuid(self.candidate_id, field="OptimizationResult.candidate_id")
        if not isinstance(self.engine_metadata, EngineMetadata):
            raise InvalidInputError("OptimizationResult.engine_metadata must be EngineMetadata")
        if self.candidate_id is None:
            if self.validation is not None or self.objective is not None:
                raise InvalidInputError("a result without an incumbent cannot carry validation/objective")
        else:
            if self.objective is None:
                raise InvalidInputError("a candidate result requires an objective breakdown")
            if self.validation is not None and not isinstance(self.validation, ValidationReport):
                raise InvalidInputError("OptimizationResult.validation must be a ValidationReport or None")
        if self.solve_status in (SolveStatus.OPTIMAL, SolveStatus.FEASIBLE) and self.candidate_id is None:
            raise InvalidInputError("OPTIMAL/FEASIBLE requires an incumbent candidate")


@dataclass(frozen=True, slots=True)
class CandidatePlan:
    """Validated plan candidate assembly; solver evidence is bound non-empty at commit."""

    id: UUID
    schedule_id: UUID
    base_version_id: UUID | None
    snapshot_id: UUID
    snapshot_hash: str
    epoch_utc: datetime
    horizon_s: int
    transport_plan: TransportPlan
    warehouse_plan: WarehousePlan
    task_assignments: tuple[ScheduleTask, ...]
    objective: ObjectiveBreakdown
    content_hash: str
    solver_evidence_refs: tuple[UUID, ...]

    def __post_init__(self) -> None:
        require_uuid(self.id, field="CandidatePlan.id")
        require_uuid(self.schedule_id, field="CandidatePlan.schedule_id")
        _require_optional_uuid(self.base_version_id, field="CandidatePlan.base_version_id")
        require_uuid(self.snapshot_id, field="CandidatePlan.snapshot_id")
        require_sha256(self.snapshot_hash, field="CandidatePlan.snapshot_hash")
        require_utc_seconds(self.epoch_utc, field="CandidatePlan.epoch_utc")
        require_int(self.horizon_s, field="CandidatePlan.horizon_s", minimum=1, maximum=HORIZON_MAX_S)
        if not isinstance(self.transport_plan, TransportPlan):
            raise InvalidInputError("CandidatePlan.transport_plan must be a TransportPlan")
        if not isinstance(self.warehouse_plan, WarehousePlan):
            raise InvalidInputError("CandidatePlan.warehouse_plan must be a WarehousePlan")
        if not isinstance(self.task_assignments, tuple):
            raise InvalidInputError("CandidatePlan.task_assignments must be a tuple")
        seen: set[UUID] = set()
        for index, assignment in enumerate(self.task_assignments):
            if not isinstance(assignment, ScheduleTask):
                raise InvalidInputError(
                    f"CandidatePlan.task_assignments[{index}] must be a ScheduleTask")
            if assignment.version_id != self.id:
                raise InvalidInputError("candidate task assignment points at another plan version")
            if assignment.task_id in seen:
                raise InvalidInputError("candidate repeats a task id")
            seen.add(assignment.task_id)
        if not isinstance(self.objective, ObjectiveBreakdown):
            raise InvalidInputError("CandidatePlan.objective must be an ObjectiveBreakdown")
        require_sha256(self.content_hash, field="CandidatePlan.content_hash")
        _require_uuid_tuple(self.solver_evidence_refs, field="CandidatePlan.solver_evidence_refs")


@dataclass(frozen=True, slots=True)
class PlanningSnapshot:
    """Consistent read of one planning scope, including matrix and calendar versions."""

    id: UUID
    scope: PlanningScope
    orders: tuple[Order, ...]
    cargo: tuple[Cargo, ...]
    vehicles: tuple[Vehicle, ...]
    drivers: tuple[Driver, ...]
    resources: ResourceBundle
    inventory: tuple[InventoryEntry, ...]
    revisions: tuple[ResourceRevision, ...]
    matrices: tuple[TravelMatrix, ...]
    hash: str

    def __post_init__(self) -> None:
        require_uuid(self.id, field="PlanningSnapshot.id")
        if not isinstance(self.scope, PlanningScope):
            raise InvalidInputError("PlanningSnapshot.scope must be a PlanningScope")
        if not isinstance(self.resources, ResourceBundle):
            raise InvalidInputError("PlanningSnapshot.resources must be a ResourceBundle")
        for name, expected in (("orders", Order), ("cargo", Cargo), ("vehicles", Vehicle),
                               ("drivers", Driver)):
            value = getattr(self, name)
            if not isinstance(value, tuple):
                raise InvalidInputError(f"PlanningSnapshot.{name} must be a tuple")
            for index, item in enumerate(value):
                if not isinstance(item, expected):
                    raise InvalidInputError(f"PlanningSnapshot.{name}[{index}] must be {expected.__name__}")
        if not isinstance(self.inventory, tuple):
            raise InvalidInputError("PlanningSnapshot.inventory must be a tuple")
        if not isinstance(self.revisions, tuple):
            raise InvalidInputError("PlanningSnapshot.revisions must be a tuple")
        if not isinstance(self.matrices, tuple):
            raise InvalidInputError("PlanningSnapshot.matrices must be a tuple")
        require_sha256(self.hash, field="PlanningSnapshot.hash")
        self._validate_graph()
        expected = content_hash({field.name: getattr(self, field.name)
                                 for field in fields(self) if field.name != "hash"})
        if expected != self.hash:
            raise InvalidInputError("PlanningSnapshot.hash does not match its canonical content")

    def _validate_graph(self) -> None:
        order_by_id = {order.id: order for order in self.orders}
        if len(order_by_id) != len(self.orders):
            raise InvalidInputError("PlanningSnapshot repeats an order id")
        cargo_by_id = {item.id: item for item in self.cargo}
        if len(cargo_by_id) != len(self.cargo):
            raise InvalidInputError("PlanningSnapshot repeats a cargo id")
        for item in self.cargo:
            if item.order_id not in order_by_id:
                raise InvalidInputError("snapshot cargo references an unknown order")
            if item.id not in order_by_id[item.order_id].cargo_ids:
                raise InvalidInputError("order cargo_ids does not list its cargo")
        for order in self.orders:
            if set(order.cargo_ids) != {item.id for item in self.cargo if item.order_id == order.id}:
                raise InvalidInputError("order cargo references do not match snapshot cargo")
        if set(self.scope.order_ids) != set(order_by_id):
            raise InvalidInputError("snapshot orders differ from the declared scope")
        if set(self.scope.vehicle_ids) != {vehicle.id for vehicle in self.vehicles}:
            raise InvalidInputError("snapshot vehicles differ from the declared scope")
        if set(self.scope.warehouse_ids) != {warehouse.id for warehouse in self.resources.warehouses}:
            raise InvalidInputError("snapshot warehouses differ from the declared scope")
        if len({vehicle.id for vehicle in self.vehicles}) != len(self.vehicles):
            raise InvalidInputError("PlanningSnapshot repeats a vehicle id")
        if len({driver.id for driver in self.drivers}) != len(self.drivers):
            raise InvalidInputError("PlanningSnapshot repeats a driver id")
        inventory_by_cargo: dict[UUID, int] = {}
        for entry in self.inventory:
            if entry.cargo_id not in cargo_by_id:
                raise InvalidInputError("inventory references unknown cargo")
            location = next((item for item in self.resources.locations
                             if item.id == entry.location_id), None)
            if location is None:
                raise InvalidInputError("inventory references an unknown storage location")
            inventory_by_cargo[entry.cargo_id] = inventory_by_cargo.get(entry.cargo_id, 0) + entry.quantity_units
        for cargo_id, quantity in inventory_by_cargo.items():
            if quantity > cargo_by_id[cargo_id].quantity_units:
                raise InvalidInputError("inventory exceeds the cargo quantity")
        revision_targets = [(EntityKind.ORDER, entity.id) for entity in self.orders]
        revision_targets += [(EntityKind.CARGO, entity.id) for entity in self.cargo]
        revision_targets += [(EntityKind.VEHICLE, entity.id) for entity in self.vehicles]
        revision_targets += [(EntityKind.DRIVER, entity.id) for entity in self.drivers]
        for kind, items in (
            (EntityKind.WAREHOUSE, self.resources.warehouses),
            (EntityKind.WAREHOUSE_ZONE, self.resources.zones),
            (EntityKind.STORAGE_LOCATION, self.resources.locations),
            (EntityKind.DOCK, self.resources.docks),
            (EntityKind.WORKER, self.resources.workers),
            (EntityKind.EQUIPMENT, self.resources.equipment),
        ):
            revision_targets += [(kind, entity.id) for entity in items]
        revision_keys = [(revision.entity_ref.kind, revision.entity_ref.id) for revision in self.revisions]
        if len(set(revision_keys)) != len(revision_keys):
            raise InvalidInputError("PlanningSnapshot repeats a resource revision")
        if set(revision_keys) != set(revision_targets):
            raise InvalidInputError("snapshot revisions do not cover exactly the snapshot entities")
        matrix_ids = [matrix.id for matrix in self.matrices]
        if len(set(matrix_ids)) != len(matrix_ids):
            raise InvalidInputError("PlanningSnapshot repeats a travel matrix")
        for matrix in self.matrices:
            if not matrix.node_ids:
                raise InvalidInputError("snapshot matrix without nodes")

    @classmethod
    def create(
        cls,
        *,
        id: UUID,
        scope: PlanningScope,
        orders: tuple[Order, ...],
        cargo: tuple[Cargo, ...],
        vehicles: tuple[Vehicle, ...],
        drivers: tuple[Driver, ...],
        resources: ResourceBundle,
        inventory: tuple[InventoryEntry, ...],
        revisions: tuple[ResourceRevision, ...],
        matrices: tuple[TravelMatrix, ...],
    ) -> "PlanningSnapshot":
        """Build a snapshot whose hash is recomputed from its canonical content."""
        body = dict(id=id, scope=scope, orders=orders, cargo=cargo, vehicles=vehicles,
                    drivers=drivers, resources=resources, inventory=inventory,
                    revisions=revisions, matrices=matrices)
        return cls(hash=content_hash(body), **body)


@dataclass(frozen=True, slots=True)
class CommitCommand:
    """Idempotent commit intent; actor/trace are added by the application boundary."""

    schedule_id: UUID
    candidate_id: UUID
    candidate_hash: str
    expected_active_version_id: UUID | None
    snapshot_hash: str
    idempotency_key: str
    confirmation_token: str | None

    def __post_init__(self) -> None:
        require_uuid(self.schedule_id, field="CommitCommand.schedule_id")
        require_uuid(self.candidate_id, field="CommitCommand.candidate_id")
        require_sha256(self.candidate_hash, field="CommitCommand.candidate_hash")
        _require_optional_uuid(self.expected_active_version_id,
                               field="CommitCommand.expected_active_version_id")
        require_sha256(self.snapshot_hash, field="CommitCommand.snapshot_hash")
        _require_safe_code(self.idempotency_key, field="CommitCommand.idempotency_key",
                           maximum=256)
        if self.confirmation_token is not None:
            _require_safe_code(self.confirmation_token, field="CommitCommand.confirmation_token",
                               maximum=512)


@dataclass(frozen=True, slots=True)
class CommitReceipt:
    """Stored outcome of one successful commit; replay returns the identical receipt."""

    schedule_id: UUID
    version_id: UUID
    version_no: int
    parent_version_id: UUID | None
    content_hash: str
    audit_id: UUID
    trace_id: UUID
    committed_at: datetime

    def __post_init__(self) -> None:
        for name in ("schedule_id", "version_id", "audit_id", "trace_id"):
            require_uuid(getattr(self, name), field=f"CommitReceipt.{name}")
        require_positive_int(self.version_no, field="CommitReceipt.version_no")
        _require_optional_uuid(self.parent_version_id, field="CommitReceipt.parent_version_id")
        require_sha256(self.content_hash, field="CommitReceipt.content_hash")
        require_utc_seconds(self.committed_at, field="CommitReceipt.committed_at")


# ------------------------------------------------------------------ calendar projection


def project_calendar(calendar: ResourceCalendar, scope: PlanningScope) -> ResourceCalendar:
    """Project an absolute calendar onto ``[scope.epoch, scope.epoch+horizon)``.

    Absolute endpoints are ``calendar.epoch_utc + integer seconds``; the intersection with
    the scope window is kept, a non-empty intersection is re-based on ``scope.epoch_utc``,
    and empty intersections are dropped. No second-level rounding or cross-epoch reuse is
    performed; the source calendar remains unchanged and is bound separately.
    """
    if not isinstance(calendar, ResourceCalendar):
        raise InvalidInputError("project_calendar expects a ResourceCalendar")
    if not isinstance(scope, PlanningScope):
        raise InvalidInputError("project_calendar expects a PlanningScope")
    from logistics_domain.primitives import CalendarInterval

    scope_start = scope.epoch_utc
    scope_end = scope_start + timedelta(seconds=scope.horizon_s)
    projected: list[CalendarInterval] = []
    for interval in calendar.intervals:
        absolute_start = calendar.epoch_utc + timedelta(seconds=interval.start_s)
        absolute_end = calendar.epoch_utc + timedelta(seconds=interval.end_s)
        start = max(absolute_start, scope_start)
        end = min(absolute_end, scope_end)
        if start >= end:
            continue
        projected.append(CalendarInterval(
            start_s=int((start - scope_start).total_seconds()),
            end_s=int((end - scope_start).total_seconds()),
            available_units=interval.available_units,
        ))
    return ResourceCalendar(epoch_utc=scope_start, intervals=tuple(projected),
                            version=calendar.version)


def bind_calendar(resource_id: UUID, source: ResourceCalendar,
                  projected: ResourceCalendar) -> ResourceCalendarBinding:
    """Bind a projected calendar to its immutable source and canonical source hash."""
    return ResourceCalendarBinding(resource_id=resource_id, source_calendar=source,
                                   source_hash=content_hash(source), calendar=projected)


#: Re-exported so callers can reference the frozen lifecycle without importing ``states``.
PLANNING_LIFECYCLES: Final[frozenset[str]] = frozenset(
    name for name in LIFECYCLE_TRANSITIONS
    if name in {"transport_task", "warehouse_task", "route", "route_stop", "schedule",
                "schedule_task", "schedule_version", "optimization_request",
                "optimization_result"}
)

#: ``Money`` is part of the planning unit vocabulary even though plans store integer cents.
PlanningMoney: TypeAlias = Money