from datetime import datetime, timezone
from copy import deepcopy

from app.application.handle_event import handle_event
from app.application.runtime import runtime
from app.contracts.common import SolveMetadata, Source, TimeWindow, ValidationReport
from app.contracts.entities import Order, PlanningSnapshot, TravelMatrix, Vehicle, Warehouse
from app.contracts.events import DispatchEvent, EventPayload
from app.contracts.planning import CandidatePlan, RoutingResult, RouteStop, VehicleArrival, VehicleRoute, WarehouseHandoff, WarehouseScheduleResult


def _source():
    return Source(source_kind="default", source_ref="b04-test", observed_at=datetime.now(timezone.utc), rule_version="test-1")


def _snapshot():
    return PlanningSnapshot(
        snapshot_id="snap_b04", version=1, origin_at=datetime.now(timezone.utc), simulation_time_s=0,
        rule_version="test-1",
        orders=(Order(order_id="ord_001", version=1, warehouse_id="wh_001", batch_id="bat_001",
                      delivery_node_id="node_customer", quantity_units=10, weight_kg=100, volume_l=100,
                      temperature_zone="chilled", service_window=TimeWindow(start_s=0, end_s=10000),
                      service_duration_s=60, freshness_deadline_s=10000, required=True, source=_source()),),
        vehicles=(
            Vehicle(vehicle_id="veh_001", version=1, warehouse_id="wh_001", start_node_id="node_wh",
                    end_node_id="node_wh", current_node_id="node_wh", capacity_weight_kg=1000,
                    capacity_volume_l=1000, remaining_weight_kg=1000, remaining_volume_l=1000,
                    temperature_zone="chilled", shift_window=TimeWindow(start_s=0, end_s=20000),
                    available_at_s=0, source=_source()),
            Vehicle(vehicle_id="veh_002", version=1, warehouse_id="wh_001", start_node_id="node_wh",
                    end_node_id="node_wh", current_node_id="node_wh", capacity_weight_kg=1000,
                    capacity_volume_l=1000, remaining_weight_kg=1000, remaining_volume_l=1000,
                    temperature_zone="chilled", shift_window=TimeWindow(start_s=0, end_s=20000),
                    available_at_s=0, source=_source()),
        ),
        warehouses=(Warehouse(warehouse_id="wh_001", version=1, node_id="node_wh", temperature_zones=("chilled",)),),
        resources=(), stock_lots=(), operations=(), frozen_operations=(),
        matrix=TravelMatrix(matrix_id="mat_001", version=1, node_ids=("node_wh", "node_customer"),
                            duration_s=((0, 600), (600, 0)), distance_m=((0, 1000), (1000, 0)), source=_source()),
    )


def _route(vehicle_id, *, with_order, start=1200):
    if with_order:
        stops = (
            RouteStop(node_id="node_wh", order_ids=(), stop_kind="depot_start", arrival_at_s=start,
                      service_start_at_s=start, departure_at_s=start, load_weight_kg=100, load_volume_l=100),
            RouteStop(node_id="node_customer", order_ids=("ord_001",), stop_kind="delivery", arrival_at_s=start + 600,
                      service_start_at_s=start + 600, departure_at_s=start + 660, load_weight_kg=0, load_volume_l=0),
            RouteStop(node_id="node_wh", order_ids=(), stop_kind="depot_end", arrival_at_s=start + 1260,
                      service_start_at_s=start + 1260, departure_at_s=start + 1260, load_weight_kg=0, load_volume_l=0),
        )
    else:
        stops = (
            RouteStop(node_id="node_wh", order_ids=(), stop_kind="depot_start", arrival_at_s=start,
                      service_start_at_s=start, departure_at_s=start, load_weight_kg=0, load_volume_l=0),
            RouteStop(node_id="node_wh", order_ids=(), stop_kind="depot_end", arrival_at_s=start,
                      service_start_at_s=start, departure_at_s=start, load_weight_kg=0, load_volume_l=0),
        )
    return VehicleRoute(vehicle_id=vehicle_id, stops=stops, distance_m=2000 if with_order else 0,
                        duration_s=1260 if with_order else 0)


def _routing(*, moved_to_second: bool):
    routes = (_route("veh_001", with_order=not moved_to_second), _route("veh_002", with_order=moved_to_second))
    return RoutingResult(
        snapshot_id="snap_b04", snapshot_version=2, metadata=SolveMetadata(
            status="feasible", raw_status="TEST_FAKE", engine="fake", engine_version="1",
            has_solution=True, proof_scope="test", solve_ms=1),
        routes=routes,
        warehouse_arrivals=(
            VehicleArrival(vehicle_id="veh_001", warehouse_id="wh_001", arrival_at_s=2460 if not moved_to_second else 1200,
                           order_ids=("ord_001",) if not moved_to_second else ()),
            VehicleArrival(vehicle_id="veh_002", warehouse_id="wh_001", arrival_at_s=2460 if moved_to_second else 1200,
                           order_ids=("ord_001",) if moved_to_second else ()),
        ),
        unserved_orders=(),
    )


def test_b04_vehicle_delay_moves_only_affected_order(monkeypatch):
    snapshot = _snapshot()
    runtime.put_snapshot(snapshot)
    handoff = WarehouseHandoff(order_id="ord_001", warehouse_id="wh_001", ready_at_s=1200,
                               loading_window=TimeWindow(start_s=1200, end_s=2400))
    warehouse = WarehouseScheduleResult(
        snapshot_id="snap_b04", snapshot_version=1,
        metadata=SolveMetadata(status="feasible", raw_status="TEST", engine="fake", engine_version="1",
                               has_solution=True, proof_scope="test", solve_ms=1),
        operations=(), warehouse_handoffs=(handoff,))
    old_routing = _routing(moved_to_second=False).model_copy(update={"snapshot_version": 1})
    old_plan = CandidatePlan(
        plan_id="plan_old", snapshot_id="snap_b04", snapshot_version=1, version=1,
        plan_hash="a" * 64, routing=old_routing, warehouse=warehouse,
        validation=ValidationReport(status="passed", validator_version="test", checked_rule_ids=("test",), violations=()),
    )

    def fake_solve(self, request):
        assert request.snapshot.version == 2
        assert request.snapshot.vehicles[0].available_at_s == 600
        assert request.frozen_routes[0].vehicle_id == "veh_002"
        return _routing(moved_to_second=True)

    monkeypatch.setattr("app.application.handle_event.OrToolsRoutingSolver.solve", fake_solve)
    event = DispatchEvent(
        event_id="evt_001", event_type="departure_delayed", snapshot_id="snap_b04", expected_snapshot_version=1,
        object_id="veh_001", occurred_at_s=0, received_at=datetime.now(timezone.utc), source=_source(),
        payload=EventPayload(delay_s=600),
    )
    result = handle_event(event=event, previous_plan=old_plan, budget_ms=10000)
    assert result.validation.status == "passed"
    assert result.impact.affected_order_ids == ("ord_001",)
    assert result.diff.changed_order_ids == ("ord_001",)
    assert result.replanned_plan.version == 2
    assert result.replanned_plan.snapshot_version == 2
    assert runtime.get_snapshot("snap_b04", 2).vehicles[0].available_at_s == 600


def test_b04_keeps_request_local_order_scope(monkeypatch):
    base = _snapshot()
    extra = Order(order_id="ord_002", version=1, warehouse_id="wh_001", batch_id="bat_002",
                  delivery_node_id="node_customer", quantity_units=5, weight_kg=50, volume_l=50,
                  temperature_zone="chilled", service_window=TimeWindow(start_s=0, end_s=10000),
                  service_duration_s=60, freshness_deadline_s=10000, required=True, source=_source())
    snapshot = base.model_copy(update={"orders": base.orders + (extra,)})
    runtime.put_snapshot(snapshot)
    handoff = WarehouseHandoff(order_id="ord_001", warehouse_id="wh_001", ready_at_s=1200,
                               loading_window=TimeWindow(start_s=1200, end_s=2400))
    warehouse = WarehouseScheduleResult(
        snapshot_id="snap_b04", snapshot_version=1,
        metadata=SolveMetadata(status="feasible", raw_status="TEST", engine="fake", engine_version="1",
                               has_solution=True, proof_scope="test", solve_ms=1),
        operations=(), warehouse_handoffs=(handoff,))
    old_routing = _routing(moved_to_second=False).model_copy(update={"snapshot_version": 1})
    old_plan = CandidatePlan(
        plan_id="plan_old_local", snapshot_id="snap_b04", snapshot_version=1, version=1,
        plan_hash="b" * 64, routing=old_routing, warehouse=warehouse,
        validation=ValidationReport(status="passed", validator_version="test", checked_rule_ids=("test",), violations=()),
    )

    def fake_solve(self, request):
        assert request.order_ids == ("ord_001",)
        assert request.warehouse_handoffs and request.warehouse_handoffs[0].order_id == "ord_001"
        return _routing(moved_to_second=True)

    monkeypatch.setattr("app.application.handle_event.OrToolsRoutingSolver.solve", fake_solve)
    event = DispatchEvent(
        event_id="evt_local_scope_001", event_type="departure_delayed", snapshot_id="snap_b04", expected_snapshot_version=1,
        object_id="veh_001", occurred_at_s=0, received_at=datetime.now(timezone.utc), source=_source(),
        payload=EventPayload(delay_s=600, affected_order_ids=("ord_001",)),
    )
    result = handle_event(event=event, previous_plan=old_plan, budget_ms=10000)
    assert result.validation.status == "passed"
