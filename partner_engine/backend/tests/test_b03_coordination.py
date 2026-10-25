import json
from pathlib import Path

import pytest

from app.domain.plan_rules import validate_plan

ROOT = Path(__file__).resolve().parents[2]
SCENARIO = ROOT / "data/scenarios/two_warehouses_20_orders.json"


def test_b03_rules_accept_realistic_warehouse_to_transport_chain():
    snapshot = json.loads(SCENARIO.read_text(encoding="utf-8"))
    order = snapshot["orders"][0]
    vehicle = next(v for v in snapshot["vehicles"] if v["warehouse_id"] == order["warehouse_id"] and v["temperature_zone"] == order["temperature_zone"])
    oid = order["order_id"]
    handoff = {"order_id": oid, "warehouse_id": order["warehouse_id"], "ready_at_s": 1200, "loading_window": {"start_s": 1200, "end_s": 2400}}
    route = {
        "vehicle_id": vehicle["vehicle_id"],
        "stops": [
            {"node_id": vehicle["start_node_id"], "order_ids": [], "stop_kind": "depot_start", "arrival_at_s": 1200, "service_start_at_s": 1200, "departure_at_s": 1200, "load_weight_kg": order["weight_kg"], "load_volume_l": order["volume_l"]},
            {"node_id": order["delivery_node_id"], "order_ids": [oid], "stop_kind": "delivery", "arrival_at_s": 1800, "service_start_at_s": 1800, "departure_at_s": 2100, "load_weight_kg": 0, "load_volume_l": 0},
            {"node_id": vehicle["end_node_id"], "order_ids": [], "stop_kind": "depot_end", "arrival_at_s": 2400, "service_start_at_s": 2400, "departure_at_s": 2400, "load_weight_kg": 0, "load_volume_l": 0},
        ],
        "distance_m": 1000,
        "duration_s": 1200,
    }
    routing = {"routes": [route], "warehouse_arrivals": [{"vehicle_id": vehicle["vehicle_id"], "warehouse_id": order["warehouse_id"], "arrival_at_s": 2400, "order_ids": [oid]}]}
    warehouse = {"warehouse_handoffs": [handoff]}

    assert validate_plan(snapshot=snapshot, order_ids=[oid], warehouse=warehouse, routing=routing) == ()


def test_b03_rules_reject_departure_before_ready_at():
    snapshot = json.loads(SCENARIO.read_text(encoding="utf-8"))
    order = snapshot["orders"][0]
    vehicle = next(v for v in snapshot["vehicles"] if v["warehouse_id"] == order["warehouse_id"] and v["temperature_zone"] == order["temperature_zone"])
    oid = order["order_id"]
    warehouse = {"warehouse_handoffs": [{"order_id": oid, "warehouse_id": order["warehouse_id"], "ready_at_s": 2000, "loading_window": {"start_s": 2000, "end_s": 2600}}]}
    route = {
        "vehicle_id": vehicle["vehicle_id"],
        "stops": [
            {"node_id": vehicle["start_node_id"], "order_ids": [], "stop_kind": "depot_start", "arrival_at_s": 1000, "service_start_at_s": 1000, "departure_at_s": 1000, "load_weight_kg": order["weight_kg"], "load_volume_l": order["volume_l"]},
            {"node_id": order["delivery_node_id"], "order_ids": [oid], "stop_kind": "delivery", "arrival_at_s": 1600, "service_start_at_s": 1600, "departure_at_s": 1900, "load_weight_kg": 0, "load_volume_l": 0},
            {"node_id": vehicle["end_node_id"], "order_ids": [], "stop_kind": "depot_end", "arrival_at_s": 2200, "service_start_at_s": 2200, "departure_at_s": 2200, "load_weight_kg": 0, "load_volume_l": 0},
        ],
        "distance_m": 1000,
        "duration_s": 1200,
    }
    routing = {"routes": [route], "warehouse_arrivals": [{"vehicle_id": vehicle["vehicle_id"], "warehouse_id": order["warehouse_id"], "arrival_at_s": 2200, "order_ids": [oid]}]}
    violations = validate_plan(snapshot=snapshot, order_ids=[oid], warehouse=warehouse, routing=routing)
    assert any(v["rule_id"] == "b03.handoff.ready_at" for v in violations)
