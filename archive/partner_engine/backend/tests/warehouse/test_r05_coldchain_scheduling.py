"""R05 cold-chain scheduling through the real CP-SAT adapter.

Two layers of evidence:

1. end-to-end runs of ``CpSatWarehouseScheduler`` on a snapshot that declares
   cold-chain data (positive solve, infeasible capacity, unknown changeover);
2. independent-checker tests on hand-crafted plans, proving the validator rejects
   over-capacity peaks, short changeover gaps, precool inversions, exposure
   overruns and missing multi-resource assignments.

Nothing here claims the DSH-owned domain rules (``domain/coldchain_capacity.py``,
``domain/joint_validation.py``) exist; these are the adapter-level checks.
"""
from __future__ import annotations

import datetime as dt

import pytest

from app.adapters.warehouse.coldchain_checks import check_coldchain
from app.adapters.warehouse.cp_sat_scheduler import CpSatWarehouseScheduler
from app.adapters.warehouse.validator import WarehouseScheduleValidator
from app.contracts.coldchain import (
    BatchCompatibility,
    CapacityAmount,
    ColdChainPlan,
    ColdChainSnapshot,
    CompatibilityPolicy,
    ExposureLimit,
    ExposureSegment,
    PrecoolRequirement,
    ResourceRequirement,
    ScheduledOccupancy,
    SetupPolicy,
    StorageLocation,
    WarehouseZone,
)
from app.contracts.entities import (
    Order,
    Operation,
    PlanningSnapshot,
    ScheduledOperation,
    StockLot,
    TravelMatrix,
    Warehouse,
    WarehouseResource,
)
from app.contracts.planning import WarehouseScheduleRequest, WarehouseScheduleResult
from app.contracts.common import SolveMetadata

ORIGIN = dt.datetime(2026, 10, 24, 0, 0, tzinfo=dt.timezone.utc)
RULE_VERSION = 'r05-test-0.2'

SOURCE = {
    'source_kind': 'simulation',
    'source_ref': 'tests/warehouse/test_r05_coldchain_scheduling.py',
    'observed_at': '2026-10-24T00:00:00Z',
    'rule_version': RULE_VERSION,
}


def _budget(ms: int = 5000) -> dict:
    return {'remaining_ms': ms, 'max_workers': 1, 'random_seed': 17}


def _order(order_id: str, batch_id: str) -> Order:
    return Order(
        order_id=order_id, version=1, warehouse_id='wh_1', batch_id=batch_id,
        delivery_node_id='node_2', quantity_units=1, weight_kg=6, volume_l=6,
        temperature_zone='chilled',
        service_window={'start_s': 0, 'end_s': 600},
        service_duration_s=10, freshness_deadline_s=600, source=SOURCE,
    )


def _operation(operation_id: str, order_id: str, kind: str, *, duration: int,
               resource_id: str, setup_class: str | None = None,
               requirements: tuple = (), predecessors: tuple[str, ...] = (),
               deadline: int = 600) -> Operation:
    return Operation(
        operation_id=operation_id, order_ids=(order_id,), warehouse_id='wh_1',
        resource_id=resource_id, operation_kind=kind, duration_s=duration,
        release_at_s=0, deadline_at_s=deadline, setup_class=setup_class,
        requirements=requirements, predecessor_ids=predecessors,
        primary_requirement_id=requirements[0].requirement_id if requirements else None,
    )


def _snapshot(coldchain: ColdChainSnapshot | None, operations: tuple[Operation, ...],
              resources: tuple[WarehouseResource, ...]) -> PlanningSnapshot:
    return PlanningSnapshot(
        snapshot_id='snap_r05', version=1, origin_at=ORIGIN, simulation_time_s=0,
        rule_version=RULE_VERSION,
        orders=(_order('ord_1', 'bat_1'), _order('ord_2', 'bat_2')),
        vehicles=(),
        warehouses=(Warehouse(warehouse_id='wh_1', version=1, node_id='node_1',
                              temperature_zones=('chilled',)),),
        resources=resources,
        stock_lots=(),
        operations=operations,
        matrix=TravelMatrix(
            matrix_id='matrix_r05', version=1, node_ids=('node_1', 'node_2'),
            duration_s=((0, 60), (60, 0)), distance_m=((0, 1000), (1000, 0)),
            source=SOURCE,
        ),
        coldchain=coldchain,
    )


def _dock(initial_class: str = 'class_a') -> WarehouseResource:
    return WarehouseResource(
        resource_id='res_dock1', warehouse_id='wh_1', version=1, resource_kind='dock',
        capacity_units=1, available_windows=({'start_s': 0, 'end_s': 600},),
        setup_policy_id='pol_dock', initial_setup_class=initial_class,
    )


def _worker() -> WarehouseResource:
    return WarehouseResource(
        resource_id='res_worker1', warehouse_id='wh_1', version=1,
        resource_kind='worker', capacity_units=1,
        available_windows=({'start_s': 0, 'end_s': 600},),
    )


def _precooler() -> WarehouseResource:
    return WarehouseResource(
        resource_id='res_pre1', warehouse_id='wh_1', version=1,
        resource_kind='pre_cooler', capacity_units=1,
        available_windows=({'start_s': 0, 'end_s': 600},),
    )


def _base_coldchain(**overrides) -> ColdChainSnapshot:
    payload = dict(
        rule_version=RULE_VERSION,
        horizon_s=600,
        zones=(WarehouseZone(
            zone_id='zone_1', warehouse_id='wh_1', version=1, temperature_zone='chilled',
            setpoint_decic=40,
            capacities=(CapacityAmount(unit='weight_g', amount=100),),
        ),),
        storage_locations=(StorageLocation(
            location_id='loc_1', warehouse_id='wh_1', zone_id='zone_1', version=1,
            capacities=(CapacityAmount(unit='weight_g', amount=10),),
            available_windows=({'start_s': 0, 'end_s': 600},),
        ),),
        occupancies=({'occupancy_id': 'occ_1', 'batch_id': 'bat_1', 'location_id': 'loc_1',
                      'capacity_use': [{'unit': 'weight_g', 'amount': 5}],
                      'origin': 'planned_inbound', 'inbound_operation_id': 'op_1-unload',
                      'outbound_operation_id': 'op_1-load'},),
        setup_policies=(SetupPolicy(
            policy_id='pol_dock', version='1', rule_version=RULE_VERSION,
            rendering='gap',
            rules=({'from_class': 'class_a', 'to_class': 'class_b', 'duration_s': 30},),
        ),),
        precool_requirements=(PrecoolRequirement(
            requirement_id='pre_1', batch_id='bat_1', warehouse_id='wh_1',
            precool_operation_id='op_1-precool', loading_operation_ids=('op_1-load',),
            min_duration_s=60, target_temperature_zone='chilled',
            eligible_resource_ids=('res_pre1',),
        ),),
        exposure_limits=(ExposureLimit(
            limit_id='exp_1', batch_id='bat_1', max_exposure_s=200,
            scopes=('in_warehouse', 'loading'), rule_version=RULE_VERSION, source=SOURCE,
        ),),
        batch_compatibility=(
            BatchCompatibility(batch_id='bat_1', warehouse_id='wh_1',
                               temperature_zone='chilled', min_temperature_decic=0,
                               max_temperature_decic=80, compatibility_class='class_a'),
            BatchCompatibility(batch_id='bat_2', warehouse_id='wh_1',
                               temperature_zone='chilled', min_temperature_decic=0,
                               max_temperature_decic=80, compatibility_class='class_b'),
        ),
        compatibility_policy=CompatibilityPolicy(
            policy_id='pol_mix', version='1', rule_version=RULE_VERSION,
            incompatible_class_pairs=(('class_a', 'class_b'),),
        ),
    )
    payload.update(overrides)
    return ColdChainSnapshot(**payload)


def _dock_requirements(eligible: tuple[str, ...] = ('res_dock1',)) -> tuple:
    return (
        ResourceRequirement(requirement_id='req_1-dock', requirement_kind='dock',
                            eligible_resource_ids=eligible, selection='fixed'),
        ResourceRequirement(requirement_id='req_1-worker', requirement_kind='worker',
                            eligible_resource_ids=('res_worker1',)),
    )


def _base_operations() -> tuple[Operation, ...]:
    requirements = _dock_requirements()
    return (
        _operation('op_1-unload', 'ord_1', 'unload', duration=40,
                   resource_id='res_dock1', setup_class='class_a',
                   requirements=requirements),
        _operation('op_1-precool', 'ord_1', 'precool', duration=60,
                   resource_id='res_pre1'),
        _operation('op_1-load', 'ord_1', 'load', duration=40,
                   resource_id='res_dock1', setup_class='class_b',
                   requirements=requirements,
                   predecessors=('op_1-unload', 'op_1-precool')),
    )


def _request(snapshot: PlanningSnapshot) -> WarehouseScheduleRequest:
    return WarehouseScheduleRequest(
        snapshot=snapshot, order_ids=('ord_1',), budget=_budget(),
    )


def _result(request: WarehouseScheduleRequest,
            operations: tuple[ScheduledOperation, ...],
            plan: ColdChainPlan | None) -> WarehouseScheduleResult:
    return WarehouseScheduleResult(
        snapshot_id=request.snapshot.snapshot_id,
        snapshot_version=request.snapshot.version,
        metadata=SolveMetadata(status='feasible', raw_status='TEST', engine='test',
                               engine_version='0', has_solution=True,
                               proof_scope='test', solve_ms=0),
        operations=operations,
        warehouse_handoffs=(),
        coldchain=plan,
    )


# --------------------------------------------------------------------------- #
# End-to-end CP-SAT runs
# --------------------------------------------------------------------------- #

def test_cp_sat_plans_with_coldchain_constraints():
    coldchain = _base_coldchain()
    operations = _base_operations() + (
        Operation(
            operation_id='op_2-unload', order_ids=('ord_2',), warehouse_id='wh_1',
            resource_id='res_worker1', operation_kind='unload', duration_s=30,
            release_at_s=0, deadline_at_s=600, setup_class='class_a',
        ),
    )
    snapshot = _snapshot(coldchain, operations, (_dock(), _worker(), _precooler()))
    request = _request(snapshot)

    result = CpSatWarehouseScheduler().schedule(request)

    assert result.metadata.has_solution is True
    assert result.coldchain is not None
    assert len(result.coldchain.occupancies) == 1
    occupancy = result.coldchain.occupancies[0]
    scheduled = {item.operation_id: item for item in result.operations}
    assert occupancy.start_s == scheduled['op_1-unload'].end_s
    assert occupancy.end_s == scheduled['op_1-load'].start_s
    assert occupancy.end_s > occupancy.start_s

    # pre-cooling finishes before loading starts
    assert scheduled['op_1-precool'].end_s <= scheduled['op_1-load'].start_s
    # changeover gap between the two dock tasks respects the 30 s rule
    gap = scheduled['op_1-load'].start_s - scheduled['op_1-unload'].end_s
    assert gap >= 30
    changeovers = [item for item in result.coldchain.changeovers
                   if item.resource_id == 'res_dock1']
    assert changeovers and changeovers[0].duration_s == 30

    # multi-resource assignments are explicit for every requirement
    for operation_id in ('op_1-unload', 'op_1-load'):
        assignments = {item.requirement_id for item in scheduled[operation_id].resource_assignments}
        assert assignments == {'req_1-dock', 'req_1-worker'}

    report = WarehouseScheduleValidator().validate(request, result)
    assert report.status == 'passed', [v.message for v in report.violations]
    assert 'r05.storage_capacity' in report.checked_rule_ids
    assert report.not_checked_rule_ids == ()


def test_cp_sat_infeasible_when_peak_capacity_cannot_be_met():
    """Two batches of 6 must both sit on a capacity-10 location until t=500."""
    coldchain = _base_coldchain(
        precool_requirements=(),
        exposure_limits=(),
        batch_compatibility=(),
        compatibility_policy=None,
        occupancies=(
            {'occupancy_id': 'occ_1', 'batch_id': 'bat_1', 'location_id': 'loc_1',
             'capacity_use': [{'unit': 'weight_g', 'amount': 6}],
             'origin': 'planned_inbound', 'inbound_operation_id': 'op_1-unload',
             'outbound_operation_id': 'op_1-load'},
            {'occupancy_id': 'occ_2', 'batch_id': 'bat_2', 'location_id': 'loc_1',
             'capacity_use': [{'unit': 'weight_g', 'amount': 6}],
             'origin': 'planned_inbound', 'inbound_operation_id': 'op_2-unload',
             'outbound_operation_id': 'op_2-load'},
        ),
    )
    operations = (
        _operation('op_1-unload', 'ord_1', 'unload', duration=10, resource_id='res_dock1',
                   deadline=100),
        _operation('op_2-unload', 'ord_2', 'unload', duration=10, resource_id='res_dock1',
                   deadline=100),
        Operation(operation_id='op_1-load', order_ids=('ord_1',), warehouse_id='wh_1',
                  resource_id='res_worker1', operation_kind='load', duration_s=10,
                  release_at_s=500, deadline_at_s=600,
                  predecessor_ids=('op_1-unload',)),
        Operation(operation_id='op_2-load', order_ids=('ord_2',), warehouse_id='wh_1',
                  resource_id='res_worker1', operation_kind='load', duration_s=10,
                  release_at_s=500, deadline_at_s=600,
                  predecessor_ids=('op_2-unload',)),
    )
    snapshot = _snapshot(coldchain, operations, (_dock('class_a'), _worker()))
    request = WarehouseScheduleRequest(snapshot=snapshot,
                                       order_ids=('ord_1', 'ord_2'), budget=_budget())

    result = CpSatWarehouseScheduler().schedule(request)

    # Both occupancies are forced to overlap in [20, 500): 6 + 6 > 10.
    assert result.metadata.has_solution is False
    assert result.coldchain is None


def test_cp_sat_infeasible_on_unknown_changeover_pair():
    coldchain = _base_coldchain(precool_requirements=(), exposure_limits=(),
                                batch_compatibility=(), compatibility_policy=None,
                                occupancies=())
    operations = (
        _operation('op_1-unload', 'ord_1', 'unload', duration=40,
                   resource_id='res_dock1', setup_class='class_a'),
        _operation('op_1-load', 'ord_1', 'load', duration=40,
                   resource_id='res_dock1', setup_class='class_c'),
    )
    snapshot = _snapshot(coldchain, operations, (_dock('class_a'),))

    result = CpSatWarehouseScheduler().schedule(_request(snapshot))

    # An unlisted class pair is unknown, never free: the two operations may not
    # share the only dock, so the request cannot be scheduled.
    assert result.metadata.has_solution is False


def test_snapshot_without_coldchain_keeps_previous_behaviour():
    operations = (
        _operation('op_1-unload', 'ord_1', 'unload', duration=40, resource_id='res_dock1'),
    )
    snapshot = _snapshot(None, operations, (_dock('class_a'),))

    result = CpSatWarehouseScheduler().schedule(_request(snapshot))

    assert result.coldchain is None
    assert WarehouseScheduleValidator().validate(_request(snapshot), result).status == 'passed'


# --------------------------------------------------------------------------- #
# Independent checker: negative evidence on hand-crafted plans
# --------------------------------------------------------------------------- #

def _plan(**overrides) -> ColdChainPlan:
    payload = dict(rule_version=RULE_VERSION, occupancies=(), exposure_segments=(),
                   changeovers=())
    payload.update(overrides)
    return ColdChainPlan(**payload)


def _scheduled(operation_id: str, start: int, end: int, resource_id: str = 'res_dock1',
               **kwargs) -> ScheduledOperation:
    return ScheduledOperation(operation_id=operation_id, resource_id=resource_id,
                              start_s=start, end_s=end, **kwargs)


def test_checker_rejects_peak_occupancy_over_capacity():
    coldchain = _base_coldchain(precool_requirements=(), exposure_limits=(),
                                batch_compatibility=(), compatibility_policy=None)
    snapshot = _snapshot(coldchain, (), (_dock('class_a'),))
    request = _request(snapshot)
    plan = _plan(occupancies=(
        ScheduledOccupancy(occupancy_id='occ_1', batch_id='bat_1', location_id='loc_1',
                           capacity_use=(CapacityAmount(unit='weight_g', amount=6),),
                           start_s=0, end_s=100),
        ScheduledOccupancy(occupancy_id='occ_2', batch_id='bat_2', location_id='loc_1',
                           capacity_use=(CapacityAmount(unit='weight_g', amount=5),),
                           start_s=50, end_s=150),
    ))
    outcome = check_coldchain(request, _result(request, (), plan))

    assert outcome.status == 'failed'
    storage = [v for v in outcome.violations if v.rule_id == 'r05.storage_capacity']
    assert storage
    evidence = storage[0].evidence
    assert evidence.observed_value == 11
    assert evidence.limit_value == 10
    assert (evidence.interval_start_s, evidence.interval_end_s) == (50, 100)


def test_checker_releases_before_acquiring_at_the_same_second():
    """A batch leaving at t frees capacity for one entering at t (half-open)."""
    coldchain = _base_coldchain(precool_requirements=(), exposure_limits=(),
                                batch_compatibility=(), compatibility_policy=None)
    snapshot = _snapshot(coldchain, (), (_dock('class_a'),))
    request = _request(snapshot)
    plan = _plan(occupancies=(
        ScheduledOccupancy(occupancy_id='occ_1', batch_id='bat_1', location_id='loc_1',
                           capacity_use=(CapacityAmount(unit='weight_g', amount=6),),
                           start_s=0, end_s=100),
        ScheduledOccupancy(occupancy_id='occ_2', batch_id='bat_2', location_id='loc_1',
                           capacity_use=(CapacityAmount(unit='weight_g', amount=6),),
                           start_s=100, end_s=200),
    ))
    outcome = check_coldchain(request, _result(request, (), plan))

    assert not [v for v in outcome.violations if v.rule_id == 'r05.storage_capacity']


def test_checker_rejects_short_changeover_gap():
    coldchain = _base_coldchain(precool_requirements=(), exposure_limits=(),
                                batch_compatibility=(), compatibility_policy=None)
    operations = (
        _operation('op_1-unload', 'ord_1', 'unload', duration=40,
                   resource_id='res_dock1', setup_class='class_a'),
        _operation('op_1-load', 'ord_1', 'load', duration=40,
                   resource_id='res_dock1', setup_class='class_b'),
    )
    snapshot = _snapshot(coldchain, operations, (_dock('class_a'),))
    request = _request(snapshot)
    plan = _plan()
    scheduled = (_scheduled('op_1-unload', 0, 40), _scheduled('op_1-load', 55, 95))
    outcome = check_coldchain(request, _result(request, scheduled, plan))

    changeover = [v for v in outcome.violations if v.rule_id == 'r05.changeover']
    assert changeover and '15s' in changeover[0].message


def test_checker_rejects_precool_loaded_too_early():
    coldchain = _base_coldchain(exposure_limits=(), batch_compatibility=(),
                                compatibility_policy=None)
    operations = _base_operations()
    snapshot = _snapshot(coldchain, operations, (_dock(), _worker(), _precooler()))
    request = _request(snapshot)
    scheduled = (
        _scheduled('op_1-unload', 0, 40),
        _scheduled('op_1-precool', 40, 90, resource_id='res_pre1'),
        _scheduled('op_1-load', 95, 135,
                   resource_assignments=(
                       {'requirement_id': 'req_1-dock', 'resource_id': 'res_dock1'},
                       {'requirement_id': 'req_1-worker', 'resource_id': 'res_worker1'},
                   )),
    )
    # loading starts before precooling ends -> violation
    scheduled = (scheduled[0], scheduled[1], _scheduled(
        'op_1-load', 85, 125,
        resource_assignments=(
            {'requirement_id': 'req_1-dock', 'resource_id': 'res_dock1'},
            {'requirement_id': 'req_1-worker', 'resource_id': 'res_worker1'},
        )))
    outcome = check_coldchain(request, _result(request, scheduled, _plan()))

    precool = [v for v in outcome.violations if v.rule_id == 'r05.precool']
    assert precool


def test_checker_counts_exposure_union_not_sum():
    coldchain = _base_coldchain(
        precool_requirements=(),
        exposure_limits=(ExposureLimit(limit_id='exp_1', batch_id='bat_1',
                                       max_exposure_s=120,
                                       scopes=('in_warehouse', 'loading'),
                                       rule_version=RULE_VERSION, source=SOURCE),),
        batch_compatibility=(), compatibility_policy=None,
    )
    snapshot = _snapshot(coldchain, (), (_dock('class_a'),))
    request = _request(snapshot)
    # [0,80) and [60,100) overlap by 20s, plus loading [100,120):
    # union = [0,120) = 120 <= 120, while the naive sum would be 140.
    plan = _plan(exposure_segments=(
        ExposureSegment(segment_id='exp_a', batch_id='bat_1', scope='in_warehouse',
                        start_s=0, end_s=80, source_kind='planned'),
        ExposureSegment(segment_id='exp_b', batch_id='bat_1', scope='in_warehouse',
                        start_s=60, end_s=100, source_kind='planned'),
        ExposureSegment(segment_id='exp_c', batch_id='bat_1', scope='loading',
                        start_s=100, end_s=120, source_kind='planned'),
    ))
    outcome = check_coldchain(request, _result(request, (), plan))

    assert not [v for v in outcome.violations if v.rule_id == 'r05.exposure']


def test_checker_rejects_exposure_over_limit_with_union_evidence():
    coldchain = _base_coldchain(
        precool_requirements=(),
        exposure_limits=(ExposureLimit(limit_id='exp_1', batch_id='bat_1',
                                       max_exposure_s=120,
                                       scopes=('in_warehouse', 'loading'),
                                       rule_version=RULE_VERSION, source=SOURCE),),
        batch_compatibility=(), compatibility_policy=None,
    )
    snapshot = _snapshot(coldchain, (), (_dock('class_a'),))
    request = _request(snapshot)
    # union [0,80) U [60,161) = [0,161) -> 161 > 120
    plan = _plan(exposure_segments=(
        ExposureSegment(segment_id='exp_a', batch_id='bat_1', scope='in_warehouse',
                        start_s=0, end_s=80, source_kind='planned'),
        ExposureSegment(segment_id='exp_b', batch_id='bat_1', scope='loading',
                        start_s=60, end_s=161, source_kind='planned'),
    ))
    outcome = check_coldchain(request, _result(request, (), plan))

    exposure = [v for v in outcome.violations if v.rule_id == 'r05.exposure']
    assert exposure
    assert exposure[0].evidence.observed_value == 161


def test_checker_reports_unchecked_when_a_scope_has_no_segments():
    coldchain = _base_coldchain(
        precool_requirements=(), occupancies=(),
        exposure_limits=(ExposureLimit(limit_id='exp_1', batch_id='bat_1',
                                       max_exposure_s=120,
                                       scopes=('in_warehouse', 'transport'),
                                       rule_version=RULE_VERSION, source=SOURCE),),
        batch_compatibility=(), compatibility_policy=None,
    )
    snapshot = _snapshot(coldchain, (), (_dock('class_a'),))
    request = _request(snapshot)
    plan = _plan(exposure_segments=(
        ExposureSegment(segment_id='exp_a', batch_id='bat_1', scope='in_warehouse',
                        start_s=0, end_s=60, source_kind='planned'),
    ))
    outcome = check_coldchain(request, _result(request, (), plan))

    assert outcome.status == 'not_checked'
    assert any('transport' in entry for entry in outcome.not_checked)


def test_checker_rejects_missing_multi_resource_assignment():
    coldchain = _base_coldchain(precool_requirements=(), exposure_limits=(),
                                batch_compatibility=(), compatibility_policy=None,
                                occupancies=())
    operations = _base_operations()[:1]
    snapshot = _snapshot(coldchain, operations, (_dock(), _worker(), _precooler()))
    request = _request(snapshot)
    scheduled = (_scheduled('op_1-unload', 0, 40, resource_assignments=(
        {'requirement_id': 'req_1-dock', 'resource_id': 'res_dock1'},
    )),)
    outcome = check_coldchain(request, _result(request, scheduled, _plan()))

    requirement_violations = [v for v in outcome.violations
                              if v.rule_id == 'r05.resource_requirements']
    assert requirement_violations
    assert any('expected exactly 1' in v.message for v in requirement_violations)


def test_checker_rejects_ineligible_requirement_resource():
    coldchain = _base_coldchain(precool_requirements=(), exposure_limits=(),
                                batch_compatibility=(), compatibility_policy=None,
                                occupancies=())
    operations = _base_operations()[:1]
    snapshot = _snapshot(coldchain, operations, (_dock(), _worker(), _precooler()))
    request = _request(snapshot)
    scheduled = (ScheduledOperation(
        operation_id='op_1-unload', resource_id='res_worker1', start_s=0, end_s=40,
        resource_assignments=(
            {'requirement_id': 'req_1-dock', 'resource_id': 'res_worker1'},
            {'requirement_id': 'req_1-worker', 'resource_id': 'res_worker1'},
        ),
    ),)
    outcome = check_coldchain(request, _result(request, scheduled, _plan()))

    assert [v for v in outcome.violations if v.rule_id == 'r05.resource_requirements']


def test_checker_rejects_incompatible_batches_sharing_a_location():
    coldchain = _base_coldchain(precool_requirements=(), exposure_limits=())
    snapshot = _snapshot(coldchain, (), (_dock('class_a'),))
    request = _request(snapshot)
    plan = _plan(occupancies=(
        ScheduledOccupancy(occupancy_id='occ_1', batch_id='bat_1', location_id='loc_1',
                           capacity_use=(CapacityAmount(unit='weight_g', amount=1),),
                           start_s=0, end_s=100),
        ScheduledOccupancy(occupancy_id='occ_2', batch_id='bat_2', location_id='loc_1',
                           capacity_use=(CapacityAmount(unit='weight_g', amount=1),),
                           start_s=50, end_s=150),
    ))
    outcome = check_coldchain(request, _result(request, (), plan))

    mixing = [v for v in outcome.violations if v.rule_id == 'r05.batch_compatibility']
    assert mixing and 'incompatible' in mixing[0].message


def test_checker_rejects_tampered_occupancy_interval():
    coldchain = _base_coldchain(
        precool_requirements=(), exposure_limits=(), batch_compatibility=(),
        compatibility_policy=None,
        occupancies=({'occupancy_id': 'occ_1', 'batch_id': 'bat_1', 'location_id': 'loc_1',
                      'capacity_use': [{'unit': 'weight_g', 'amount': 4}],
                      'origin': 'planned_inbound', 'inbound_operation_id': 'op_1-unload',
                      'outbound_operation_id': 'op_1-load'},),
    )
    operations = _base_operations()[:1] + _base_operations()[2:]
    snapshot = _snapshot(coldchain, operations, (_dock(), _worker(), _precooler()))
    request = _request(snapshot)
    scheduled = (_scheduled('op_1-unload', 0, 40), _scheduled('op_1-load', 70, 110,
                                                             resource_assignments=(
        {'requirement_id': 'req_1-dock', 'resource_id': 'res_dock1'},
        {'requirement_id': 'req_1-worker', 'resource_id': 'res_worker1'},
    )))
    plan = _plan(occupancies=(
        ScheduledOccupancy(occupancy_id='occ_1', batch_id='bat_1', location_id='loc_1',
                           capacity_use=(CapacityAmount(unit='weight_g', amount=4),),
                           start_s=0, end_s=50),
    ))
    outcome = check_coldchain(request, _result(request, scheduled, plan))

    derivation = [v for v in outcome.violations
                  if v.rule_id == 'r05.occupancy_declaration']
    assert derivation and any('interval' in v.message for v in derivation)





def test_checker_rejects_assignment_outside_resource_window():
    coldchain = _base_coldchain(precool_requirements=(), exposure_limits=(),
                                batch_compatibility=(), compatibility_policy=None,
                                occupancies=())
    operations = _base_operations()[:1]
    narrow_worker = WarehouseResource(
        resource_id='res_worker1', warehouse_id='wh_1', version=1,
        resource_kind='worker', capacity_units=1,
        available_windows=({'start_s': 0, 'end_s': 20},),
    )
    snapshot = _snapshot(coldchain, operations, (_dock(), narrow_worker, _precooler()))
    request = _request(snapshot)
    scheduled = (_scheduled('op_1-unload', 0, 40, resource_assignments=(
        {'requirement_id': 'req_1-dock', 'resource_id': 'res_dock1'},
        {'requirement_id': 'req_1-worker', 'resource_id': 'res_worker1'},
    )),)
    outcome = check_coldchain(request, _result(request, scheduled, _plan()))

    window = [v for v in outcome.violations
              if v.rule_id == 'r05.resource_requirements' and 'not available' in v.message]
    assert window
