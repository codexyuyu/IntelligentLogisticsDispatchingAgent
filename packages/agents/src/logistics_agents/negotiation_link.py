"""Bind R08 to solved current-domain plans, without importing any solver adapter.

The caller supplies actual solver results and independently validated reports.
Missing or stale evidence yields not_checked with no coordinator and no bids.
All tasks share one coordinator so conflicts cannot disappear between orders.
"""
from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Literal
from uuid import UUID

from logistics_agents.contract_net import (
    ContractNet,
    NegotiationError,
    NegotiationPolicy,
    NegotiationResult,
    TaskSpec,
)
from logistics_agents.negotiation_roles import (
    ExceptionRecoveryRole,
    RecoveryDeclaration,
    TransportBinding,
    TransportWindowRole,
    WarehouseWindowRole,
)
from logistics_domain.planning import CandidatePlan, SolveStatus, TaskKind, content_hash
from logistics_domain.primitives import TimeWindow
from logistics_domain.transport import RoutingNodeKind, TransportProblem, TransportSolution
from logistics_domain.warehouse import WarehouseProblem, WarehouseSolution

FEASIBLE = (SolveStatus.OPTIMAL, SolveStatus.FEASIBLE)


@dataclass(frozen=True)
class PlanTaskBinding:
    task_id: UUID
    order_id: UUID | None
    resource_ids: tuple[UUID, ...]
    vehicle_id: UUID | None
    handoff_ready_at_s: int


@dataclass(frozen=True)
class NegotiationOutcome:
    status: Literal['checked', 'not_checked']
    reason: str
    bindings: tuple[PlanTaskBinding, ...]
    result: NegotiationResult | None


@dataclass(frozen=True)
class NegotiationLink:
    status: Literal['checked', 'not_checked']
    reason: str
    tasks: tuple[TaskSpec, ...] = ()
    bindings: tuple[PlanTaskBinding, ...] = ()
    coordinator: ContractNet | None = None

    def negotiate(self, now_s: int = 0, idempotency_key: str | None = None) -> NegotiationOutcome:
        result = (self.coordinator.negotiate(self.tasks, now_s, idempotency_key)
                  if self.coordinator is not None else None)
        return NegotiationOutcome(self.status, self.reason, self.bindings, result)


def _require(condition: bool, reason: str) -> None:
    if not condition:
        raise NegotiationError(reason)


def _check_solution(problem, solution, engine, assignment_hash, validation_hash):
    _require(solution is not None, f'{engine}_solution_missing')
    _require(solution.status in FEASIBLE and solution.engine_metadata.incumbent_exists,
             f'{engine}_no_feasible_solution')
    _require(solution.engine_metadata.input_hash == content_hash(problem), f'{engine}_input_mismatch')
    evidence = solution.solver_evidence
    _require(bool(evidence), f'{engine}_evidence_missing')
    _require(all(e.engine_name == engine and e.solve_status == solution.status
                 and e.input_hash == content_hash(problem)
                 and e.assignment_hash == assignment_hash for e in evidence), f'{engine}_evidence_mismatch')
    report = solution.validation
    _require(report is not None, f'{engine}_validation_missing')
    _require(report.valid and report.snapshot_hash == problem.snapshot.hash
             and report.candidate_hash == validation_hash, f'{engine}_validation_mismatch')


def link_plan(warehouse_problem: WarehouseProblem, warehouse_solution: WarehouseSolution | None, *,
              candidate: CandidatePlan | None = None,
              transport_problem: TransportProblem | None = None,
              transport_solution: TransportSolution | None = None,
              available_at_s: Mapping[UUID, int] | None = None,
              recoveries: tuple[RecoveryDeclaration, ...] = (),
              policy: NegotiationPolicy | None = None) -> NegotiationLink:
    """Adapt a warehouse solve, optionally bound to a combined CandidatePlan.

    Vehicle availability is an explicit input: current Vehicle has no such field.
    Vehicle/driver shifts come from current snapshot and TransportProblem, and
    per-task handoffs come from the assigned warehouse operation's actual end.
    This validates evidence binding, not a replacement for independent validators.
    """
    try:
        return _link(warehouse_problem, warehouse_solution, candidate, transport_problem,
                     transport_solution, available_at_s, recoveries, policy)
    except NegotiationError as error:
        return NegotiationLink('not_checked', str(error))


def _link(problem, solution, candidate, transport_problem, transport_solution,
          available_at_s, recoveries, policy):
    _require(solution is not None, 'cp_sat_solution_missing')
    _check_solution(problem, solution, 'cp_sat', content_hash(solution.assignments), content_hash({
        'assignments': solution.assignments, 'storage': solution.storage_allocations,
        'setup': solution.setup_operations}))
    snapshot = problem.snapshot
    assigned = {}
    bundle = snapshot.resources
    resources_by_id = {r.id: (kind, r) for kind, group in (
        ('dock', bundle.docks), ('worker', bundle.workers), ('equipment', bundle.equipment)) for r in group}
    for assignment in solution.assignments:
        assigned.setdefault(assignment.task_id, []).append(assignment)
    _require(set(assigned) == {t.id for t in problem.tasks}, 'warehouse_task_coverage_mismatch')
    _require(candidate is not None or (transport_problem is None and transport_solution is None),
             'transport_requires_candidate')
    has_transport = candidate is not None and bool(candidate.transport_plan.routes)
    if candidate is not None:
        _require((candidate.snapshot_id, candidate.snapshot_hash, candidate.epoch_utc, candidate.horizon_s) ==
                 (snapshot.id, snapshot.hash, snapshot.scope.epoch_utc, snapshot.scope.horizon_s),
                 'candidate_snapshot_mismatch')
        body = {name: getattr(candidate, name) for name in (
            'schedule_id', 'snapshot_id', 'snapshot_hash', 'epoch_utc', 'horizon_s',
            'transport_plan', 'warehouse_plan', 'task_assignments', 'objective', 'solver_evidence_refs')}
        _require(candidate.content_hash == content_hash(body), 'candidate_content_mismatch')
        _require(candidate.warehouse_plan.assignments == solution.assignments
                 and candidate.warehouse_plan.storage_intervals == solution.storage_allocations
                 and candidate.warehouse_plan.setup_operations == solution.setup_operations,
                 'candidate_warehouse_mismatch')
        scheduled = {a.task_id: a for a in candidate.task_assignments if a.task_kind == TaskKind.WAREHOUSE}
        _require(set(scheduled) == set(assigned), 'candidate_task_coverage_mismatch')
        for task_id, values in assigned.items():
            task = scheduled[task_id]
            _require(set(task.assigned_resource_ids) == {a.resource_id for a in values}
                     and task.planned_start_s == min(a.start_s for a in values)
                     and task.planned_end_s == max(a.end_s for a in values), 'candidate_task_assignment_mismatch')
        evidence_ids = {e.id for e in solution.solver_evidence}
        if has_transport:
            _require(transport_problem is not None and transport_solution is not None,
                     'transport_evidence_missing')
            _require(transport_problem.snapshot.hash == snapshot.hash, 'transport_snapshot_mismatch')
            _require(transport_solution.candidate == candidate.transport_plan, 'candidate_transport_mismatch')
            _check_solution(transport_problem, transport_solution, 'routing',
                            content_hash(candidate.transport_plan.routes),
                            content_hash({'plan': candidate.transport_plan, 'stops': transport_solution.stops}))
            evidence_ids.update(e.id for e in transport_solution.solver_evidence)
        _require(set(candidate.solver_evidence_refs) == evidence_ids, 'candidate_evidence_refs_mismatch')

    bindings, transport_bindings, specs = [], [], []
    # Identity includes availability/declarations: same times with changed evidence
    # cannot silently replay as the same negotiation or have the same digest.
    source_hash = content_hash({'problem': problem, 'assignments': solution.assignments,
                               'candidate': candidate, 'availability': {str(k): v for k, v in (available_at_s or {}).items()},
                               'recoveries': recoveries})
    for task in sorted(problem.tasks, key=lambda t: str(t.id)):
        values = assigned[task.id]
        _require(len(values) == len(task.requirements), 'warehouse_requirement_coverage_mismatch')
        covered = set()
        for assignment in values:
            _require(assignment.resource_id in resources_by_id, 'warehouse_resource_missing_or_unsupported')
            kind, resource = resources_by_id[assignment.resource_id]
            matches = [i for i, req in enumerate(task.requirements)
                       if assignment.resource_id in req.eligible_ids and req.resource_kind.value == kind
                       and assignment.units == req.units]
            _require(len(matches) == 1 and matches[0] not in covered
                     and resource.warehouse_id == task.warehouse_id, 'warehouse_resource_binding_mismatch')
            covered.add(matches[0])
        _require(len({(a.start_s, a.end_s) for a in values}) == 1, 'inconsistent_operation_window')
        _require(values[0].end_s - values[0].start_s == task.duration_s,
                 'operation_duration_mismatch')
        _require(task.window.earliest_s <= values[0].start_s < values[0].end_s <= task.window.latest_s,
                 'solved_operation_outside_task_window')
        resources = tuple(sorted({a.resource_id for a in values}, key=str))
        ready = max(a.end_s for a in values)
        vehicle_id = None
        if has_transport and task.order_id is not None:
            nodes = {n.id: n for n in transport_problem.nodes}
            routes = {r.id: r for r in candidate.transport_plan.routes}
            deliveries = [s for s in transport_solution.stops
                          if s.node_id in nodes and nodes[s.node_id].order_id == task.order_id
                          and nodes[s.node_id].kind == RoutingNodeKind.DELIVERY]
            route_ids = {s.route_id for s in deliveries}
            _require(len(route_ids) == 1 and route_ids <= routes.keys(), 'carrying_route_missing_or_ambiguous')
            route = routes[next(iter(route_ids))]
            vehicle_id = route.vehicle_id
            vehicle = next((v for v in snapshot.vehicles if v.id == vehicle_id), None)
            state = next((v for v in transport_problem.vehicles if v.vehicle_id == vehicle_id), None)
            driver = next((d for d in snapshot.drivers if d.id == route.driver_id), None)
            _require(vehicle is not None and state is not None and driver is not None,
                     'vehicle_or_driver_missing')
            _require(vehicle.driver_id == state.driver_id == driver.id, 'vehicle_driver_binding_mismatch')
            _require(vehicle.calendar.epoch_utc == snapshot.scope.epoch_utc, 'vehicle_calendar_epoch_mismatch')
            _require(available_at_s is not None and vehicle_id in available_at_s, 'available_at_s_missing')
            availability = available_at_s[vehicle_id]
            _require(type(availability) is int and availability >= 0, 'invalid_available_at_s')
            pickups = [s for s in transport_solution.stops if s.route_id == route.id
                       and s.node_id in nodes and nodes[s.node_id].order_id == task.order_id
                       and nodes[s.node_id].kind == RoutingNodeKind.PICKUP]
            _require(len(pickups) == 1, 'handoff_stop_missing_or_ambiguous')
            warehouse = next((w for w in snapshot.resources.warehouses if w.id == task.warehouse_id), None)
            _require(warehouse is not None, 'warehouse_missing')
            _require(nodes[pickups[0].node_id].location_id == warehouse.node_id, 'handoff_warehouse_mismatch')
            _require(pickups[0].service_start_s >= ready, 'solved_handoff_before_warehouse_ready')
            service_duration = pickups[0].departure_s - pickups[0].service_start_s
            _require(service_duration > 0, 'empty_handoff_service')
            lower = max(driver.shift.earliest_s, state.available_window.earliest_s)
            upper = min(driver.shift.latest_s, state.available_window.latest_s)
            _require(lower < upper, 'empty_vehicle_shift')
            transport_bindings.append(TransportBinding(str(task.id), str(task.warehouse_id), vehicle_id,
                TimeWindow(lower, upper), availability, ready, service_duration))
        bindings.append(PlanTaskBinding(task.id, task.order_id, resources, vehicle_id, ready))
        specs.append(TaskSpec(str(task.id), str(task.warehouse_id), task.window.earliest_s,
                              task.window.latest_s, exclusive_resource_ids=tuple(sorted(
                                  str(r) for r in (*resources, *((vehicle_id,) if vehicle_id else ())))),
                              source_hash=source_hash))
    _require(bool(specs), 'no_solved_tasks')
    by_id = {s.task_id: s for s in specs}
    _require(all(d.task_id in by_id and d.resource_id in by_id[d.task_id].exclusive_resource_ids
                 for d in recoveries), 'recovery_binding_mismatch')
    coordinator = ContractNet([
        WarehouseWindowRole(snapshot, problem.tasks, solution.assignments),
        TransportWindowRole(snapshot.vehicles, tuple(transport_bindings)),
        ExceptionRecoveryRole(recoveries),
    ], policy)
    return NegotiationLink('checked', 'bound_to_solver_evidence', tuple(specs), tuple(bindings), coordinator)


def tasks_from_plan(*args, **kwargs) -> tuple[TaskSpec, ...]:
    """Return verified public tasks; never silently omit tasks with missing evidence."""
    link = link_plan(*args, **kwargs)
    if link.status == 'not_checked':
        raise NegotiationError(link.reason)
    return link.tasks


def negotiate_plan(*args, now_s: int = 0, **kwargs) -> NegotiationOutcome:
    return link_plan(*args, **kwargs).negotiate(now_s)
