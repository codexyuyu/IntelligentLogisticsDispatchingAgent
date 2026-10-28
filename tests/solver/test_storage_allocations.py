"""R05 storage intervals must come from the solved CP-SAT occupancy endpoints.

The source fixtures live in tests/integration (A-owned); the new tests and
production changes are kept within B-owned paths.
"""

from dataclasses import replace

from tests.integration.test_partner_coldchain import cold_problem, rebuild, solve

from logistics_domain.coldchain import CapacityAmount, CapacityUnit, ReuseRule
from logistics_domain.planning import SolveStatus
from logistics_optimization.validation.warehouse import validate_warehouse


def _assigned_bounds(result, task_id):
    values = [item for item in result.assignments if item.task_id == task_id]
    assert values
    return min(item.start_s for item in values), max(item.end_s for item in values)


def test_storage_intervals_match_real_operation_endpoints_and_stay_valid():
    problem = cold_problem()
    result = solve(problem)
    assert result.status in (SolveStatus.OPTIMAL, SolveStatus.FEASIBLE)
    assert result.validation.valid, result.validation.violations
    cold = problem.snapshot.coldchain
    by_occupancy = {item.cargo_id: item for item in result.storage_allocations}
    assert set(by_occupancy) == {item.occupancy_id for item in cold.occupancies}
    assert len(result.storage_allocations) == len(cold.occupancies)
    for occupancy in cold.occupancies:
        exported = by_occupancy[occupancy.occupancy_id]
        assert exported.location_id == occupancy.location_id
        expected_start = (_assigned_bounds(result, occupancy.inbound_operation_id)[1]
                          if occupancy.inbound_operation_id else occupancy.declared_start_s or 0)
        expected_end = (_assigned_bounds(result, occupancy.outbound_operation_id)[0]
                        if occupancy.outbound_operation_id else cold.horizon_s)
        assert (exported.start_s, exported.end_s) == (expected_start, expected_end)
        assert (exported.quantity_units, exported.weight_g, exported.volume_cm3) == (0, 0, 5)
    assert validate_warehouse(problem, result).valid


def test_time_phased_capacity_at_boundary_and_overload():
    at_capacity = cold_problem(capacity=5)
    result = solve(at_capacity)
    assert result.validation.valid
    location = at_capacity.snapshot.coldchain.storage_locations[0]
    assert all(item.location_id == location.location_id for item in result.storage_allocations)
    # For each capacity boundary, the half-open intervals' actual concurrent
    # occupancy must not exceed the declared capacity in that period.
    for period in location.capacity_periods:
        for time_s in (period.start_s, period.end_s - 1):
            used = sum(item.volume_cm3 for item in result.storage_allocations
                       if item.start_s <= time_s < item.end_s)
            available = next(amount.amount for amount in period.capacities
                             if amount.unit == CapacityUnit.VOLUME_CM3)
            assert used <= available
    overload = solve(cold_problem(capacity=4))
    assert overload.status == SolveStatus.INFEASIBLE
    assert overload.storage_allocations == ()


def test_seven_day_reuse_cap_exports_real_capped_endpoint():
    problem = cold_problem(horizon=604800, second_start=2 * 86400)
    cold = problem.snapshot.coldchain
    rule = ReuseRule(cold.storage_locations[0].location_id,
                     max_batch_age_s=3600, min_gap_s=0)
    cold = replace(cold, reuse_rules=(rule,))
    problem = replace(problem, snapshot=rebuild(problem.snapshot, coldchain=cold))
    result = solve(problem)
    assert result.validation.valid, result.validation.violations
    entries = {item.cargo_id: item for item in result.storage_allocations}
    first, second = cold.occupancies
    assert entries[first.occupancy_id].end_s == _assigned_bounds(result, first.outbound_operation_id)[0]
    assert entries[second.occupancy_id].start_s == _assigned_bounds(result, second.inbound_operation_id)[1]
    assert entries[second.occupancy_id].end_s == entries[second.occupancy_id].start_s + 3600
    assert entries[first.occupancy_id].end_s <= entries[second.occupancy_id].start_s


def test_all_three_capacity_dimensions_are_exported_from_occupancy():
    problem = cold_problem()
    cold = problem.snapshot.coldchain
    declared = (
        CapacityAmount(CapacityUnit.QUANTITY_UNITS, 1),
        CapacityAmount(CapacityUnit.WEIGHT_G, 4),
        CapacityAmount(CapacityUnit.VOLUME_CM3, 5),
    )
    zone = replace(cold.zones[0], capacities=(
        CapacityAmount(CapacityUnit.QUANTITY_UNITS, 4),
        CapacityAmount(CapacityUnit.WEIGHT_G, 20),
        CapacityAmount(CapacityUnit.VOLUME_CM3, 20),
    ))
    original = cold.storage_locations[0]
    location = replace(original, capacities=(
        CapacityAmount(CapacityUnit.QUANTITY_UNITS, 2),
        CapacityAmount(CapacityUnit.WEIGHT_G, 8),
        CapacityAmount(CapacityUnit.VOLUME_CM3, 10),
    ), capacity_periods=tuple(replace(period, capacities=(
        CapacityAmount(CapacityUnit.QUANTITY_UNITS, 2 if period.start_s == 0 else 1),
        CapacityAmount(CapacityUnit.WEIGHT_G, 8 if period.start_s == 0 else 4),
        CapacityAmount(CapacityUnit.VOLUME_CM3, 10 if period.start_s == 0 else 5),
    )) for period in original.capacity_periods))
    cold = replace(cold, zones=(zone,), storage_locations=(location,),
                   occupancies=tuple(replace(item, capacity_use=declared)
                                     for item in cold.occupancies))
    problem = replace(problem, snapshot=rebuild(problem.snapshot, coldchain=cold))
    result = solve(problem)
    assert result.validation.valid, result.validation.violations
    assert all((item.quantity_units, item.weight_g, item.volume_cm3) == (1, 4, 5)
               for item in result.storage_allocations)


def test_independent_validation_rejects_tampered_storage_output():
    problem = cold_problem()
    result = solve(problem)
    assert result.validation.valid
    original = result.storage_allocations[0]
    bad_time = replace(result, storage_allocations=(
        replace(original, start_s=original.start_s + 1), *result.storage_allocations[1:]))
    report = validate_warehouse(problem, bad_time)
    assert not report.valid
    assert 'coldchain_storage_time' in {item.code for item in report.violations}
    bad_amount = replace(result, storage_allocations=(
        replace(original, volume_cm3=original.volume_cm3 + 1), *result.storage_allocations[1:]))
    report = validate_warehouse(problem, bad_amount)
    assert not report.valid
    assert 'coldchain_storage_mismatch' in {item.code for item in report.violations}
    duplicate = replace(result, storage_allocations=(*result.storage_allocations, original))
    report = validate_warehouse(problem, duplicate)
    assert not report.valid
    assert 'coldchain_storage_duplicate' in {item.code for item in report.violations}


def test_plain_warehouse_without_r05_has_no_storage_intervals():
    problem = cold_problem()
    problem = replace(problem, snapshot=rebuild(problem.snapshot, coldchain=None))
    result = solve(problem)
    assert result.status in (SolveStatus.OPTIMAL, SolveStatus.FEASIBLE)
    assert result.storage_allocations == ()
    assert result.validation.valid
