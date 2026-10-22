"""R20: B-04 now handles three event types, not just departure_delayed.

  departure_delayed   unchanged (regression covered by test_b04_reschedule.py)
  dock_unavailable    a warehouse cannot load before a time -> loading window shifts,
                      orders whose window closes before that are recorded unserved
  cargo_quarantined   orders are removed from the replan and recorded unserved
weather_changed and demand_changed still raise b04_event_type_not_implemented.
"""
from datetime import datetime, timezone

import pytest

from app.application.handle_event import _derive_snapshot_for_event, handle_event
from app.application.impact_analysis import find_affected_work
from app.application.runtime import runtime
from app.contracts.common import SolveMetadata, Source, TimeWindow, ValidationReport
from app.contracts.entities import Order, PlanningSnapshot, TravelMatrix, Vehicle, Warehouse
from app.contracts.events import DispatchEvent, EventPayload
from app.contracts.planning import (
    CandidatePlan, RouteStop, RoutingResult, VehicleArrival, VehicleRoute, WarehouseHandoff,
    WarehouseScheduleResult,
)

DURATION = ((0, 600, 600), (600, 0, 600), (600, 600, 0))
DISTANCE = ((0, 1000, 1000), (1000, 0, 1000), (1000, 1000, 0))


def _source() -> Source:
    return Source(source_kind="default", source_ref="b04-events-test",
                  observed_at=datetime.now(timezone.utc), rule_version="test-1")


def _snapshot() -> PlanningSnapshot:
    orders = tuple(
        Order(order_id=f"ord_00{i}", version=1, warehouse_id="wh_1", batch_id=f"bat_00{i}",
              delivery_node_id=f"node_c{i}", quantity_units=1, weight_kg=100, volume_l=100,
              temperature_zone="chilled", service_window=TimeWindow(start_s=0, end_s=8000),
              service_duration_s=60, freshness_deadline_s=8000, required=True, source=_source())
        for i in (1, 2)
    )
    vehicles = tuple(
        Vehicle(vehicle_id=f"veh_00{i}", version=1, warehouse_id="wh_1", start_node_id="node_wh",
                end_node_id="node_wh", current_node_id="node_wh", capacity_weight_kg=1000,
                capacity_volume_l=1000, remaining_weight_kg=1000, remaining_volume_l=1000,
                temperature_zone="chilled", shift_window=TimeWindow(start_s=0, end_s=20000),
                available_at_s=0, source=_source())
        for i in (1, 2)
    )
    return PlanningSnapshot(
        snapshot_id="snap_b04_events", version=1, origin_at=datetime.now(timezone.utc),
        simulation_time_s=0, rule_version="test-1", orders=orders, vehicles=vehicles,
        warehouses=(Warehouse(warehouse_id="wh_1", version=1, node_id="node_wh",
                              temperature_zones=("chilled",)),),
        resources=(), stock_lots=(), operations=(), frozen_operations=(),
        matrix=TravelMatrix(matrix_id="mat_events", version=1,
                            node_ids=("node_wh", "node_c1", "node_c2"),
                            duration_s=DURATION, distance_m=DISTANCE, source=_source()),
    )


def _handoffs() -> tuple[WarehouseHandoff, ...]:
    return (
        WarehouseHandoff(order_id="ord_001", warehouse_id="wh_1", ready_at_s=1200,
                         loading_window=TimeWindow(start_s=1200, end_s=3000)),
        WarehouseHandoff(order_id="ord_002", warehouse_id="wh_1", ready_at_s=2400,
                         loading_window=TimeWindow(start_s=2400, end_s=4000)),
    )


def _serving_route(vehicle_id: str, node_id: str, order_id: str, start: int) -> VehicleRoute:
    return VehicleRoute(
        vehicle_id=vehicle_id,
        stops=(
            RouteStop(node_id="node_wh", order_ids=(), stop_kind="depot_start", arrival_at_s=start,
                      service_start_at_s=start, departure_at_s=start, load_weight_kg=100,
                      load_volume_l=100),
            RouteStop(node_id=node_id, order_ids=(order_id,), stop_kind="delivery",
                      arrival_at_s=start + 600, service_start_at_s=start + 600,
                      departure_at_s=start + 660, load_weight_kg=0, load_volume_l=0),
            RouteStop(node_id="node_wh", order_ids=(), stop_kind="depot_end",
                      arrival_at_s=start + 1260, service_start_at_s=start + 1260,
                      departure_at_s=start + 1260, load_weight_kg=0, load_volume_l=0),
        ),
        distance_m=2000, duration_s=1260)


def _idle_route(vehicle_id: str, at: int = 0) -> VehicleRoute:
    stop = RouteStop(node_id="node_wh", order_ids=(), stop_kind="depot_start", arrival_at_s=at,
                     service_start_at_s=at, departure_at_s=at, load_weight_kg=0, load_volume_l=0)
    return VehicleRoute(vehicle_id=vehicle_id,
                        stops=(stop, stop.model_copy(update={"stop_kind": "depot_end"})),
                        distance_m=0, duration_s=0)


def _routing(*, first_start: int, first_order: str | None, second_start: int,
             second_order: str | None, version: int = 1) -> RoutingResult:
    first = (_serving_route("veh_001", "node_c1", first_order, first_start) if first_order
             else _idle_route("veh_001"))
    second = (_serving_route("veh_002", "node_c2", second_order, second_start) if second_order
              else _idle_route("veh_002"))
    first_end = first.stops[-1].arrival_at_s
    second_end = second.stops[-1].arrival_at_s
    return RoutingResult(
        snapshot_id="snap_b04_events", snapshot_version=version,
        metadata=SolveMetadata(status="feasible", raw_status="TEST_FAKE", engine="fake",
                               engine_version="1", has_solution=True, proof_scope="test",
                               solve_ms=1),
        routes=(first, second),
        warehouse_arrivals=(
            VehicleArrival(vehicle_id="veh_001", warehouse_id="wh_1", arrival_at_s=first_end,
                           order_ids=(first_order,) if first_order else ()),
            VehicleArrival(vehicle_id="veh_002", warehouse_id="wh_1", arrival_at_s=second_end,
                           order_ids=(second_order,) if second_order else ()),
        ),
        unserved_orders=(),
    )


def _baseline_plan() -> CandidatePlan:
    warehouse = WarehouseScheduleResult(
        snapshot_id="snap_b04_events", snapshot_version=1,
        metadata=SolveMetadata(status="feasible", raw_status="TEST", engine="fake",
                               engine_version="1", has_solution=True, proof_scope="test",
                               solve_ms=1),
        operations=(), warehouse_handoffs=_handoffs())
    routing = _routing(first_start=1200, first_order="ord_001", second_start=2400,
                       second_order="ord_002")
    return CandidatePlan(
        plan_id="plan_baseline_events", snapshot_id="snap_b04_events", snapshot_version=1,
        version=1, plan_hash="a" * 64, routing=routing, warehouse=warehouse,
        validation=ValidationReport(status="passed", validator_version="test",
                                    checked_rule_ids=("test",), violations=()))


def _event(event_type: str, *, object_id: str, payload: EventPayload, event_id: str) -> DispatchEvent:
    return DispatchEvent(
        event_id=event_id, event_type=event_type, snapshot_id="snap_b04_events",
        expected_snapshot_version=1, object_id=object_id, occurred_at_s=0,
        received_at=datetime.now(timezone.utc), source=_source(), payload=payload)


def _dock_event(until: int, event_id: str = "evt_dock_test") -> DispatchEvent:
    return _event("dock_unavailable", object_id="wh_1",
                  payload=EventPayload(unavailable_until_s=until), event_id=event_id)


def _quarantine_event(order_ids: tuple[str, ...], event_id: str = "evt_quar_test") -> DispatchEvent:
    return _event("cargo_quarantined", object_id="bat_001",
                  payload=EventPayload(affected_order_ids=order_ids), event_id=event_id)


# --- impact analysis -------------------------------------------------------------------

def test_dock_unavailable_affects_only_vehicles_that_would_load_before_reopening():
    impact = find_affected_work(event=_dock_event(2000), plan=_baseline_plan())
    assert impact.affected_order_ids == ("ord_001",)   # veh_001 departs 1200 < 2000
    assert impact.locked_order_ids == ("ord_002",)     # veh_002 departs 2400 >= 2000
    assert impact.affected_vehicle_ids == ("veh_001",)


def test_dock_unavailable_requires_a_positive_time_and_a_known_warehouse():
    with pytest.raises(ValueError, match="dock_unavailable_requires_positive"):
        find_affected_work(event=_dock_event(0), plan=_baseline_plan())
    unknown = _event("dock_unavailable", object_id="wh_9",
                     payload=EventPayload(unavailable_until_s=2000), event_id="evt_unknown_dock")
    with pytest.raises(ValueError, match="dock_warehouse_not_in_plan"):
        find_affected_work(event=unknown, plan=_baseline_plan())


def test_cargo_quarantined_affects_the_orders_and_their_vehicles():
    impact = find_affected_work(event=_quarantine_event(("ord_001",)), plan=_baseline_plan())
    assert impact.affected_order_ids == ("ord_001",)
    assert impact.affected_vehicle_ids == ("veh_001",)
    assert impact.locked_order_ids == ("ord_002",)


def test_cargo_quarantined_requires_orders_that_are_in_the_plan():
    with pytest.raises(ValueError, match="cargo_quarantined_requires_affected_order_ids"):
        find_affected_work(event=_quarantine_event(()), plan=_baseline_plan())
    with pytest.raises(ValueError, match="quarantined_orders_not_in_plan"):
        find_affected_work(event=_quarantine_event(("ord_999",)), plan=_baseline_plan())


def test_unimplemented_event_types_still_fail_loudly():
    event = _event("weather_changed", object_id="mat_001", payload=EventPayload(),
                   event_id="evt_weather")
    with pytest.raises(ValueError, match="b04_event_type_not_implemented:weather_changed"):
        find_affected_work(event=event, plan=_baseline_plan())
    with pytest.raises(ValueError, match="b04_event_type_not_implemented"):
        _derive_snapshot_for_event(_snapshot(), event)


# --- end-to-end orchestration (fake solver, real validation) ----------------------------

def test_dock_unavailable_shifts_the_loading_window_and_replans_the_affected_vehicle(monkeypatch):
    snapshot = _snapshot()
    runtime.put_snapshot(snapshot)
    baseline = _baseline_plan()
    seen = {}

    def fake_solve(self, request):
        seen["request"] = request
        return _routing(first_start=2000, first_order="ord_001", second_start=2400,
                        second_order="ord_002", version=request.snapshot.version)

    monkeypatch.setattr("app.application.handle_event.OrToolsRoutingSolver.solve", fake_solve)
    result = handle_event(event=_dock_event(2000), previous_plan=baseline, budget_ms=10000)

    request = seen["request"]
    scoped = {h.order_id: h for h in request.warehouse_handoffs}
    assert scoped["ord_001"].loading_window.start_s == 2000   # dock reopens at 2000
    assert scoped["ord_001"].ready_at_s == 1200               # goods readiness unchanged
    assert scoped["ord_002"].loading_window.start_s == 2400   # untouched
    assert request.frozen_routes and request.frozen_routes[0].vehicle_id == "veh_002"

    assert result.impact.affected_order_ids == ("ord_001",)
    assert result.replanned_plan.routing.routes[0].stops[0].departure_at_s == 2000
    replanned = {h.order_id: h for h in result.replanned_plan.warehouse.warehouse_handoffs}
    assert replanned["ord_001"].loading_window.start_s == 2000
    assert "b04.dock.loading_window_shifted" in result.validation.checked_rule_ids


def test_dock_unavailable_records_orders_it_cannot_load(monkeypatch):
    snapshot = _snapshot()
    runtime.put_snapshot(snapshot)
    baseline = _baseline_plan()
    seen = {}

    def fake_solve(self, request):
        seen["request"] = request
        # Only ord_002 is still in scope; veh_002 starts once the dock reopens.
        return _routing(first_start=0, first_order=None, second_start=3500,
                        second_order="ord_002", version=request.snapshot.version)

    monkeypatch.setattr("app.application.handle_event.OrToolsRoutingSolver.solve", fake_solve)
    result = handle_event(event=_dock_event(3500), previous_plan=baseline, budget_ms=10000)

    assert seen["request"].order_ids == ("ord_002",)      # ord_001 cannot be loaded any more
    unserved = {u.order_id: u.reason_code for u in result.replanned_plan.routing.unserved_orders}
    assert unserved == {"ord_001": "dock_unavailable"}
    assert "b04.dock.undeliverable_recorded" in result.validation.checked_rule_ids


def test_cargo_quarantined_drops_the_orders_and_records_them(monkeypatch):
    snapshot = _snapshot()
    runtime.put_snapshot(snapshot)
    baseline = _baseline_plan()
    seen = {}

    def fake_solve(self, request):
        seen["request"] = request
        return _routing(first_start=0, first_order=None, second_start=2400,
                        second_order="ord_002", version=request.snapshot.version)

    monkeypatch.setattr("app.application.handle_event.OrToolsRoutingSolver.solve", fake_solve)
    result = handle_event(event=_quarantine_event(("ord_001",)), previous_plan=baseline,
                          budget_ms=10000)

    assert seen["request"].order_ids == ("ord_002",)
    unserved = {u.order_id: u.reason_code for u in result.replanned_plan.routing.unserved_orders}
    assert unserved == {"ord_001": "cargo_quarantined"}
    assert result.impact.affected_order_ids == ("ord_001",)
    assert "b04.quarantine.orders_removed_and_recorded" in result.validation.checked_rule_ids
    assert result.replanned_plan.version == baseline.version + 1
