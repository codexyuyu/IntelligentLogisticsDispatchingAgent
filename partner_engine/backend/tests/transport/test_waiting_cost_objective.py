"""R20 routing-objective tests: the copy-binding fix, and the waiting term's status.

Two findings from the R20 work are pinned here:

1. FIXED. `VehicleVar(index) == (vehicle_idx + 1) * active - 1` (the R14 workaround) also
   stopped the local search from ever activating another vehicle's copy of an order. The
   fixture below has a split plan of 2200 m against a single-vehicle plan of 3100 m; the old
   formulation returned 3100 m, the native domain returns 2200 m.

2. NOT YET EFFECTIVE. The waiting term (`waiting_s` dimension + soft upper bounds) models
   exactly `departure - ready_at` -- verified by reading the solved cumul vars -- but the
   search does not act on it: at coefficient 100000 it still pays 1800 s of waiting instead
   of 400 m of extra distance. The term is kept wired and documented; it must not be
   reported as an achieved optimisation until a search-level change lands.
"""
from datetime import datetime, timezone
from pathlib import Path

import pytest

from app.adapters.routing.ortools_solver import WAITING_COST_PER_SECOND, OrToolsRoutingSolver
from app.contracts.common import Source, TimeWindow
from app.contracts.entities import Order, PlanningSnapshot, TravelMatrix, Vehicle, Warehouse
from app.contracts.planning import RoutingRequest, WarehouseHandoff

SOURCE = Source(source_kind="default", source_ref="waiting-cost-test",
                observed_at=datetime.now(timezone.utc), rule_version="test-1")
READY_AT = {"ord_001": 0, "ord_002": 1800}
DURATION = ((0, 100, 100), (100, 0, 200), (100, 200, 0))


def _distance(lateral: int):
    # one vehicle : wh->c1 + c1->c2 + c2->wh = 1000 + 2000 + lateral
    # split       : (wh->c1 + c1->wh) + (wh->c2 + c2->wh) = 2000 + 2*lateral
    return ((0, 1000, lateral), (1000, 0, 2000), (lateral, 2000, 0))


def _snapshot(lateral: int) -> PlanningSnapshot:
    orders = tuple(
        Order(order_id=f"ord_00{i}", version=1, warehouse_id="wh_1", batch_id=f"bat_00{i}",
              delivery_node_id=f"node_c{i}", quantity_units=1, weight_kg=10, volume_l=10,
              temperature_zone="chilled", service_window=TimeWindow(start_s=0, end_s=10000),
              service_duration_s=60, freshness_deadline_s=10000, required=True, source=SOURCE)
        for i in (1, 2)
    )
    vehicles = tuple(
        Vehicle(vehicle_id=f"veh_{i}", version=1, warehouse_id="wh_1", start_node_id="node_wh",
                end_node_id="node_wh", current_node_id="node_wh", capacity_weight_kg=1000,
                capacity_volume_l=1000, remaining_weight_kg=1000, remaining_volume_l=1000,
                temperature_zone="chilled", shift_window=TimeWindow(start_s=0, end_s=20000),
                available_at_s=0, source=SOURCE)
        for i in (1, 2)
    )
    return PlanningSnapshot(
        snapshot_id="snap_waiting", version=1, origin_at=datetime.now(timezone.utc),
        simulation_time_s=0, rule_version="test-1", orders=orders, vehicles=vehicles,
        warehouses=(Warehouse(warehouse_id="wh_1", version=1, node_id="node_wh",
                              temperature_zones=("chilled",)),),
        resources=(), stock_lots=(), operations=(), frozen_operations=(),
        matrix=TravelMatrix(matrix_id="mat_waiting", version=1,
                            node_ids=("node_wh", "node_c1", "node_c2"),
                            duration_s=DURATION, distance_m=_distance(lateral), source=SOURCE),
    )


def _handoff(order_id: str) -> WarehouseHandoff:
    ready = READY_AT[order_id]
    return WarehouseHandoff(order_id=order_id, warehouse_id="wh_1", ready_at_s=ready,
                            loading_window=TimeWindow(start_s=ready, end_s=10000))


def _solve(lateral: int):
    request = RoutingRequest(
        snapshot=_snapshot(lateral), order_ids=("ord_001", "ord_002"),
        warehouse_handoffs=(_handoff("ord_001"), _handoff("ord_002")), frozen_routes=(),
        budget={"remaining_ms": 5000, "max_workers": 1, "random_seed": 17},
    )
    result = OrToolsRoutingSolver().solve(request)
    assert result.metadata.has_solution, result.metadata.raw_status
    served = {route.vehicle_id: tuple(oid for stop in route.stops
                                      if stop.stop_kind == "delivery" for oid in stop.order_ids)
              for route in result.routes}
    distance = sum(route.distance_m for route in result.routes)
    waiting = sum(max(0, route.stops[0].departure_at_s - READY_AT[oid])
                  for route in result.routes for stop in route.stops
                  if stop.stop_kind == "delivery" for oid in stop.order_ids)
    return served, distance, waiting


def test_solver_splits_orders_across_vehicles_when_that_is_cheaper():
    served, distance, waiting = _solve(lateral=100)
    assert distance == 2200, "2200 m split exists but the solver returned a more expensive plan"
    assert served["veh_1"] and served["veh_2"]
    assert waiting == 0


def test_single_vehicle_alternative_is_more_expensive_on_that_instance():
    """Arithmetic only: quantifies what the old copy binding left on the table."""
    one_vehicle = 1000 + 2000 + 100
    split = (1000 + 1000) + (100 + 100)
    assert (one_vehicle, split) == (3100, 2200)


def test_equal_distance_tie_is_not_yet_broken_by_waiting():
    """Documents the known gap: at equal distance the solver keeps the waiting-heavy plan."""
    served, distance, waiting = _solve(lateral=1000)
    assert distance == 4000
    assert (distance, waiting) == (4000, 1800), (
        "waiting soft costs started steering the search; update this test and the "
        "documented limitation in ortools_solver.py")
    assert sorted(served["veh_1"] + served["veh_2"]) == ["ord_001", "ord_002"]


def test_waiting_term_is_wired_into_the_model():
    source = Path(__file__).resolve().parents[2] / "app/adapters/routing/ortools_solver.py"
    text = source.read_text(encoding="utf-8")
    assert "waiting_dim.SetCumulVarSoftUpperBound(" in text
    assert 'waiting_dim_name = "waiting_s"' in text
    assert "KNOWN LIMITATION" in text
    assert WAITING_COST_PER_SECOND > 0


def test_copy_binding_uses_the_native_two_value_domain():
    source = Path(__file__).resolve().parents[2] / "app/adapters/routing/ortools_solver.py"
    text = source.read_text(encoding="utf-8")
    assert "routing.VehicleVar(index).SetValues([vehicle_idx, -1])" in text
    assert "routing.VehicleVar(index) == (vehicle_idx + 1) * active - 1" not in text
