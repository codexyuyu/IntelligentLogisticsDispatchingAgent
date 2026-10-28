"""One application pipeline over current solvers, validators, R08 and R09."""
import json
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from time import monotonic, monotonic_ns, sleep
from uuid import UUID, uuid4, uuid5

from fastapi.encoders import jsonable_encoder
from sqlalchemy import select, text, update
from sqlalchemy.dialects.postgresql import insert

from logistics_agents.negotiation_link import link_plan
from logistics_agents.negotiation_roles import RecoveryDeclaration
from logistics_backend.application.artifacts import ResultArtifactStore
from logistics_backend.application.budgets import solver_budget
from logistics_backend.application.candidates import build_candidate
from logistics_backend.application.optimization import build_transport_problem
from logistics_backend.application.scenario_import import prepare_scenario
from logistics_backend.application.submission import submit_job
from logistics_backend.errors import ServiceError
from logistics_backend.persistence.integration_models import integration_runs, integration_scenarios
from logistics_contracts.integration import IntegrationJobContent, IntegrationRun, ScenarioImport
from logistics_contracts.mapping import (
    budget_dto,
    policy_dto,
    problem_dto,
    scope_dto,
    solution_dto,
    warehouse_problem_dto,
    warehouse_solution_dto,
)
from logistics_contracts.planning import CandidatePlanDTO, MatrixRefDTO
from logistics_contracts.runtime import JobResultRef
from logistics_contracts.transport import TransportProblemDTO, TransportRequestDTO, TransportSolutionDTO
from logistics_contracts.warehouse import WarehouseProblemDTO, WarehouseSolutionDTO
from logistics_domain.metrics import MetricSource
from logistics_domain.planning import (
    DisturbanceWeights,
    ObjectivePolicy,
    SolveBudget,
    SolveStatus,
    content_hash,
)
from logistics_domain.primitives import TimeWindow
from logistics_domain.states import ErrorCode, JobKind, JobOptimizationMode, JobStatus
from logistics_domain.transport import RoutingNodeKind
from logistics_domain.warehouse import WarehouseProblem
from logistics_evaluation.complete import MetricInput, OrderOutcome, ResourceUse, Span, calculate_metrics
from logistics_optimization.transport.solver import OrToolsTransportSolver
from logistics_optimization.validation.joint import validate_joint
from logistics_optimization.validation.transport import validate_transport
from logistics_optimization.warehouse.solver import CpSatWarehouseScheduler

FEASIBLE = (SolveStatus.OPTIMAL, SolveStatus.FEASIBLE)
NAMESPACE = UUID('f254be67-7058-4a24-9714-edab05450c89')


def _observations(problem, warehouse, transport_problem, transport, scope_id):
    snapshot = problem.snapshot
    nodes = {n.id: n for n in transport_problem.nodes}
    deliveries = {nodes[s.node_id].order_id: s for s in transport.stops
                  if s.node_id in nodes and nodes[s.node_id].kind == RoutingNodeKind.DELIVERY}
    pickups = {nodes[s.node_id].order_id: s for s in transport.stops
               if s.node_id in nodes and nodes[s.node_id].kind == RoutingNodeKind.PICKUP}
    resource_spans, task_starts, task_ends, route_stops = {}, {}, {}, {}
    for assignment in warehouse.assignments:
        resource_spans.setdefault(assignment.resource_id, []).append(
            Span(assignment.start_s, assignment.end_s, assignment.units))
        task_starts[assignment.task_id] = min(task_starts.get(assignment.task_id, assignment.start_s), assignment.start_s)
        task_ends[assignment.task_id] = max(task_ends.get(assignment.task_id, 0), assignment.end_s)
    for setup in warehouse.setup_operations:
        resource_spans.setdefault(setup.resource_id, []).append(Span(setup.start_s, setup.end_s))
    for stop in transport.stops:
        route_stops.setdefault(stop.route_id, []).append(stop)
    outcomes = tuple(OrderOutcome(str(o.id), deliveries[o.id].departure_s if o.id in deliveries else None,
        o.soft_due_at_s, o.delivery_window.latest_s, 0,
        service_started_s=deliveries[o.id].service_start_s if o.id in deliveries else None) for o in snapshot.orders)
    def resources(items):
        return tuple(ResourceUse(str(item.id), tuple(resource_spans.get(item.id, ())),
            tuple(Span(i.start_s, i.end_s, i.available_units) for i in item.calendar.intervals)) for item in items)
    route_by_vehicle = {r.vehicle_id: r for r in transport.candidate.routes}
    vehicles = []
    drivers = {d.id: d for d in snapshot.drivers}
    for vehicle in snapshot.vehicles:
        route = route_by_vehicle.get(vehicle.id)
        stops = route_stops.get(route.id, ()) if route else ()
        used = (Span(min(s.arrival_s for s in stops), max(s.departure_s for s in stops)),) if stops else ()
        state = next(s for s in transport_problem.vehicles if s.vehicle_id == vehicle.id)
        driver = drivers.get(vehicle.driver_id)
        lower = max(state.available_window.earliest_s, driver.shift.earliest_s if driver else 0)
        upper = min(state.available_window.latest_s, driver.shift.latest_s if driver else snapshot.scope.horizon_s)
        available = tuple(Span(max(lower, i.start_s), min(upper, i.end_s))
            for i in vehicle.calendar.intervals if i.available_units and max(lower, i.start_s) < min(upper, i.end_s))
        vehicles.append(ResourceUse(str(vehicle.id), used, available))
    occupancies, zone_use = [], {}
    cold = snapshot.coldchain
    locations = {location.location_id: location for location in cold.storage_locations}
    for item in cold.occupancies:
        start = task_ends[item.inbound_operation_id] if item.inbound_operation_id else (item.declared_start_s or 0)
        end = task_starts[item.outbound_operation_id] if item.outbound_operation_id else cold.horizon_s
        occupancies.append({'occupancy_id': str(item.occupancy_id), 'batch_id': item.batch_id,
                            'location_id': str(item.location_id), 'start_s': start, 'end_s': end})
        volume = next((c.amount for c in item.capacity_use if c.unit.value == 'volume_cm3'), None)
        if volume is not None:
            zone_use.setdefault(locations[item.location_id].zone_id, []).append(Span(start, end, volume))
    zones = tuple(ResourceUse(str(z.zone_id), tuple(zone_use.get(z.zone_id, ())),
        (Span(0, cold.horizon_s, next(c.amount for c in z.capacities if c.unit.value == 'volume_cm3')),))
        for z in cold.zones if any(c.unit.value == 'volume_cm3' for c in z.capacities))
    cost = transport.candidate.cost
    data = MetricInput(str(scope_id), MetricSource.PLANNED, 0, snapshot.scope.horizon_s,
        orders=outcomes, distance_m=sum(r.total_distance_m for r in transport.candidate.routes),
        transport_cost_cents=cost.distance_cents+cost.fixed_vehicle_cents+cost.service_cents+cost.overtime_cents,
        vehicles=tuple(vehicles), warehouse_zones=zones or None,
        docks=resources(snapshot.resources.docks), equipment=resources(snapshot.resources.equipment),
        solve_ms=(warehouse.engine_metadata.solve_ms+transport.engine_metadata.solve_ms,))
    return {'metrics': jsonable_encoder(calculate_metrics(data)), 'coldchain': {
        'rule_version': cold.rule_version, 'occupancies': occupancies,
        'locations': jsonable_encoder(cold.storage_locations), 'zones': jsonable_encoder(cold.zones)},
        'handoffs': [{'order_id': str(task.order_id), 'task_id': str(task.id),
            'warehouse_ready_s': task_ends[task.id],
            'pickup_start_s': pickups[task.order_id].service_start_s if task.order_id in pickups else None}
                    for task in problem.tasks if task.order_id is not None]}


def solve_imported(command: ScenarioImport, request: IntegrationRun, scope_id, *, rule_baseline=False, actor_id=None, deadline=None):
    """Compute from immutable imported evidence; no client-provided solution is trusted."""
    prepared = prepare_scenario(command)
    if prepared['status'] != 'checked':
        return prepared
    command = ScenarioImport.model_validate(prepared['payload'])
    snapshot = command.snapshot.to_domain()
    started = monotonic_ns()
    now = datetime.now(UTC).replace(microsecond=0)
    budget = SolveBudget(request.budget_ms, deadline or now+timedelta(seconds=30), 1, request.seed, worker_count=1)
    policy = ObjectivePolicy('1.0.0', 100000, 1, 1, DisturbanceWeights(0, 0, 0, 0))
    tasks = tuple(t.to_domain() for t in command.warehouse_tasks)
    problem = WarehouseProblem(snapshot, tasks, policy, budget, command.setup_policy.to_domain())
    solve_problem = problem
    if rule_baseline:
        # Earliest-deadline serial rule; CP-SAT fixes and checks every proposed time.
        cursor, fixed = 0, []
        for task in sorted(tasks, key=lambda t: (t.window.latest_s, str(t.id))):
            cursor = max(cursor, task.window.earliest_s)
            if cursor+task.duration_s > task.window.latest_s:
                return {'status': 'not_checked', 'reason': 'rule_baseline_window_infeasible'}
            fixed.append(replace(task, window=TimeWindow(cursor, cursor+task.duration_s)))
            cursor += task.duration_s
        solve_problem = replace(problem, tasks=tuple(fixed))
    warehouse = CpSatWarehouseScheduler().solve(solve_problem, budget)
    base = {'schema_version': '2.0.0', 'source_kind': command.source_kind, 'source_ref': command.source_ref,
            'source_verified': False, 'request': request.model_dump(mode='json'), 'revocations': [],
            'snapshot_hash': snapshot.hash, 'warehouse_problem': warehouse_problem_dto(solve_problem).model_dump(mode='json'),
            'warehouse_solution': warehouse_solution_dto(warehouse).model_dump(mode='json')}
    if warehouse.status not in FEASIBLE or not warehouse.validation or not warehouse.validation.valid:
        return {**base, 'status': 'not_checked', 'reason': 'warehouse_not_independently_validated'}
    matrix = snapshot.matrices[0] if snapshot.matrices else None
    if matrix is None:
        return {**base, 'status': 'not_checked', 'reason': 'travel_matrix_missing'}
    transport_request = TransportRequestDTO(scope=scope_dto(snapshot.scope), order_ids=snapshot.scope.order_ids,
        vehicle_ids=snapshot.scope.vehicle_ids, matrix_ref=MatrixRefDTO(matrix_id=matrix.id, version=matrix.version,
        hash=matrix.hash), budget=budget_dto(budget), objective_policy=policy_dto(policy))
    transport_problem = build_transport_problem(snapshot, transport_request)
    ready = {}
    task_ends = {}
    for assignment in warehouse.assignments:
        task_ends[assignment.task_id] = max(task_ends.get(assignment.task_id, 0), assignment.end_s)
    for task in tasks:
        ready[task.order_id] = max(ready.get(task.order_id, 0), task_ends[task.id])
    nodes = []
    for node in transport_problem.nodes:
        earliest = max(node.hard_window.earliest_s, ready.get(node.order_id, 0)) if node.kind == RoutingNodeKind.PICKUP else node.hard_window.earliest_s
        if earliest > node.hard_window.latest_s:
            return {**base, 'status': 'not_checked', 'reason': 'handoff_outside_transport_window'}
        nodes.append(replace(node, hard_window=TimeWindow(earliest, node.hard_window.latest_s)))
    drivers = {d.id: d for d in snapshot.drivers}
    states = []
    for state in transport_problem.vehicles:
        driver = drivers.get(state.driver_id)
        if driver is None:
            return {**base, 'status': 'not_checked', 'reason': 'driver_evidence_missing'}
        lower = max(state.available_window.earliest_s, driver.shift.earliest_s, command.available_at_s[state.vehicle_id])
        upper = min(state.available_window.latest_s, driver.shift.latest_s)
        if lower >= upper:
            return {**base, 'status': 'not_checked', 'reason': 'vehicle_unavailable'}
        states.append(replace(state, available_window=TimeWindow(lower, upper)))
    transport_problem = replace(transport_problem, nodes=tuple(nodes), vehicles=tuple(states))
    remaining = request.budget_ms-int((monotonic_ns()-started)/1_000_000)
    if remaining <= 0:
        return {**base, 'status': 'not_checked', 'reason': 'budget_exhausted'}
    transport = OrToolsTransportSolver().solve(transport_problem, replace(budget, wall_time_ms=remaining))
    if transport.status not in FEASIBLE:
        return {**base, 'status': 'not_checked', 'reason': 'transport_infeasible'}
    transport = replace(transport, validation=validate_transport(transport.candidate, transport_problem, transport.stops))
    joint = validate_joint(transport.candidate, transport_problem, transport.stops, solve_problem, warehouse)
    base.update(transport_problem=problem_dto(transport_problem).model_dump(mode='json'),
                transport_solution=solution_dto(transport).model_dump(mode='json'), joint_validation=jsonable_encoder(joint))
    if not joint.valid:
        return {**base, 'status': 'not_checked', 'reason': 'joint_validation_failed'}
    candidate = build_candidate(schedule_id=request.scenario_id, snapshot=snapshot,
        plan=transport.candidate, stops=transport.stops, actor_id=actor_id or UUID(int=0), now=now,
        warehouse_solution=warehouse,
        solver_evidence_refs=tuple(e.id for e in (*warehouse.solver_evidence, *transport.solver_evidence)))
    link = link_plan(solve_problem, warehouse, candidate=candidate, transport_problem=transport_problem,
        transport_solution=transport, available_at_s=command.available_at_s,
        recoveries=tuple(RecoveryDeclaration(str(r.task_id), str(r.resource_id), r.disruption_at_s, r.recovery_s) for r in request.recoveries))
    outcome = link.negotiate()
    return {**base, 'status': outcome.status, 'reason': outcome.reason,
        'candidate': jsonable_encoder(candidate), 'available_at_s': {str(k): v for k, v in command.available_at_s.items()},
        'negotiation': jsonable_encoder(outcome), 'observations': _observations(solve_problem, warehouse, transport_problem, transport, scope_id),
        'total_elapsed_ms': (monotonic_ns()-started)/1_000_000}


class IntegrationJobHandler:
    family = JobKind.OPTIMIZATION
    mode = JobOptimizationMode.JOINT

    def __init__(self, result_store=None):
        self.result_store = result_store or ResultArtifactStore()

    def validate(self, content):
        from pydantic import ValidationError

        from logistics_domain.errors import InvalidInputError
        try:
            IntegrationJobContent.model_validate_json(content)
        except ValidationError as exc:
            raise InvalidInputError("invalid joint optimization input") from exc

    def execute(self, content, deadline):
        payload = IntegrationJobContent.model_validate_json(content)
        requested = SolveBudget(payload.request.budget_ms, deadline.expires_at_utc,
                                1, payload.request.seed, worker_count=1)
        budget = solver_budget(deadline, requested, server_limit_ms=12000)
        request = payload.request.model_copy(update={"budget_ms": budget.wall_time_ms})
        result = solve_imported(payload.scenario, request, payload.scope_id,
                               actor_id=payload.actor_id, deadline=deadline.expires_at_utc)
        # Preserve the accepted request; the effective worker budget is execution metadata.
        result["request"] = payload.request.model_dump(mode="json")
        result["effective_budget_ms"] = budget.wall_time_ms
        result_id = uuid4()
        digest = self.result_store.write(result_id, result)
        return JobResultRef(result_id=result_id, version=1, schema_version="2.0.0",
                            hash=digest, family=JobKind.OPTIMIZATION)


class IntegrationService:
    def __init__(self, uow_factory, workspace_id, jobs=None, result_store=None):
        self.uow_factory, self.workspace_id = uow_factory, workspace_id
        self.jobs = jobs
        self.result_store = result_store or ResultArtifactStore()

    def _scope(self, actor):
        if actor.scope_id != self.workspace_id:
            raise ServiceError(ErrorCode.FORBIDDEN, 'scope mismatch')

    def import_scenario(self, command, actor):
        self._scope(actor)
        prepared = prepare_scenario(command)
        if prepared['status'] != 'checked':
            return prepared
        identity = uuid5(NAMESPACE, f'{actor.scope_id}:{prepared["input_hash"]}')
        with self.uow_factory() as uow:
            uow.connection.execute(insert(integration_scenarios).values(id=identity, scope_id=actor.scope_id,
                input_hash=prepared['input_hash'], created_at=datetime.now(UTC), created_by=actor.actor_id,
                payload=prepared['payload']).on_conflict_do_nothing())
        return {k: v for k, v in {**prepared, 'scenario_id': str(identity)}.items() if k != 'payload'}

    def list_scenarios(self, actor):
        self._scope(actor)
        with self.uow_factory() as uow:
            rows = uow.connection.execute(select(integration_scenarios).where(
                integration_scenarios.c.scope_id == actor.scope_id).order_by(integration_scenarios.c.created_at.desc()).limit(50)).mappings().all()
        return {'items': [{'id': str(r['id']), 'name': r['payload']['name'], 'source_kind': r['payload']['source_kind'],
                           'input_hash': r['input_hash']} for r in rows]}

    def scenario(self, identity, actor):
        self._scope(actor)
        with self.uow_factory() as uow:
            row = uow.connection.execute(select(integration_scenarios).where(
                integration_scenarios.c.id == identity, integration_scenarios.c.scope_id == actor.scope_id)).mappings().first()
        if row is None:
            raise ServiceError(ErrorCode.NOT_FOUND, 'scenario not found')
        return ScenarioImport.model_validate(row['payload'])

    def submit(self, request, actor, key, trace_id=None):
        self._scope(actor)
        if not key or len(key) > 128:
            raise ServiceError(ErrorCode.INVALID_INPUT, 'invalid idempotency key')
        digest = content_hash(request.model_dump(mode='json'))
        identity = uuid5(NAMESPACE, f'{actor.scope_id}:{key}')
        lock_id = int.from_bytes(identity.bytes[:8], 'big', signed=True)
        with self.uow_factory() as uow:
            # Preserve scope-wide integration idempotency, including concurrent actors.
            uow.connection.execute(text('SELECT pg_advisory_xact_lock(:identity)'), {'identity': lock_id})
            row = uow.connection.execute(select(integration_runs).where(
                integration_runs.c.id == identity, integration_runs.c.scope_id == actor.scope_id)).mappings().first()
            if row:
                if row['request_hash'] != digest:
                    raise ServiceError(ErrorCode.IDEMPOTENCY_CONFLICT, 'key already used with different input')
                return row['id'], row['payload']
            if self.jobs is None:
                raise ServiceError(ErrorCode.DEPENDENCY_UNAVAILABLE, 'joint job service is unavailable')
            receipt = submit_job(self.jobs, request, actor, key, trace_id or uuid4(),
                kind=JobKind.OPTIMIZATION, mode=JobOptimizationMode.JOINT, connection=uow.connection,
                build_content=lambda: IntegrationJobContent(scenario=self.scenario(request.scenario_id, actor),
                    request=request, scope_id=actor.scope_id, actor_id=actor.actor_id).model_dump(mode='json'))
            result = {**receipt.model_dump(mode='json'), 'run_id': str(identity),
                      'request': request.model_dump(mode='json')}
            uow.connection.execute(insert(integration_runs).values(id=identity, scope_id=actor.scope_id,
                scenario_id=request.scenario_id, request_hash=digest, idempotency_key=key,
                created_at=datetime.now(UTC), created_by=actor.actor_id, payload=result))
        return identity, result

    def run(self, request, actor, key, trace_id=None, *, wait=True):
        identity, payload = self.submit(request, actor, key, trace_id)
        if not wait or 'job_id' not in payload:
            return payload
        until = monotonic() + 56
        while True:
            result = self.get(identity, actor)
            if result.get('status') not in ('queued', 'running'):
                return result
            if monotonic() >= until:
                raise ServiceError(ErrorCode.DEPENDENCY_UNAVAILABLE,
                    f'job still pending; retrieve integration run {identity}')
            sleep(0.25)

    def get(self, identity, actor):
        self._scope(actor)
        with self.uow_factory() as uow:
            row = uow.connection.execute(select(integration_runs).where(integration_runs.c.id == identity,
                integration_runs.c.scope_id == actor.scope_id)).mappings().first()
        if not row:
            raise ServiceError(ErrorCode.NOT_FOUND, 'run not found')
        payload = row['payload']
        if 'job_id' not in payload or payload.get('status') not in ('queued', 'running'):
            return payload
        job = self.jobs.get(UUID(payload['job_id']), actor)
        if job.status in (JobStatus.QUEUED, JobStatus.RUNNING):
            return {**payload, 'status': job.status.value}
        if job.status == JobStatus.COMPLETED:
            result = json.loads(self.result_store.read(job.result_ref.result_id, job.result_ref.hash))
            result.update(run_id=str(identity), job_id=payload['job_id'])
        else:
            result = {**payload, 'status': job.status.value,
                      'error': job.error.model_dump(mode='json') if job.error else None}
        with self.uow_factory() as uow:
            # Another reader/revoker may already have materialized or changed the result.
            current = uow.connection.execute(select(integration_runs).where(
                integration_runs.c.id == identity, integration_runs.c.scope_id == actor.scope_id)
                .with_for_update()).mappings().one()
            if current['payload'].get('status') not in ('queued', 'running'):
                return current['payload']
            uow.connection.execute(update(integration_runs).where(integration_runs.c.id == identity).values(payload=result))
        return result

    def revoke(self, identity, command, actor):
        self._scope(actor)
        with self.uow_factory() as uow:
            row = uow.connection.execute(select(integration_runs).where(integration_runs.c.id == identity,
                integration_runs.c.scope_id == actor.scope_id).with_for_update()).mappings().first()
            if not row:
                raise ServiceError(ErrorCode.NOT_FOUND, 'run not found')
            payload = dict(row['payload'])
            if payload.get('status') != 'checked' or payload['negotiation']['result']['digest'] != command.expected_digest:
                raise ServiceError(ErrorCode.RESOURCE_CONFLICT, 'negotiation digest changed or was not checked')
            request = IntegrationRun.model_validate(payload['request'])
            link = link_plan(WarehouseProblemDTO.model_validate(payload['warehouse_problem']).to_domain(),
                WarehouseSolutionDTO.model_validate(payload['warehouse_solution']).to_domain(),
                candidate=CandidatePlanDTO.model_validate(payload['candidate']).to_domain(),
                transport_problem=TransportProblemDTO.model_validate(payload['transport_problem']).to_domain(),
                transport_solution=TransportSolutionDTO.model_validate(payload['transport_solution']).to_domain(),
                available_at_s={UUID(k): v for k, v in payload['available_at_s'].items()},
                recoveries=tuple(RecoveryDeclaration(str(r.task_id), str(r.resource_id), r.disruption_at_s, r.recovery_s) for r in request.recoveries))
            previous = link.negotiate().result
            if previous is None:
                raise ServiceError(ErrorCode.UNVERIFIED_SOLVER_RESULT, 'stored evidence no longer validates')
            for prior in payload['revocations']:
                previous = link.coordinator.revoke(prior['task_id'], prior['now_s'])
            if previous.digest != command.expected_digest or not link.coordinator.award_of(str(command.task_id)):
                raise ServiceError(ErrorCode.RESOURCE_CONFLICT, 'award absent or replay digest differs')
            if command.now_s < max(m.at_s for m in previous.transcript):
                raise ServiceError(ErrorCode.INVALID_INPUT, 'revocation precedes transcript clock')
            result = link.coordinator.revoke(str(command.task_id), command.now_s)
            payload['negotiation']['result'] = jsonable_encoder(result)
            payload['revocations'] = [*payload['revocations'], {'task_id': str(command.task_id), 'now_s': command.now_s}]
            uow.connection.execute(update(integration_runs).where(integration_runs.c.id == identity).values(payload=payload))
        return payload
