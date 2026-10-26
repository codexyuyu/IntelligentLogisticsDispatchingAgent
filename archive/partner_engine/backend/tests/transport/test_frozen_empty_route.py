"""Regression: a frozen route with no delivery must not lock an idle vehicle out.

R19 measured this defect (stress family, B-04 local reschedule returned
`ROUTING_NO_SOLUTION` in 2-136 ms because `_apply_frozen_routes` pinned
`NextVar(start) = end` for frozen empty routes, forbidding the spare vehicle from
serving the very orders it existed to recover).
"""
from datetime import datetime, timezone
from pathlib import Path

from app.adapters.routing.ortools_solver import OrToolsRoutingSolver
from app.contracts.common import Source, TimeWindow
from app.contracts.entities import Order, PlanningSnapshot, TravelMatrix, Vehicle, Warehouse
from app.contracts.planning import RouteStop, RoutingRequest, VehicleRoute, WarehouseHandoff

SOURCE = Source(source_kind="default", source_ref="frozen-empty-route-test",
                observed_at=datetime.now(timezone.utc), rule_version="test-1")


def _snapshot() -> PlanningSnapshot:
    orders = tuple(
        Order(order_id=f"ord_00{i}", version=1, warehouse_id="wh_1", batch_id=f"bat_00{i}",
              delivery_node_id=f"node_c{i}", quantity_units=1, weight_kg=100, volume_l=100,
              temperature_zone="chilled", service_window=TimeWindow(start_s=0, end_s=5000),
              service_duration_s=60, freshness_deadline_s=5000, required=True, source=SOURCE)
        for i in (1, 2)
    )
    # veh_1 is delayed far past every window; veh_2 is the idle spare.
    vehicles = (
        Vehicle(vehicle_id="veh_1", version=1, warehouse_id="wh_1", start_node_id="node_wh",
                end_node_id="node_wh", current_node_id="node_wh", capacity_weight_kg=1000,
                capacity_volume_l=1000, remaining_weight_kg=1000, remaining_volume_l=1000,
                temperature_zone="chilled", shift_window=TimeWindow(start_s=0, end_s=200000),
                available_at_s=100000, source=SOURCE),
        Vehicle(vehicle_id="veh_2", version=1, warehouse_id="wh_1", start_node_id="node_wh",
                end_node_id="node_wh", current_node_id="node_wh", capacity_weight_kg=1000,
                capacity_volume_l=1000, remaining_weight_kg=1000, remaining_volume_l=1000,
                temperature_zone="chilled", shift_window=TimeWindow(start_s=0, end_s=200000),
                available_at_s=0, source=SOURCE),
    )
    return PlanningSnapshot(
        snapshot_id="snap_frozen_empty", version=1, origin_at=datetime.now(timezone.utc),
        simulation_time_s=0, rule_version="test-1", orders=orders, vehicles=vehicles,
        warehouses=(Warehouse(warehouse_id="wh_1", version=1, node_id="node_wh",
                              temperature_zones=("chilled",)),),
        resources=(), stock_lots=(), operations=(), frozen_operations=(),
        matrix=TravelMatrix(
            matrix_id="mat_1", version=1, node_ids=("node_wh", "node_c1", "node_c2"),
            duration_s=((0, 100, 200), (100, 0, 100), (200, 100, 0)),
            distance_m=((0, 1000, 2000), (1000, 0, 1000), (2000, 1000, 0)), source=SOURCE),
    )


def _empty_route(vehicle_id: str) -> VehicleRoute:
    stop = RouteStop(node_id="node_wh", order_ids=(), stop_kind="depot_start", arrival_at_s=0,
                     service_start_at_s=0, departure_at_s=0, load_weight_kg=0, load_volume_l=0)
    end = stop.model_copy(update={"stop_kind": "depot_end"})
    return VehicleRoute(vehicle_id=vehicle_id, stops=(stop, end), distance_m=0, duration_s=0)


def _request(*, freeze_empty_spare: bool) -> RoutingRequest:
    snapshot = _snapshot()
    return RoutingRequest(
        snapshot=snapshot, order_ids=("ord_001", "ord_002"),
        warehouse_handoffs=tuple(
            WarehouseHandoff(order_id=f"ord_00{i}", warehouse_id="wh_1", ready_at_s=0,
                             loading_window=TimeWindow(start_s=0, end_s=5000))
            for i in (1, 2)),
        frozen_routes=(_empty_route("veh_2"),) if freeze_empty_spare else (),
        budget={"remaining_ms": 5000, "max_workers": 1, "random_seed": 17},
    )


def test_frozen_empty_route_does_not_forbid_that_vehicle_from_serving():
    result = OrToolsRoutingSolver().solve(_request(freeze_empty_spare=True))
    assert result.metadata.has_solution, result.metadata.raw_status
    used = {route.vehicle_id: tuple(oid for stop in route.stops if stop.stop_kind == "delivery"
                                    for oid in stop.order_ids)
            for route in result.routes}
    assert sorted(used["veh_2"]) == ["ord_001", "ord_002"]
    assert used["veh_1"] == ()


def test_frozen_empty_route_matches_unfrozen_result():
    frozen = OrToolsRoutingSolver().solve(_request(freeze_empty_spare=True))
    open_request = OrToolsRoutingSolver().solve(_request(freeze_empty_spare=False))
    assert frozen.metadata.has_solution and open_request.metadata.has_solution
    assert (sum(r.distance_m for r in frozen.routes)
            == sum(r.distance_m for r in open_request.routes))


def test_solver_source_keeps_the_empty_frozen_route_guard():
    source = Path(__file__).resolve().parents[2] / "app/adapters/routing/ortools_solver.py"
    text = source.read_text(encoding="utf-8")
    assert "if not deliveries:" in text
    assert "A frozen route with no committed delivery freezes no work" in text
