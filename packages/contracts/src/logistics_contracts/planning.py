"""Boundary projections for the P02-03 planning domain.

Every DTO is an exact field projection of the frozen domain/value type in
``logistics_domain.planning``: no independent entity, enum or free-form dict is defined
here. ``to_domain`` recursively maps nested DTOs, so a boundary payload either constructs a
fully valid pure-domain value or fails validation; there is no partial plan.

``Constraint``/``ConstraintParameters`` are absent for the same reason they are absent from
the domain module: the frozen inputs do not publish the code vocabulary or parameter shape.
"""

from __future__ import annotations

from datetime import datetime
from typing import ClassVar, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, StrictInt, model_validator

from logistics_contracts.common import EntityRefDTO
from logistics_contracts.entities import (
    CalendarDTO,
    CargoDTO,
    DriverDTO,
    EquipmentDTO,
    DockDTO,
    OrderDTO,
    StorageLocationDTO,
    TimeWindowDTO,
    VehicleDTO,
    WarehouseDTO,
    WorkerDTO,
    ZoneDTO,
)
from logistics_domain import planning as domain
from logistics_domain.errors import InvalidInputError
from logistics_domain.primitives import Load
from logistics_domain.states import EntityState, ResourceKind


class Record(BaseModel):
    """Base for pure planning records; validates by constructing the domain value."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    domain_type: ClassVar[type]

    def to_domain(self):
        return self.domain_type(**{key: _convert(value) for key, value in self.__dict__.items()})

    @model_validator(mode="after")
    def validate_domain(self):
        try:
            self.to_domain()
        except InvalidInputError as exc:
            raise ValueError(str(exc)) from exc
        except TypeError as exc:
            raise ValueError(str(exc)) from exc
        return self


def _convert(value):
    if isinstance(value, Record):
        return value.to_domain()
    if isinstance(value, BaseModel) and hasattr(value, "to_domain"):
        return value.to_domain()
    if isinstance(value, tuple):
        return tuple(_convert(item) for item in value)
    if isinstance(value, list):
        return [_convert(item) for item in value]
    return value


class PlanningEntityDTO(Record):
    id: UUID
    status: EntityState
    created_at: datetime
    updated_at: datetime
    row_version: StrictInt
    schema_version: Literal["2.0.0"]
    created_by: UUID


class PlanningScopeDTO(Record):
    domain_type = domain.PlanningScope
    order_ids: tuple[UUID, ...]
    warehouse_ids: tuple[UUID, ...]
    vehicle_ids: tuple[UUID, ...]
    epoch_utc: datetime
    horizon_s: StrictInt


class InventoryEntryDTO(Record):
    domain_type = domain.InventoryEntry
    cargo_id: UUID
    location_id: UUID
    quantity_units: StrictInt
    weight_g: StrictInt
    volume_cm3: StrictInt


class ResourceRevisionDTO(Record):
    domain_type = domain.ResourceRevision
    entity_ref: EntityRefDTO
    row_version: StrictInt


class ResourceRequirementDTO(Record):
    domain_type = domain.ResourceRequirement
    resource_kind: ResourceKind
    eligible_ids: tuple[UUID, ...]
    units: StrictInt


class MatrixRefDTO(Record):
    domain_type = domain.MatrixRef
    matrix_id: UUID
    version: StrictInt
    hash: str


class LoadDTO(Record):
    domain_type = Load
    weight_g: StrictInt
    volume_cm3: StrictInt


class CostBreakdownDTO(Record):
    domain_type = domain.CostBreakdown
    distance_cents: StrictInt
    fixed_vehicle_cents: StrictInt
    service_cents: StrictInt
    overtime_cents: StrictInt
    setup_cents: StrictInt
    total_cents: StrictInt


class ObjectiveBreakdownDTO(Record):
    domain_type = domain.ObjectiveBreakdown
    business_cost_cents: StrictInt
    optional_unserved_penalty: StrictInt
    soft_late_penalty: StrictInt
    disturbance_penalty: StrictInt
    makespan_penalty: StrictInt
    objective_total: StrictInt


class DisturbanceWeightsDTO(Record):
    domain_type = domain.DisturbanceWeights
    assignment_change: StrictInt
    time_shift: StrictInt
    order_change: StrictInt
    membership_change: StrictInt


class ObjectivePolicyDTO(Record):
    domain_type = domain.ObjectivePolicy
    version: str
    optional_unserved_penalty_cents: StrictInt
    soft_late_cents_per_s: StrictInt
    makespan_cents_per_s: StrictInt
    disturbance_weights: DisturbanceWeightsDTO


class SolveBudgetDTO(Record):
    domain_type = domain.SolveBudget
    wall_time_ms: StrictInt
    deadline_utc: datetime
    max_candidates: StrictInt
    seed: StrictInt
    worker_count: StrictInt = 1
    deterministic_test_mode: bool = False


class TravelMatrixDTO(Record):
    domain_type = domain.TravelMatrix
    id: UUID
    version: StrictInt
    node_ids: tuple[UUID, ...]
    distance_m: tuple[tuple[StrictInt | None, ...], ...]
    travel_s: tuple[tuple[StrictInt | None, ...], ...]
    source: str
    observed_at: datetime
    hash: str


class ViolationDTO(Record):
    domain_type = domain.Violation
    code: str
    severity: domain.Severity
    entity_refs: tuple[EntityRefDTO, ...]
    field_path: str
    actual: str
    expected: str
    message: str


class ValidationReportDTO(Record):
    domain_type = domain.ValidationReport
    id: UUID
    candidate_hash: str
    snapshot_hash: str
    rules_version: str
    valid: bool
    required_codes: tuple[str, ...]
    checked_codes: tuple[str, ...]
    unsupported_codes: tuple[str, ...]
    violations: tuple[ViolationDTO, ...]
    validated_at: datetime


class EngineMetadataDTO(Record):
    domain_type = domain.EngineMetadata
    name: str
    version: str
    configuration_hash: str
    seed: StrictInt
    workers: StrictInt
    input_hash: str
    solve_ms: StrictInt
    build_ms: StrictInt
    engine_status: str
    incumbent_exists: bool
    best_bound: StrictInt | None
    optimality_gap: float | None


class SolverEvidenceDTO(Record):
    domain_type = domain.SolverEvidence
    id: UUID
    engine_name: Literal["routing", "cp_sat"]
    engine_version: str
    input_hash: str
    assignment_hash: str
    configuration_hash: str
    solve_status: domain.SolveStatus
    trusted_job_id: UUID | None


class OperationAssignmentDTO(Record):
    domain_type = domain.OperationAssignment
    task_id: UUID
    resource_id: UUID
    start_s: StrictInt
    end_s: StrictInt
    units: StrictInt


class StorageIntervalDTO(Record):
    domain_type = domain.StorageInterval
    cargo_id: UUID
    location_id: UUID
    start_s: StrictInt
    end_s: StrictInt
    quantity_units: StrictInt
    weight_g: StrictInt
    volume_cm3: StrictInt


class SetupOperationDTO(Record):
    domain_type = domain.SetupOperation
    resource_id: UUID
    from_class: str
    to_class: str
    start_s: StrictInt
    end_s: StrictInt
    cost_cents: StrictInt


class TransportTaskDTO(PlanningEntityDTO):
    domain_type = domain.TransportTask
    order_id: UUID
    leg_no: StrictInt
    pickup_node_id: UUID
    delivery_node_id: UUID
    cargo_ids: tuple[UUID, ...]
    predecessor_ids: tuple[UUID, ...]
    service_s: StrictInt


class WarehouseTaskDTO(PlanningEntityDTO):
    domain_type = domain.WarehouseTask
    order_id: UUID | None
    warehouse_id: UUID
    kind: domain.OperationKind
    duration_s: StrictInt
    window: TimeWindowDTO
    predecessor_ids: tuple[UUID, ...]
    requirements: tuple[ResourceRequirementDTO, ...]
    setup_class: str
    required_skills: tuple[str, ...] = ()

    def to_domain(self):
        from logistics_domain.resources import Skill

        values = {key: _convert(value) for key, value in self.__dict__.items()
                  if key != "required_skills"}
        values["required_skills"] = tuple(Skill(value) for value in self.required_skills)
        return domain.WarehouseTask(**values)


class RouteDTO(PlanningEntityDTO):
    domain_type = domain.Route
    version_id: UUID
    vehicle_id: UUID
    driver_id: UUID
    start_node_id: UUID
    end_node_id: UUID
    total_distance_m: StrictInt
    cost: CostBreakdownDTO
    matrix_ref: MatrixRefDTO


class RouteStopDTO(PlanningEntityDTO):
    domain_type = domain.RouteStop
    route_id: UUID
    sequence: StrictInt
    node_id: UUID
    task_ids: tuple[UUID, ...]
    arrival_s: StrictInt
    service_start_s: StrictInt
    departure_s: StrictInt
    load_before: LoadDTO
    load_after: LoadDTO


class TransportPlanDTO(Record):
    domain_type = domain.TransportPlan
    routes: tuple[RouteDTO, ...]
    unserved_order_ids: tuple[UUID, ...]
    cost: CostBreakdownDTO


class WarehousePlanDTO(Record):
    domain_type = domain.WarehousePlan
    assignments: tuple[OperationAssignmentDTO, ...]
    storage_intervals: tuple[StorageIntervalDTO, ...]
    setup_operations: tuple[SetupOperationDTO, ...]
    cost: CostBreakdownDTO


class ScheduleDTO(PlanningEntityDTO):
    domain_type = domain.Schedule
    name: str
    scope: PlanningScopeDTO
    active_version_id: UUID | None
    epoch_utc: datetime
    horizon_s: StrictInt


class ScheduleTaskDTO(PlanningEntityDTO):
    domain_type = domain.ScheduleTask
    version_id: UUID
    task_id: UUID
    task_kind: domain.TaskKind
    assigned_resource_ids: tuple[UUID, ...]
    planned_start_s: StrictInt
    planned_end_s: StrictInt
    sequence: StrictInt | None


class ScheduleVersionDTO(PlanningEntityDTO):
    domain_type = domain.ScheduleVersion
    schedule_id: UUID
    version_no: StrictInt
    parent_version_id: UUID | None
    snapshot_id: UUID
    content_hash: str
    reason: str
    event_id: UUID | None
    task_refs: tuple[UUID, ...]
    validation_report_ref: UUID


class OptimizationRequestDTO(PlanningEntityDTO):
    domain_type = domain.OptimizationRequest
    kind: domain.OptimizationKind
    snapshot_id: UUID
    policy: ObjectivePolicyDTO
    budget: SolveBudgetDTO
    request_hash: str
    job_id: UUID


class OptimizationResultDTO(PlanningEntityDTO):
    domain_type = domain.OptimizationResult
    request_id: UUID
    solve_status: domain.SolveStatus
    engine_status: str
    candidate_id: UUID | None
    validation: ValidationReportDTO | None
    objective: ObjectiveBreakdownDTO | None
    engine_metadata: EngineMetadataDTO


class CandidatePlanDTO(Record):
    domain_type = domain.CandidatePlan
    id: UUID
    schedule_id: UUID
    base_version_id: UUID | None
    snapshot_id: UUID
    snapshot_hash: str
    epoch_utc: datetime
    horizon_s: StrictInt
    transport_plan: TransportPlanDTO
    warehouse_plan: WarehousePlanDTO
    task_assignments: tuple[ScheduleTaskDTO, ...]
    objective: ObjectiveBreakdownDTO
    content_hash: str
    solver_evidence_refs: tuple[UUID, ...]


class ResourceCalendarBindingDTO(Record):
    domain_type = domain.ResourceCalendarBinding
    resource_id: UUID
    source_calendar: CalendarDTO
    source_hash: str
    calendar: CalendarDTO


class ResourceBundleDTO(Record):
    domain_type = domain.ResourceBundle
    warehouses: tuple[WarehouseDTO, ...]
    zones: tuple[ZoneDTO, ...]
    locations: tuple[StorageLocationDTO, ...]
    docks: tuple[DockDTO, ...]
    workers: tuple[WorkerDTO, ...]
    equipment: tuple[EquipmentDTO, ...]
    calendars: tuple[ResourceCalendarBindingDTO, ...]


class PlanningSnapshotDTO(Record):
    domain_type = domain.PlanningSnapshot
    id: UUID
    scope: PlanningScopeDTO
    orders: tuple[OrderDTO, ...]
    cargo: tuple[CargoDTO, ...]
    vehicles: tuple[VehicleDTO, ...]
    drivers: tuple[DriverDTO, ...]
    resources: ResourceBundleDTO
    inventory: tuple[InventoryEntryDTO, ...]
    revisions: tuple[ResourceRevisionDTO, ...]
    matrices: tuple[TravelMatrixDTO, ...]
    hash: str


class CommitCommandDTO(Record):
    domain_type = domain.CommitCommand
    schedule_id: UUID
    candidate_id: UUID
    candidate_hash: str
    expected_active_version_id: UUID | None
    snapshot_hash: str
    idempotency_key: str
    confirmation_token: str | None


class CommitReceiptDTO(Record):
    domain_type = domain.CommitReceipt
    schedule_id: UUID
    version_id: UUID
    version_no: StrictInt
    parent_version_id: UUID | None
    content_hash: str
    audit_id: UUID
    trace_id: UUID
    committed_at: datetime
