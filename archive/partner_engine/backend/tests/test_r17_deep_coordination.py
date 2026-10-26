"""R17 safety / backward-compatibility tests; independent from optional OR-Tools install."""
import json
from pathlib import Path

import pytest

from app.application import coordinator
from app.contracts.common import SolveMetadata, TimeWindow
from app.contracts.entities import PlanningSnapshot, ScheduledOperation
from app.contracts.planning import (
    RouteStop, RoutingResult, VehicleArrival, VehicleRoute,
    WarehouseHandoff, WarehouseScheduleResult, WarehouseDepartureTarget, DispatchRequest,
)
from app.domain.plan_rules import validate_plan

ROOT = Path(__file__).resolve().parents[2]
SNAPSHOT = PlanningSnapshot.model_validate_json((ROOT / "data/scenarios/two_warehouses_20_orders.json").read_text(encoding="utf8"))


def meta():
    return SolveMetadata(status="feasible", raw_status="TEST", engine="stub", engine_version="1",
                         has_solution=True, proof_scope="test", solve_ms=1)


def pair(ready=200, departure=900, distance=2000):
    order = SNAPSHOT.orders[0]
    vehicle = next(v for v in SNAPSHOT.vehicles if v.warehouse_id == order.warehouse_id
                   and v.temperature_zone == order.temperature_zone)
    h = WarehouseHandoff(order_id=order.order_id, warehouse_id=order.warehouse_id,
                         ready_at_s=ready, loading_window=TimeWindow(start_s=ready, end_s=28800))
    wh = WarehouseScheduleResult(snapshot_id=SNAPSHOT.snapshot_id,
        snapshot_version=SNAPSHOT.version, metadata=meta(),
        operations=(ScheduledOperation(operation_id="op_load001", resource_id="res_dock1",
                                       start_s=ready-60, end_s=ready),), warehouse_handoffs=(h,))
    route = VehicleRoute(vehicle_id=vehicle.vehicle_id, distance_m=distance, duration_s=600,
        stops=(
            RouteStop(node_id=vehicle.start_node_id, order_ids=(), stop_kind="depot_start",
                      arrival_at_s=departure, service_start_at_s=departure,
                      departure_at_s=departure, load_weight_kg=order.weight_kg, load_volume_l=order.volume_l),
            RouteStop(node_id=order.delivery_node_id, order_ids=(order.order_id,), stop_kind="delivery",
                      arrival_at_s=departure+180, service_start_at_s=departure+180,
                      departure_at_s=departure+180+order.service_duration_s,
                      load_weight_kg=0, load_volume_l=0),
            RouteStop(node_id=vehicle.end_node_id, order_ids=(), stop_kind="depot_end",
                      arrival_at_s=departure+600, service_start_at_s=departure+600,
                      departure_at_s=departure+600, load_weight_kg=0, load_volume_l=0),
        ))
    rt = RoutingResult(snapshot_id=SNAPSHOT.snapshot_id, snapshot_version=SNAPSHOT.version,
        metadata=meta(), routes=(route,), unserved_orders=(),
        warehouse_arrivals=(VehicleArrival(vehicle_id=vehicle.vehicle_id,
            warehouse_id=order.warehouse_id, arrival_at_s=departure+600,
            order_ids=(order.order_id,)),))
    return wh, rt


def coordinate(**kwargs):
    return coordinator.coordinate(snapshot=SNAPSHOT, order_ids=(SNAPSHOT.orders[0].order_id,), **kwargs)


def test_sequential_backwards_compatible_even_when_max_rounds_is_three(monkeypatch):
    calls = []
    def stub(**kwargs):
        calls.append(kwargs)
        return pair()
    monkeypatch.setattr(coordinator, "_solve_pair", stub)
    result = coordinate(budget_ms=12000, max_coordination_rounds=3)
    assert len(calls) == 1
    assert calls[0]["budget_ms"] == 12000
    assert result.coordination.mode == "sequential"
    assert result.coordination.selected_round == 1
    assert result.coordination.rounds[0].accepted
    assert result.validation.status == "passed"
    assert len(result.plan_hash) == 64


def test_deep_mode_passes_actual_departures_back_and_selects_better_pair(monkeypatch):
    calls = []
    def stub(**kwargs):
        calls.append(kwargs)
        if len(calls) == 1:
            assert not kwargs.get("targets")
            return pair(ready=200)
        if len(calls) == 2:
            assert kwargs["targets"] == (
                WarehouseDepartureTarget(order_id=SNAPSHOT.orders[0].order_id,
                    warehouse_id=SNAPSHOT.orders[0].warehouse_id, departure_at_s=900,
                    vehicle_id=pair()[1].routes[0].vehicle_id),
            )
            return pair(ready=750)
        return pair(ready=750)
    monkeypatch.setattr(coordinator, "_solve_pair", stub)
    result = coordinate(budget_ms=90000, max_coordination_rounds=3, coordination_mode="deep")
    assert len(calls) >= 2
    assert calls[0]["budget_ms"] <= 60000
    assert result.coordination.baseline_distance_m == 2000
    assert result.coordination.selected_distance_m == 2000
    assert result.coordination.baseline_handoff_wait_s == 700
    assert result.coordination.selected_handoff_wait_s == 150
    assert result.coordination.selected_round == 2
    assert result.coordination.rounds[1].accepted
    assert result.warehouse.warehouse_handoffs[0].ready_at_s == 750


def test_deep_mode_never_accepts_worse_transport_distance(monkeypatch):
    calls = []
    def stub(**kwargs):
        calls.append(kwargs)
        return pair(ready=200, distance=2000) if len(calls) == 1 else pair(ready=895, distance=2001)
    monkeypatch.setattr(coordinator, "_solve_pair", stub)
    result = coordinate(budget_ms=90000, max_coordination_rounds=3, coordination_mode="deep")
    assert result.coordination.selected_round == 1
    assert result.coordination.rounds[1].reason == "feasible_not_better"
    assert result.coordination.selected_distance_m == 2000
    assert result.coordination.selected_handoff_wait_s == 700


def test_failure_of_optional_feedback_preserves_valid_initial_plan(monkeypatch):
    calls = []
    def stub(**kwargs):
        calls.append(kwargs)
        if len(calls) == 1: return pair()
        raise RuntimeError("independent_validation_rejected")
    monkeypatch.setattr(coordinator, "_solve_pair", stub)
    result = coordinate(budget_ms=90000, max_coordination_rounds=3, coordination_mode="deep")
    assert result.validation.status == "passed"
    assert result.coordination.selected_round == 1
    assert not result.coordination.rounds[1].accepted
    assert "independent_validation_rejected" in result.coordination.rounds[1].reason


def test_feedback_target_is_departure_not_return_arrival():
    wh, rt = pair(departure=900)
    (target,) = coordinator._departure_targets(SNAPSHOT, rt)
    assert target.departure_at_s == 900
    assert target.vehicle_id == rt.routes[0].vehicle_id
    assert rt.warehouse_arrivals[0].arrival_at_s == 1500


def test_cross_domain_validator_detects_handoff_ready_fraud():
    wh, rt = pair(ready=200)
    payload = wh.model_dump(mode="python")
    payload["warehouse_handoffs"][0]["ready_at_s"] = 120
    snapshot = SNAPSHOT.model_dump(mode="python")
    violations = validate_plan(snapshot=snapshot, order_ids=(SNAPSHOT.orders[0].order_id,),
                               warehouse=payload, routing=rt.model_dump(mode="python"))
    assert "b03.handoff.operation_ready" in {v["rule_id"] for v in violations}


def test_deep_requires_explicit_mode_contract():
    data = dict(snapshot_id=SNAPSHOT.snapshot_id, expected_snapshot_version=1,
                order_ids=(SNAPSHOT.orders[0].order_id,), budget_ms=90000)
    assert DispatchRequest(**data).coordination_mode == "sequential"
    assert DispatchRequest(**data, coordination_mode="deep").coordination_mode == "deep"
    with pytest.raises(Exception):
        DispatchRequest(**data, coordination_mode="instant_magic")


def test_reject_duplicate_scoped_orders_before_solver(monkeypatch):
    def forbidden(**kwargs):
        raise AssertionError("should reject before solver")
    monkeypatch.setattr(coordinator, "_solve_pair", forbidden)
    with pytest.raises(ValueError, match="duplicate_order_ids"):
        coordinator.coordinate(snapshot=SNAPSHOT, order_ids=(SNAPSHOT.orders[0].order_id,) * 2,
                               budget_ms=10000)
