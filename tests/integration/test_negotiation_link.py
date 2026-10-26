"""Actual CP-SAT + Routing -> current CandidatePlan -> one R08 coordinator."""
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from uuid import UUID

import pytest
from tests.unit.test_negotiation_roles import EPOCH, scenario

from logistics_agents.contract_net import NegotiationError
from logistics_agents.negotiation_link import link_plan, negotiate_plan, tasks_from_plan
from logistics_agents.negotiation_roles import RecoveryDeclaration
from logistics_backend.application.optimization import build_transport_problem
from logistics_contracts.mapping import budget_dto, policy_dto, scope_dto
from logistics_contracts.planning import MatrixRefDTO
from logistics_contracts.transport import TransportRequestDTO
from logistics_domain.planning import (
    CandidatePlan,
    CostBreakdown,
    DisturbanceWeights,
    ObjectivePolicy,
    ScheduleTask,
    SolveBudget,
    SolveStatus,
    TaskKind,
    WarehousePlan,
    content_hash,
)
from logistics_domain.states import EntityState
from logistics_domain.warehouse import WarehouseProblem
from logistics_optimization.transport.solver import OrToolsTransportSolver
from logistics_optimization.validation.transport import validate_transport
from logistics_optimization.validation.warehouse import validate_warehouse
from logistics_optimization.warehouse.solver import CpSatWarehouseScheduler


def rehash(candidate):
    body = {name: getattr(candidate, name) for name in (
        'schedule_id', 'snapshot_id', 'snapshot_hash', 'epoch_utc', 'horizon_s',
        'transport_plan', 'warehouse_plan', 'task_assignments', 'objective', 'solver_evidence_refs')}
    return replace(candidate, content_hash=content_hash(body))


@pytest.fixture(scope='module')
def solved():
    snapshot, tasks, _ = scenario()
    # Warehouse handling and solved pickup service have different durations.
    tasks = tuple(replace(task, duration_s=20) for task in tasks)
    policy = ObjectivePolicy('1.0.0', 0, 0, 0, DisturbanceWeights(0, 0, 0, 0))
    budget = SolveBudget(1000, datetime.now(UTC).replace(microsecond=0) + timedelta(minutes=5), 1, 0)
    problem = WarehouseProblem(snapshot, tasks, policy, budget)
    solution = CpSatWarehouseScheduler().solve(problem, budget)
    assert solution.status in (SolveStatus.OPTIMAL, SolveStatus.FEASIBLE)
    solution = replace(solution, validation=validate_warehouse(problem, solution))
    assert solution.validation.valid
    matrix = snapshot.matrices[0]
    request = TransportRequestDTO(scope=scope_dto(snapshot.scope), order_ids=snapshot.scope.order_ids,
        vehicle_ids=snapshot.scope.vehicle_ids, matrix_ref=MatrixRefDTO(matrix_id=matrix.id,
        version=matrix.version, hash=matrix.hash), budget=budget_dto(budget), objective_policy=policy_dto(policy))
    transport_problem = build_transport_problem(snapshot, request)
    transport_solution = OrToolsTransportSolver().solve(transport_problem, budget)
    assert transport_solution.status in (SolveStatus.OPTIMAL, SolveStatus.FEASIBLE)
    transport_solution = replace(transport_solution, validation=validate_transport(
        transport_solution.candidate, transport_problem, transport_solution.stops))
    assert transport_solution.validation.valid
    candidate_id = UUID(int=8500)
    assignments = tuple(ScheduleTask(id=UUID(int=8600+i), status=EntityState.PLANNED,
        created_at=EPOCH, updated_at=EPOCH, row_version=0, schema_version='2.0.0', created_by=UUID(int=1),
        version_id=candidate_id, task_id=t.id, task_kind=TaskKind.WAREHOUSE,
        assigned_resource_ids=tuple(a.resource_id for a in solution.assignments if a.task_id == t.id),
        planned_start_s=min(a.start_s for a in solution.assignments if a.task_id == t.id),
        planned_end_s=max(a.end_s for a in solution.assignments if a.task_id == t.id), sequence=None)
        for i, t in enumerate(tasks))
    cost = CostBreakdown(0, 0, solution.objective.business_cost_cents, 0, 0,
                         solution.objective.business_cost_cents)
    candidate = rehash(CandidatePlan(id=candidate_id, schedule_id=UUID(int=8501), base_version_id=None,
        snapshot_id=snapshot.id, snapshot_hash=snapshot.hash, epoch_utc=snapshot.scope.epoch_utc,
        horizon_s=snapshot.scope.horizon_s, transport_plan=transport_solution.candidate,
        warehouse_plan=WarehousePlan(solution.assignments, (), (), cost), task_assignments=assignments,
        objective=solution.objective, content_hash='0'*64,
        solver_evidence_refs=tuple(e.id for e in (*solution.solver_evidence, *transport_solution.solver_evidence))))
    options = dict(candidate=candidate, transport_problem=transport_problem,
                   transport_solution=transport_solution,
                   available_at_s={v.id: 0 for v in snapshot.vehicles})
    return problem, solution, options


def test_real_solvers_bind_two_tasks_resources_vehicle_handoffs_and_transcript(solved):
    problem, solution, options = solved
    declarations = tuple(RecoveryDeclaration(str(a.task_id), str(a.resource_id), 0, 20)
                         for a in solution.assignments)
    link = link_plan(problem, solution, **options, recoveries=declarations)
    assert link.status == 'checked', link.reason
    assert len(link.tasks) == 2
    for binding, spec in zip(link.bindings, link.tasks, strict=True):
        actual = [a for a in solution.assignments if a.task_id == binding.task_id]
        assert binding.resource_ids == tuple(a.resource_id for a in actual)
        assert binding.handoff_ready_at_s == max(a.end_s for a in actual)
        assert binding.vehicle_id in {r.vehicle_id for r in options['candidate'].transport_plan.routes}
        assert spec.task_id == str(binding.task_id)
        assert str(binding.vehicle_id) in spec.exclusive_resource_ids
    first = link.negotiate()
    second = negotiate_plan(problem, solution, **options, recoveries=declarations)
    assert first == second
    assert first.result.status == 'confirmed'
    assert len(first.result.awards) == 2
    assert {m.role for m in first.result.transcript if m.kind == 'bid'} == {'warehouse', 'transport', 'exception'}
    transport_bids = [m for m in first.result.transcript if m.kind == 'bid' and m.role == 'transport']
    assert len(transport_bids) == 2
    assert all('cost=30;window=[20,50)' in m.detail for m in transport_bids)
    assert link.negotiate() == first
    revoked = link.coordinator.revoke(link.tasks[0].task_id, 120)
    assert revoked.outcome_of(link.tasks[0].task_id) == 'revoked'
    assert link.coordinator.award_of(link.tasks[0].task_id) is None


def test_warehouse_only_solved_tasks_do_not_invent_vehicle_or_disruption(solved):
    problem, solution, _ = solved
    outcome = negotiate_plan(problem, solution)
    assert outcome.status == 'checked' and outcome.result.status == 'confirmed'
    assert all(b.vehicle_id is None for b in outcome.bindings)
    assert {m.role for m in outcome.result.transcript if m.kind == 'bid'} == {'warehouse'}


@pytest.mark.parametrize('mutation', [
    'missing_solution', 'missing_evidence', 'wrong_input', 'wrong_assignment_hash',
    'missing_validation', 'invalid_validation', 'wrong_validation_hash',
    'missing_transport', 'missing_availability', 'wrong_snapshot', 'wrong_candidate_hash',
    'missing_candidate_refs', 'changed_resource', 'changed_warehouse_window', 'changed_stop',
])
def test_incomplete_or_stale_evidence_is_not_checked_with_no_bids(solved, mutation):
    problem, solution, original = solved
    options = dict(original)
    candidate = options['candidate']
    if mutation == 'missing_solution':
        solution = None
    elif mutation == 'missing_evidence':
        solution = replace(solution, solver_evidence=())
    elif mutation in ('wrong_input', 'wrong_assignment_hash'):
        field = 'input_hash' if mutation == 'wrong_input' else 'assignment_hash'
        solution = replace(solution, solver_evidence=(replace(solution.solver_evidence[0], **{field: 'a'*64}),))
    elif mutation == 'missing_validation':
        solution = replace(solution, validation=None)
    elif mutation == 'invalid_validation':
        solution = replace(solution, validation=replace(solution.validation, valid=False))
    elif mutation == 'wrong_validation_hash':
        solution = replace(solution, validation=replace(solution.validation, candidate_hash='a'*64))
    elif mutation == 'missing_transport':
        options['transport_solution'] = None
    elif mutation == 'missing_availability':
        options['available_at_s'] = {}
    elif mutation == 'wrong_snapshot':
        options['candidate'] = replace(candidate, snapshot_hash='a'*64)
    elif mutation == 'wrong_candidate_hash':
        options['candidate'] = replace(candidate, content_hash='a'*64)
    elif mutation == 'missing_candidate_refs':
        options['candidate'] = rehash(replace(candidate, solver_evidence_refs=()))
    elif mutation == 'changed_resource':
        task = replace(candidate.task_assignments[0], assigned_resource_ids=(UUID(int=999),))
        options['candidate'] = rehash(replace(candidate, task_assignments=(task, *candidate.task_assignments[1:])))
    elif mutation == 'changed_warehouse_window':
        changed = replace(solution.assignments[0], start_s=10, end_s=40)
        solution = replace(solution, assignments=(changed, *solution.assignments[1:]))
    elif mutation == 'changed_stop':
        transport = options['transport_solution']
        changed = replace(transport.stops[0], departure_s=transport.stops[0].departure_s+1)
        options['transport_solution'] = replace(transport, stops=(changed, *transport.stops[1:]))
    link = link_plan(problem, solution, **options)
    assert link.status == 'not_checked' and link.reason
    assert link.tasks == () and link.coordinator is None
    assert link.negotiate().result is None
    with pytest.raises(NegotiationError):
        tasks_from_plan(problem, solution, **options)


def test_changed_availability_changes_digest_and_never_squeezes_transport_window(solved):
    problem, solution, options = solved
    before = negotiate_plan(problem, solution, **options)
    options = {**options, 'available_at_s': {v.id: 700 for v in problem.snapshot.vehicles}}
    after = negotiate_plan(problem, solution, **options)
    assert after.status == 'checked'
    assert after.result.digest != before.result.digest
    assert not [m for m in after.result.transcript if m.kind == 'bid' and m.role == 'transport']


def test_changed_recovery_resource_is_rejected(solved):
    problem, solution, options = solved
    recovery = RecoveryDeclaration(str(problem.tasks[0].id), 'invented-resource', 0, 10)
    result = negotiate_plan(problem, solution, **options, recoveries=(recovery,))
    assert result.status == 'not_checked' and result.result is None
