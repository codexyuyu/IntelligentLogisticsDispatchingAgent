"""Central domain -> boundary DTO mapping.

Keeping every projection in one module prevents the application layer, the worker and the
HTTP layer from each inventing their own conversion. The functions are pure and deterministic;
they never read the database and never mutate a domain value.
"""

from __future__ import annotations

from logistics_contracts import entities
from logistics_contracts.planning import (
    CostBreakdownDTO,
    DisturbanceWeightsDTO,
    EngineMetadataDTO,
    InventoryEntryDTO,
    LoadDTO,
    MatrixRefDTO,
    ObjectiveBreakdownDTO,
    ObjectivePolicyDTO,
    OperationAssignmentDTO,
    PlanningScopeDTO,
    PlanningSnapshotDTO,
    ResourceCalendarBindingDTO,
    ResourceRequirementDTO,
    ResourceBundleDTO,
    ResourceRevisionDTO,
    RouteDTO,
    RouteStopDTO,
    ScheduleTaskDTO,
    ScheduleVersionDTO,
    SetupOperationDTO,
    SolverEvidenceDTO,
    SolveBudgetDTO,
    StorageIntervalDTO,
    TransportPlanDTO,
    TravelMatrixDTO,
    ValidationReportDTO,
    ViolationDTO,
    WarehouseTaskDTO,
)
from logistics_contracts.metrics import MetricValueDTO
from logistics_contracts.simulation import (
    SimulationEventDTO,
    SimulationRequestDTO,
    SimulationResultDTO,
)
from logistics_contracts.warehouse import (
    DiagnosticDTO as WarehouseDiagnosticDTO,
    WarehouseProblemDTO,
    WarehouseSolutionDTO,
)
from logistics_contracts.transport import (
    DiagnosticDTO,
    RoutingNodeDTO,
    SignedLoadDTO,
    TransportProblemDTO,
    TransportSolutionDTO,
    VehicleStateDTO,
)
from logistics_domain import planning as domain
from logistics_domain import simulation as simulation_domain
from logistics_domain import transport as transport_domain
from logistics_domain import warehouse as warehouse_domain
from logistics_domain.primitives import Load
from logistics_domain.resources import ResourceCalendarBinding


def calendar_dto(value) -> entities.CalendarDTO:
    return entities.CalendarDTO.from_domain(value)


def scope_dto(scope: domain.PlanningScope) -> PlanningScopeDTO:
    return PlanningScopeDTO(order_ids=scope.order_ids, warehouse_ids=scope.warehouse_ids,
        vehicle_ids=scope.vehicle_ids, epoch_utc=scope.epoch_utc,
        horizon_s=scope.horizon_s)


def inventory_dto(entry: domain.InventoryEntry) -> InventoryEntryDTO:
    return InventoryEntryDTO(cargo_id=entry.cargo_id, location_id=entry.location_id,
        quantity_units=entry.quantity_units, weight_g=entry.weight_g,
        volume_cm3=entry.volume_cm3)


def revision_dto(revision: domain.ResourceRevision) -> ResourceRevisionDTO:
    from logistics_contracts.common import EntityRefDTO

    return ResourceRevisionDTO(entity_ref=EntityRefDTO.from_domain(revision.entity_ref),
        row_version=revision.row_version)


def matrix_dto(matrix: domain.TravelMatrix) -> TravelMatrixDTO:
    return TravelMatrixDTO(id=matrix.id, version=matrix.version, node_ids=matrix.node_ids,
        distance_m=matrix.distance_m, travel_s=matrix.travel_s, source=matrix.source,
        observed_at=matrix.observed_at, hash=matrix.hash)


def binding_dto(binding: ResourceCalendarBinding) -> ResourceCalendarBindingDTO:
    return ResourceCalendarBindingDTO(resource_id=binding.resource_id,
        source_calendar=calendar_dto(binding.source_calendar),
        source_hash=binding.source_hash, calendar=calendar_dto(binding.calendar))


def bundle_dto(bundle) -> ResourceBundleDTO:
    return ResourceBundleDTO(
        warehouses=tuple(entities.WarehouseDTO.from_domain(v) for v in bundle.warehouses),
        zones=tuple(entities.ZoneDTO.from_domain(v) for v in bundle.zones),
        locations=tuple(entities.StorageLocationDTO.from_domain(v) for v in bundle.locations),
        docks=tuple(entities.DockDTO.from_domain(v) for v in bundle.docks),
        workers=tuple(entities.WorkerDTO.from_domain(v) for v in bundle.workers),
        equipment=tuple(entities.EquipmentDTO.from_domain(v) for v in bundle.equipment),
        calendars=tuple(binding_dto(v) for v in bundle.calendars))


def snapshot_dto(snapshot: domain.PlanningSnapshot) -> PlanningSnapshotDTO:
    return PlanningSnapshotDTO(
        id=snapshot.id, scope=scope_dto(snapshot.scope),
        orders=tuple(entities.OrderDTO.from_domain(v) for v in snapshot.orders),
        cargo=tuple(entities.CargoDTO.from_domain(v) for v in snapshot.cargo),
        vehicles=tuple(entities.VehicleDTO.from_domain(v) for v in snapshot.vehicles),
        drivers=tuple(entities.DriverDTO.from_domain(v) for v in snapshot.drivers),
        resources=bundle_dto(snapshot.resources),
        inventory=tuple(inventory_dto(v) for v in snapshot.inventory),
        revisions=tuple(revision_dto(v) for v in snapshot.revisions),
        matrices=tuple(matrix_dto(v) for v in snapshot.matrices), hash=snapshot.hash)


def policy_dto(policy: domain.ObjectivePolicy) -> ObjectivePolicyDTO:
    return ObjectivePolicyDTO(version=policy.version,
        optional_unserved_penalty_cents=policy.optional_unserved_penalty_cents,
        soft_late_cents_per_s=policy.soft_late_cents_per_s,
        makespan_cents_per_s=policy.makespan_cents_per_s,
        disturbance_weights=DisturbanceWeightsDTO(
            assignment_change=policy.disturbance_weights.assignment_change,
            time_shift=policy.disturbance_weights.time_shift,
            order_change=policy.disturbance_weights.order_change,
            membership_change=policy.disturbance_weights.membership_change))


def budget_dto(budget: domain.SolveBudget) -> SolveBudgetDTO:
    return SolveBudgetDTO(wall_time_ms=budget.wall_time_ms, deadline_utc=budget.deadline_utc,
        max_candidates=budget.max_candidates, seed=budget.seed,
        worker_count=budget.worker_count,
        deterministic_test_mode=budget.deterministic_test_mode)


def node_dto(node: transport_domain.RoutingNode) -> RoutingNodeDTO:
    return RoutingNodeDTO(id=node.id, kind=node.kind, order_id=node.order_id,
        location_id=node.location_id, service_s=node.service_s,
        hard_window=entities.TimeWindowDTO(earliest_s=node.hard_window.earliest_s,
                                           latest_s=node.hard_window.latest_s),
        soft_due_at_s=node.soft_due_at_s,
        load_delta=SignedLoadDTO(weight_g=node.load_delta.weight_g,
                                 volume_cm3=node.load_delta.volume_cm3),
        pair_id=node.pair_id)


def vehicle_state_dto(vehicle: transport_domain.VehicleState) -> VehicleStateDTO:
    return VehicleStateDTO(vehicle_id=vehicle.vehicle_id, driver_id=vehicle.driver_id,
        start_node_id=vehicle.start_node_id, end_node_id=vehicle.end_node_id,
        start_load=LoadDTO(weight_g=vehicle.start_load.weight_g,
                           volume_cm3=vehicle.start_load.volume_cm3),
        capacity_weight_g=vehicle.capacity_weight_g,
        capacity_volume_cm3=vehicle.capacity_volume_cm3,
        setpoint_decic=vehicle.setpoint_decic,
        available_window=entities.TimeWindowDTO(earliest_s=vehicle.available_window.earliest_s,
                                               latest_s=vehicle.available_window.latest_s),
        max_drive_s=vehicle.max_drive_s, allowed_cargo_types=vehicle.allowed_cargo_types)


def problem_dto(problem: transport_domain.TransportProblem) -> TransportProblemDTO:
    return TransportProblemDTO(snapshot=snapshot_dto(problem.snapshot),
        nodes=tuple(node_dto(v) for v in problem.nodes),
        vehicles=tuple(vehicle_state_dto(v) for v in problem.vehicles),
        matrix=matrix_dto(problem.matrix),
        constraints=(), policy=policy_dto(problem.policy))


def route_dto(route: domain.Route) -> RouteDTO:
    return RouteDTO(id=route.id, status=route.status, created_at=route.created_at,
        updated_at=route.updated_at, row_version=route.row_version,
        schema_version="2.0.0", created_by=route.created_by, version_id=route.version_id,
        vehicle_id=route.vehicle_id, driver_id=route.driver_id,
        start_node_id=route.start_node_id, end_node_id=route.end_node_id,
        total_distance_m=route.total_distance_m,
        cost=CostBreakdownDTO(distance_cents=route.cost.distance_cents,
            fixed_vehicle_cents=route.cost.fixed_vehicle_cents,
            service_cents=route.cost.service_cents, overtime_cents=route.cost.overtime_cents,
            setup_cents=route.cost.setup_cents, total_cents=route.cost.total_cents),
        matrix_ref=MatrixRefDTO(matrix_id=route.matrix_ref.matrix_id,
                                version=route.matrix_ref.version, hash=route.matrix_ref.hash))


def route_stop_dto(stop: domain.RouteStop) -> RouteStopDTO:
    return RouteStopDTO(id=stop.id, status=stop.status, created_at=stop.created_at,
        updated_at=stop.updated_at, row_version=stop.row_version, schema_version="2.0.0",
        created_by=stop.created_by, route_id=stop.route_id, sequence=stop.sequence,
        node_id=stop.node_id, task_ids=stop.task_ids, arrival_s=stop.arrival_s,
        service_start_s=stop.service_start_s, departure_s=stop.departure_s,
        load_before=LoadDTO(weight_g=stop.load_before.weight_g,
                            volume_cm3=stop.load_before.volume_cm3),
        load_after=LoadDTO(weight_g=stop.load_after.weight_g,
                           volume_cm3=stop.load_after.volume_cm3))


def plan_dto(plan: domain.TransportPlan) -> TransportPlanDTO:
    return TransportPlanDTO(routes=tuple(route_dto(v) for v in plan.routes),
        unserved_order_ids=plan.unserved_order_ids,
        cost=CostBreakdownDTO(distance_cents=plan.cost.distance_cents,
            fixed_vehicle_cents=plan.cost.fixed_vehicle_cents,
            service_cents=plan.cost.service_cents, overtime_cents=plan.cost.overtime_cents,
            setup_cents=plan.cost.setup_cents, total_cents=plan.cost.total_cents))


def objective_dto(value: domain.ObjectiveBreakdown) -> ObjectiveBreakdownDTO:
    return ObjectiveBreakdownDTO(business_cost_cents=value.business_cost_cents,
        optional_unserved_penalty=value.optional_unserved_penalty,
        soft_late_penalty=value.soft_late_penalty,
        disturbance_penalty=value.disturbance_penalty,
        makespan_penalty=value.makespan_penalty, objective_total=value.objective_total)


def violation_dto(value: domain.Violation) -> ViolationDTO:
    from logistics_contracts.common import EntityRefDTO

    return ViolationDTO(code=value.code, severity=value.severity,
        entity_refs=tuple(EntityRefDTO.from_domain(v) for v in value.entity_refs),
        field_path=value.field_path, actual=value.actual, expected=value.expected,
        message=value.message)


def validation_dto(value: domain.ValidationReport) -> ValidationReportDTO:
    return ValidationReportDTO(id=value.id, candidate_hash=value.candidate_hash,
        snapshot_hash=value.snapshot_hash, rules_version=value.rules_version,
        valid=value.valid, required_codes=value.required_codes,
        checked_codes=value.checked_codes, unsupported_codes=value.unsupported_codes,
        violations=tuple(violation_dto(v) for v in value.violations),
        validated_at=value.validated_at)


def metadata_dto(value: domain.EngineMetadata) -> EngineMetadataDTO:
    return EngineMetadataDTO(name=value.name, version=value.version,
        configuration_hash=value.configuration_hash, seed=value.seed, workers=value.workers,
        input_hash=value.input_hash, solve_ms=value.solve_ms, build_ms=value.build_ms,
        engine_status=value.engine_status, incumbent_exists=value.incumbent_exists,
        best_bound=value.best_bound, optimality_gap=value.optimality_gap)


def evidence_dto(value: domain.SolverEvidence) -> SolverEvidenceDTO:
    return SolverEvidenceDTO(id=value.id, engine_name=value.engine_name,
        engine_version=value.engine_version, input_hash=value.input_hash,
        assignment_hash=value.assignment_hash, configuration_hash=value.configuration_hash,
        solve_status=value.solve_status, trusted_job_id=value.trusted_job_id)


def solution_dto(value: transport_domain.TransportSolution) -> TransportSolutionDTO:
    return TransportSolutionDTO(status=value.status,
        engine_metadata=metadata_dto(value.engine_metadata),
        candidate=plan_dto(value.candidate) if value.candidate is not None else None,
        optional_unserved_order_ids=value.optional_unserved_order_ids,
        objective=objective_dto(value.objective) if value.objective is not None else None,
        validation=validation_dto(value.validation) if value.validation is not None else None,
        diagnostics=tuple(DiagnosticDTO(code=v.code, severity=v.severity, message=v.message)
                          for v in value.diagnostics),
        solver_evidence=tuple(evidence_dto(v) for v in value.solver_evidence))


def warehouse_task_dto(task: domain.WarehouseTask) -> WarehouseTaskDTO:
    return WarehouseTaskDTO(id=task.id, status=task.status, created_at=task.created_at,
        updated_at=task.updated_at, row_version=task.row_version, schema_version="2.0.0",
        created_by=task.created_by, order_id=task.order_id, warehouse_id=task.warehouse_id,
        kind=task.kind, duration_s=task.duration_s,
        window=entities.TimeWindowDTO(earliest_s=task.window.earliest_s,
                                      latest_s=task.window.latest_s),
        predecessor_ids=task.predecessor_ids,
        requirements=tuple(ResourceRequirementDTO(
            resource_kind=value.resource_kind, eligible_ids=value.eligible_ids,
            units=value.units) for value in task.requirements),
        setup_class=task.setup_class)


def operation_assignment_dto(value: domain.OperationAssignment) -> OperationAssignmentDTO:
    return OperationAssignmentDTO(task_id=value.task_id, resource_id=value.resource_id,
        start_s=value.start_s, end_s=value.end_s, units=value.units)


def storage_interval_dto(value: domain.StorageInterval) -> StorageIntervalDTO:
    return StorageIntervalDTO(cargo_id=value.cargo_id, location_id=value.location_id,
        start_s=value.start_s, end_s=value.end_s, quantity_units=value.quantity_units,
        weight_g=value.weight_g, volume_cm3=value.volume_cm3)


def setup_operation_dto(value: domain.SetupOperation) -> SetupOperationDTO:
    return SetupOperationDTO(resource_id=value.resource_id, from_class=value.from_class,
        to_class=value.to_class, start_s=value.start_s, end_s=value.end_s,
        cost_cents=value.cost_cents)


def warehouse_problem_dto(problem: warehouse_domain.WarehouseProblem) -> WarehouseProblemDTO:
    return WarehouseProblemDTO(snapshot=snapshot_dto(problem.snapshot),
        tasks=tuple(warehouse_task_dto(value) for value in problem.tasks),
        policy=policy_dto(problem.policy), budget=budget_dto(problem.budget))


def warehouse_diagnostic_dto(value: warehouse_domain.Diagnostic) -> WarehouseDiagnosticDTO:
    return WarehouseDiagnosticDTO(code=value.code, message=value.message,
                                  severity=value.severity)


def warehouse_solution_dto(
        value: warehouse_domain.WarehouseSolution) -> WarehouseSolutionDTO:
    return WarehouseSolutionDTO(status=value.status,
        engine_metadata=metadata_dto(value.engine_metadata),
        assignments=tuple(operation_assignment_dto(v) for v in value.assignments),
        storage_allocations=tuple(storage_interval_dto(v) for v in value.storage_allocations),
        setup_operations=tuple(setup_operation_dto(v) for v in value.setup_operations),
        objective=objective_dto(value.objective) if value.objective is not None else None,
        validation=validation_dto(value.validation) if value.validation is not None else None,
        diagnostics=tuple(warehouse_diagnostic_dto(v) for v in value.diagnostics),
        solver_evidence=tuple(evidence_dto(v) for v in value.solver_evidence))


def metric_dto(value) -> MetricValueDTO:
    return MetricValueDTO(code=value.code, definition_version=value.definition_version,
        source=value.source, unit=value.unit, value=value.value,
        numerator=value.numerator, denominator=value.denominator,
        reason=value.reason, sample_count=value.sample_count)


def simulation_event_dto(value: simulation_domain.SimulationEvent) -> SimulationEventDTO:
    return SimulationEventDTO(event_id=value.event_id, time_s=value.time_s, kind=value.kind,
        vehicle_id=value.vehicle_id, order_id=value.order_id, stop_id=value.stop_id)


def simulation_request_dto(
        value: simulation_domain.SimulationRequest) -> SimulationRequestDTO:
    return SimulationRequestDTO(plan=plan_dto(value.plan),
        stops=tuple(route_stop_dto(v) for v in value.stops), seed=value.seed,
        until_s=value.until_s)


def simulation_result_dto(
        value: simulation_domain.SimulationResult) -> SimulationResultDTO:
    return SimulationResultDTO(status=value.status, final_time_s=value.final_time_s,
        events=tuple(simulation_event_dto(v) for v in value.events),
        delivered_order_ids=value.delivered_order_ids, seed=value.seed)


__all__ = [
    "binding_dto", "budget_dto", "bundle_dto", "calendar_dto", "evidence_dto",
    "inventory_dto", "matrix_dto", "metadata_dto", "node_dto", "objective_dto",
    "plan_dto", "policy_dto", "problem_dto", "revision_dto", "route_dto", "route_stop_dto",
    "scope_dto", "snapshot_dto", "solution_dto", "validation_dto", "vehicle_state_dto",
    "violation_dto", "warehouse_problem_dto", "warehouse_solution_dto",
    "warehouse_task_dto", "simulation_request_dto", "simulation_result_dto", "metric_dto",
]
