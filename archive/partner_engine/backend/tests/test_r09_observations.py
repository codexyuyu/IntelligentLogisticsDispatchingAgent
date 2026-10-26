"""R09 integration tests: business observations and the R08 composed negotiator.

The observations must be facts a reviewer can recompute by hand, and absent
cold-chain evidence must stay absent rather than turn into zeros.
"""
from __future__ import annotations

import datetime as dt

import pytest

from app.application.contract_net import TaskSpec
from app.application.plan_observations import observe_plan
from app.bootstrap import build_negotiator
from app.contracts.coldchain import (
    CapacityAmount,
    ColdChainPlan,
    ExposureSegment,
    ScheduledChangeover,
    ScheduledOccupancy,
)
from app.contracts.common import SolveMetadata, TimeWindow, ValidationReport
from app.contracts.entities import (
    Operation,
    Order,
    PlanningSnapshot,
    ScheduledOperation,
    TravelMatrix,
    Vehicle,
    Warehouse,
    WarehouseResource,
)
from app.contracts.planning import (
    CandidatePlan,
    RouteStop as PlanningRouteStop,
    RoutingResult,
    UnservedOrder,
    VehicleRoute as PlanningVehicleRoute,
    WarehouseHandoff,
    WarehouseScheduleResult,
)

ORIGIN = dt.datetime(2026, 10, 24, 0, 0, tzinfo=dt.timezone.utc)
SOURCE = {
    'source_kind': 'simulation',
    'source_ref': 'tests/test_r09_observations.py',
    'observed_at': '2026-10-24T00:00:00Z',
    'rule_version': 'r09-test',
}
META = SolveMetadata(status='feasible', raw_status='TEST', engine='test', engine_version='0',
                     has_solution=True, proof_scope='test', solve_ms=1)
VALIDATED = ValidationReport(status='passed', validator_version='test',
                             checked_rule_ids=('test.rule',), violations=())


def _stop(node: str, kind: str, departure: int, orders: tuple = (),
          arrival: int = 0, start: int = 0) -> PlanningRouteStop:
    return PlanningRouteStop(node_id=node, order_ids=orders, stop_kind=kind,
                             arrival_at_s=arrival, service_start_at_s=start,
                             departure_at_s=departure, load_weight_kg=0, load_volume_l=0)


def _routing(unserved: tuple = (), routes: tuple = ()) -> RoutingResult:
    return RoutingResult(snapshot_id='snap_r09', snapshot_version=1, metadata=META,
                         routes=routes, warehouse_arrivals=(), unserved_orders=unserved)


def _route(vehicle: str, departure: int, orders: tuple, distance: int = 1000,
           duration: int = 300) -> PlanningVehicleRoute:
    return PlanningVehicleRoute(
        vehicle_id=vehicle,
        stops=(_stop('node_depot', 'depot_start', departure),
               _stop('node_c1', 'delivery', departure + 120, orders, arrival=departure + 100,
                     start=departure + 110),
               _stop('node_depot', 'depot_end', departure + 200)),
        distance_m=distance, duration_s=duration,
    )


def _warehouse(handoffs: tuple = (), operations: tuple = (),
               coldchain: ColdChainPlan | None = None) -> WarehouseScheduleResult:
    return WarehouseScheduleResult(snapshot_id='snap_r09', snapshot_version=1, metadata=META,
                                   operations=operations, warehouse_handoffs=handoffs,
                                   coldchain=coldchain)


def _plan(routing: RoutingResult, warehouse: WarehouseScheduleResult) -> CandidatePlan:
    return CandidatePlan(plan_id='plan_r09', snapshot_id='snap_r09', snapshot_version=1,
                         version=1, plan_hash='a' * 64, routing=routing, warehouse=warehouse,
                         validation=VALIDATED)


def _handoff(order_id: str, ready_at: int) -> WarehouseHandoff:
    return WarehouseHandoff(order_id=order_id, warehouse_id='wh_1', ready_at_s=ready_at,
                            loading_window=TimeWindow(start_s=ready_at, end_s=ready_at + 600))


# --------------------------------------------------------------------------- #
# Coverage, waits, totals
# --------------------------------------------------------------------------- #

def test_coverage_separates_served_and_unserved():
    routing = _routing(unserved=(UnservedOrder(order_id='ord_2', reason_code='cargo_quarantined'),),
                       routes=(_route('veh_1', 600, ('ord_1',)),))
    observations = observe_plan(_plan(routing, _warehouse()), ('ord_1', 'ord_2'))

    assert observations.requested_order_ids == ('ord_1', 'ord_2')
    assert observations.served_order_ids == ('ord_1',)
    assert observations.unserved == (('ord_2', 'cargo_quarantined'),)
    assert observations.requested_count == 2 and observations.served_count == 1


def test_handoff_wait_is_departure_minus_ready_at():
    routing = _routing(routes=(_route('veh_1', 900, ('ord_1',)),))
    warehouse = _warehouse(handoffs=(_handoff('ord_1', 300),))
    observations = observe_plan(_plan(routing, warehouse), ('ord_1',))

    assert observations.handoff_wait_s == (('ord_1', 600),)


def test_makespan_distance_and_duration_are_summed():
    routing = _routing(routes=(_route('veh_1', 600, ('ord_1',), distance=1200, duration=300),
                               _route('veh_2', 700, ('ord_2',), distance=800, duration=250)))
    operations = (ScheduledOperation(operation_id='op_1', resource_id='res_1',
                                     start_s=0, end_s=420),
                  ScheduledOperation(operation_id='op_2', resource_id='res_2',
                                     start_s=100, end_s=780))
    observations = observe_plan(_plan(routing, _warehouse(operations=operations)),
                                ('ord_1', 'ord_2'))

    assert observations.warehouse_makespan_s == 780
    assert observations.total_distance_m == 2000
    assert observations.total_duration_s == 550


# --------------------------------------------------------------------------- #
# Cold-chain evidence: present or explicitly absent
# --------------------------------------------------------------------------- #

def test_absent_coldchain_evidence_is_not_zero_measurements():
    observations = observe_plan(_plan(_routing(routes=(_route('veh_1', 600, ('ord_1',)),)),
                                      _warehouse()), ('ord_1',))

    assert observations.coldchain_evidence is False
    assert observations.capacity_peaks == ()
    assert observations.exposure_totals == ()
    assert observations.changeover_count == 0


def test_capacity_peak_uses_half_open_intervals():
    coldchain = ColdChainPlan(
        rule_version='r09-test',
        occupancies=(
            ScheduledOccupancy(occupancy_id='occ_1', batch_id='bat_1', location_id='loc_1',
                               capacity_use=(CapacityAmount(unit='weight_g', amount=6),),
                               start_s=0, end_s=100),
            ScheduledOccupancy(occupancy_id='occ_2', batch_id='bat_2', location_id='loc_1',
                               capacity_use=(CapacityAmount(unit='weight_g', amount=6),),
                               start_s=50, end_s=150),
            ScheduledOccupancy(occupancy_id='occ_3', batch_id='bat_3', location_id='loc_1',
                               capacity_use=(CapacityAmount(unit='weight_g', amount=6),),
                               start_s=150, end_s=200),
        ),
        exposure_segments=(),
        changeovers=(),
    )
    observations = observe_plan(_plan(_routing(), _warehouse(coldchain=coldchain)), ())

    peak = observations.capacity_peaks[0]
    assert (peak.location_id, peak.unit, peak.peak) == ('loc_1', 'weight_g', 12)
    assert (peak.interval_start_s, peak.interval_end_s) == (50, 100)
    # occ_3 starts exactly when occ_2 ends: touching intervals do not stack.
    assert len(observations.capacity_peaks) == 1


def test_exposure_union_counts_overlaps_once():
    coldchain = ColdChainPlan(
        rule_version='r09-test', occupancies=(),
        exposure_segments=(
            ExposureSegment(segment_id='seg_1', batch_id='bat_1', scope='in_warehouse',
                            start_s=0, end_s=80, source_kind='planned'),
            ExposureSegment(segment_id='seg_2', batch_id='bat_1', scope='loading',
                            start_s=60, end_s=100, source_kind='planned'),
            ExposureSegment(segment_id='seg_3', batch_id='bat_1', scope='loading',
                            start_s=100, end_s=120, source_kind='planned'),
        ),
        changeovers=(),
    )
    observations = observe_plan(_plan(_routing(), _warehouse(coldchain=coldchain)), ())

    exposure = observations.exposure_totals[0]
    assert exposure.batch_id == 'bat_1'
    assert exposure.union_s == 120            # [0,120), not 80+40+20=140
    assert exposure.scopes == ('in_warehouse', 'loading')


def test_changeovers_are_counted_with_their_duration():
    coldchain = ColdChainPlan(
        rule_version='r09-test', occupancies=(), exposure_segments=(),
        changeovers=(
            ScheduledChangeover(changeover_id='chg_1', resource_id='res_1', from_class='a',
                                to_class='b', duration_s=30, after_operation_id='op_1',
                                before_operation_id='op_2'),
            ScheduledChangeover(changeover_id='chg_2', resource_id='res_1', from_class='b',
                                to_class='a', duration_s=45, after_operation_id='op_2',
                                before_operation_id='op_3'),
        ),
    )
    observations = observe_plan(_plan(_routing(), _warehouse(coldchain=coldchain)), ())

    assert observations.changeover_count == 2
    assert observations.changeover_duration_s == 75


# --------------------------------------------------------------------------- #
# Negotiation facts ride along, and determinism
# --------------------------------------------------------------------------- #

def test_observations_are_deterministic():
    routing = _routing(routes=(_route('veh_1', 600, ('ord_1',)),))
    warehouse = _warehouse(handoffs=(_handoff('ord_1', 300),))

    first = observe_plan(_plan(routing, warehouse), ('ord_1',))
    second = observe_plan(_plan(routing, warehouse), ('ord_1',))

    assert first == second


def _snapshot() -> PlanningSnapshot:
    return PlanningSnapshot(
        snapshot_id='snap_r09', version=1, origin_at=ORIGIN, simulation_time_s=0,
        rule_version='r09-test',
        orders=(Order(order_id='ord_1', version=1, warehouse_id='wh_1', batch_id='bat_1',
                      delivery_node_id='node_c1', quantity_units=1, weight_kg=10, volume_l=10,
                      temperature_zone='chilled', service_window={'start_s': 0, 'end_s': 900},
                      service_duration_s=10, freshness_deadline_s=900, source=SOURCE),),
        vehicles=(Vehicle(vehicle_id='veh_1', version=1, warehouse_id='wh_1',
                          start_node_id='node_depot', end_node_id='node_depot',
                          current_node_id='node_depot', capacity_weight_kg=100,
                          capacity_volume_l=100, remaining_weight_kg=100,
                          remaining_volume_l=100, temperature_zone='chilled',
                          shift_window={'start_s': 0, 'end_s': 900},
                          available_at_s=0, source=SOURCE),),
        warehouses=(Warehouse(warehouse_id='wh_1', version=1, node_id='node_depot',
                              temperature_zones=('chilled',)),),
        resources=(WarehouseResource(resource_id='res_dock1', warehouse_id='wh_1', version=1,
                                     resource_kind='dock', capacity_units=1,
                                     available_windows=({'start_s': 0, 'end_s': 900},)),),
        stock_lots=(),
        operations=(Operation(operation_id='task_1', order_ids=('ord_1',), warehouse_id='wh_1',
                              resource_id='res_dock1', operation_kind='load',
                              duration_s=30, release_at_s=0, deadline_at_s=900),),
        matrix=TravelMatrix(matrix_id='matrix_r09', version=1,
                            node_ids=('node_depot', 'node_c1'),
                            duration_s=((0, 120), (120, 0)),
                            distance_m=((0, 1000), (1000, 0)), source=SOURCE),
    )


def test_composed_negotiator_is_bound_to_snapshot_objects():
    negotiator = build_negotiator(_snapshot())
    result = negotiator.negotiate([TaskSpec(task_id='task_1', warehouse_id='wh_1',
                                            window_start_s=0, window_end_s=900)], now_s=0)

    assert result.status == 'confirmed'
    # no declared disruption -> the exception role stays silent
    assert [award.role for award in result.awards] == ['warehouse']


def test_declared_disruption_lets_the_exception_role_bid():
    negotiator = build_negotiator(_snapshot(), disruption_at_s=0, recovery_s=10)
    result = negotiator.negotiate([TaskSpec(task_id='task_1', warehouse_id='wh_1',
                                            window_start_s=0, window_end_s=900,
                                            exclusive_resource_ids=('res_dock1',))], now_s=0)

    assert result.status == 'confirmed'
    # recovery costs 10 and the warehouse slot 30, so the exception role wins.
    # Two bids for the SAME task are ordinary competition, not a resource
    # conflict, so nothing is recorded as a conflict.
    assert [award.role for award in result.awards] == ['exception']
    assert result.conflicts == ()


def test_unknown_resource_or_vehicle_is_rejected():
    with pytest.raises(ValueError, match='unknown_warehouse_resource:res_missing'):
        build_negotiator(_snapshot(), warehouse_resource_id='res_missing')
    with pytest.raises(ValueError, match='unknown_vehicle:veh_missing'):
        build_negotiator(_snapshot(), vehicle_id='veh_missing')


def test_negotiation_facts_are_carried_into_observations():
    negotiator = build_negotiator(_snapshot())
    result = negotiator.negotiate([TaskSpec(task_id='task_1', warehouse_id='wh_1',
                                            window_start_s=0, window_end_s=900)], now_s=0)
    observations = observe_plan(
        _plan(_routing(routes=(_route('veh_1', 600, ('ord_1',)),)), _warehouse()),
        ('ord_1',), negotiation=result,
    )

    assert observations.negotiation_status == 'confirmed'
    assert observations.negotiation_awards == 1
    assert observations.negotiation_conflicts == 0
    assert observations.negotiation_digest == result.digest

