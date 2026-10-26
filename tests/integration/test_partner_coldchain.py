"""Real CP-SAT with hand-computed capacity, calendar and handoff cases."""
from dataclasses import fields, replace
from datetime import UTC, datetime, timedelta
from uuid import UUID

from tests.unit.test_negotiation_roles import EPOCH, scenario

from logistics_domain.coldchain import (
    BatchCompatibility,
    CapacityAmount,
    CapacityPeriod,
    CapacityUnit,
    ColdChainSnapshot,
    ColdChainStorageLocation,
    ColdChainZone,
    ExposureLimit,
    ExposureScope,
    ReuseRule,
    StorageOccupancy,
)
from logistics_domain.planning import (
    DisturbanceWeights,
    ObjectivePolicy,
    PlanningSnapshot,
    SolveBudget,
    SolveStatus,
    bind_calendar,
)
from logistics_domain.primitives import CalendarInterval, ResourceCalendar, TimeWindow
from logistics_domain.warehouse import WarehouseProblem
from logistics_optimization.validation.coldchain import validate_coldchain
from logistics_optimization.validation.joint import validate_joint
from logistics_optimization.warehouse.solver import CpSatWarehouseScheduler


def rebuild(snapshot, **changes):
    return PlanningSnapshot.create(**{**{f.name: getattr(snapshot, f.name) for f in fields(snapshot)
                                        if f.name != 'hash'}, **changes})


def cold_problem(horizon=86400, second_start=0, capacity=5):
    snapshot, tasks, _ = scenario(((0, horizon, 1),))
    warehouse = snapshot.resources.warehouses[0]
    calendar = ResourceCalendar(EPOCH, (CalendarInterval(0, horizon, 1),), 1)
    warehouse_ids = {w.id for w in snapshot.resources.warehouses}
    bundle = replace(snapshot.resources, warehouses=tuple(replace(w, calendar=calendar)
                    for w in snapshot.resources.warehouses), calendars=tuple(
                        bind_calendar(b.resource_id, calendar, calendar) if b.resource_id in warehouse_ids else b
                        for b in snapshot.resources.calendars))
    tasks = (replace(tasks[0], window=TimeWindow(60, 90)),
             replace(tasks[1], window=TimeWindow(second_start, max(200, second_start+60))))
    amount = (CapacityAmount(CapacityUnit.VOLUME_CM3, 5),)
    zone = ColdChainZone(UUID(int=9100), warehouse.id, 1, 40,
                         (CapacityAmount(CapacityUnit.VOLUME_CM3, 20),))
    location = ColdChainStorageLocation(UUID(int=9101), warehouse.id, zone.zone_id, 1,
        (CapacityAmount(CapacityUnit.VOLUME_CM3, 10),), capacity_periods=(
        CapacityPeriod(0, 50, (CapacityAmount(CapacityUnit.VOLUME_CM3, 10),)),
        CapacityPeriod(50, horizon, (CapacityAmount(CapacityUnit.VOLUME_CM3, capacity),))))
    occupancies = (StorageOccupancy(UUID(int=9102), 'initial', location.location_id, amount,
                     'initial_stock', outbound_operation_id=tasks[0].id),
                   StorageOccupancy(UUID(int=9103), 'incoming', location.location_id, amount,
                     'planned_inbound', inbound_operation_id=tasks[1].id))
    cold = ColdChainSnapshot('test-1', horizon, (zone,), (location,), occupancies,
        exposure_limits=tuple(ExposureLimit(UUID(int=9110+i), b, horizon,
            (ExposureScope.IN_WAREHOUSE,), 'test-1', 'synthetic') for i, b in enumerate(('initial', 'incoming'))),
        batch_compatibility=tuple(BatchCompatibility(b, warehouse.id, 'chilled', 0, 80)
                                  for b in ('initial', 'incoming')))
    snapshot = rebuild(snapshot, resources=bundle, scope=replace(snapshot.scope, horizon_s=horizon), coldchain=cold)
    budget = SolveBudget(2000, datetime.now(UTC).replace(microsecond=0)+timedelta(minutes=2), 1, 7)
    return WarehouseProblem(snapshot, tasks,
        ObjectivePolicy('1.0.0', 0, 0, 0, DisturbanceWeights(0, 0, 0, 0)), budget)


def solve(problem):
    return CpSatWarehouseScheduler().solve(problem, problem.budget)


def test_capacity_drop_forces_inbound_after_stock_release():
    problem = cold_problem()
    result = solve(problem)
    assert result.status in (SolveStatus.FEASIBLE, SolveStatus.OPTIMAL)
    assert result.validation.valid, result.validation
    by_task = {a.task_id: a for a in result.assignments}
    assert by_task[problem.tasks[1].id].end_s >= by_task[problem.tasks[0].id].start_s == 60
    # Independently tamper the inbound result to create overload across the drop.
    bad = replace(result, assignments=tuple(replace(a, start_s=0, end_s=30)
                  if a.task_id == problem.tasks[1].id else a for a in result.assignments))
    assert 'coldchain_capacity' in {v.code for v in validate_coldchain(problem, bad).violations}


def test_reuse_rule_is_reported_checked_without_changing_solved_times():
    problem = cold_problem(horizon=604800, second_start=2*86400)
    cold = problem.snapshot.coldchain
    location = cold.storage_locations[0]
    cold = replace(cold, reuse_rules=(ReuseRule(location.location_id, 604800, 3600),))
    problem = replace(problem, snapshot=rebuild(problem.snapshot, coldchain=cold))
    result = solve(problem)
    assert result.status in (SolveStatus.FEASIBLE, SolveStatus.OPTIMAL)
    outcome = validate_coldchain(problem, result)
    assert 'r05.reuse' in outcome.checked
    assert not [v for v in outcome.violations if v.code == 'coldchain_reuse_gap']


def test_seven_day_capacity_is_reused_after_release_not_summed_forever():
    problem = cold_problem(horizon=604800, second_start=2*86400)
    result = solve(problem)
    assert result.status in (SolveStatus.FEASIBLE, SolveStatus.OPTIMAL)
    assert result.validation.valid
    assert max(a.end_s for a in result.assignments) == 2*86400+30


def test_unavoidable_capacity_deficit_is_infeasible():
    problem = cold_problem(capacity=4)
    result = solve(problem)
    assert result.status == SolveStatus.INFEASIBLE
    assert not result.assignments


def test_resource_calendar_gap_and_task_end_are_hard_constraints():
    snapshot, tasks, _ = scenario(((0, 20, 1), (60, 100, 1)))
    base = cold_problem()
    problem = replace(base, snapshot=snapshot, tasks=(replace(tasks[0], window=TimeWindow(0, 90)),))
    result = solve(problem)
    assert result.assignments[0].start_s == 60
    assert result.assignments[0].end_s == 90
    assert solve(replace(problem, tasks=(replace(problem.tasks[0], window=TimeWindow(0, 89)),))).status == SolveStatus.INFEASIBLE


def test_missing_coldchain_operation_evidence_never_returns_feasible():
    problem = cold_problem()
    cold = problem.snapshot.coldchain
    cold = replace(cold, occupancies=(replace(cold.occupancies[0], outbound_operation_id=UUID(int=999)),))
    result = solve(replace(problem, snapshot=rebuild(problem.snapshot, coldchain=cold)))
    assert result.status == SolveStatus.UNKNOWN and not result.assignments


def test_joint_rejects_pickup_before_warehouse_ready():
    from tests.integration.test_negotiation_link import solved
    problem, result, options = solved.__wrapped__()
    good = validate_joint(options['candidate'].transport_plan, options['transport_problem'],
                          options['transport_solution'].stops, problem, result)
    assert good.valid
    late = replace(result, assignments=tuple(replace(a, start_s=580, end_s=600) for a in result.assignments))
    report = validate_joint(options['candidate'].transport_plan, options['transport_problem'],
                            options['transport_solution'].stops, problem, late)
    assert not report.valid
    assert 'handoff_sequence' in {v.code for v in report.violations}
