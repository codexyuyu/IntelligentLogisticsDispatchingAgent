from copy import deepcopy
from pathlib import Path
import json

from app.domain.transport_rules import validate_transport

ROOT = Path(__file__).resolve().parents[2]
REQUEST = ROOT / "../contracts/examples/routing_request.json"


def payload():
    return json.loads(REQUEST.read_text(encoding="utf-8"))


def one_order_case():
    data = payload()
    order = data["snapshot"]["orders"][0]
    vehicle = data["snapshot"]["vehicles"][0]
    warehouse = next(w for w in data["snapshot"]["warehouses"] if w["warehouse_id"] == vehicle["warehouse_id"])
    handoff = data["warehouse_handoffs"][0]
    data["order_ids"] = [order["order_id"]]
    data["warehouse_handoffs"] = [handoff]
    data["snapshot"]["orders"] = [order]
    data["snapshot"]["vehicles"] = [vehicle]
    data["snapshot"]["warehouses"] = [warehouse]
    data["snapshot"]["resources"] = []
    data["snapshot"]["stock_lots"] = []
    data["snapshot"]["operations"] = []
    data["snapshot"]["frozen_operations"] = []
    return data


def valid_result(data):
    snap = data["snapshot"]
    order = snap["orders"][0]
    vehicle = snap["vehicles"][0]
    depot = vehicle["start_node_id"]
    destination = order["delivery_node_id"]
    matrix = snap["matrix"]
    a = matrix["node_ids"].index(depot)
    b = matrix["node_ids"].index(destination)
    travel = matrix["duration_s"][a][b]
    distance = matrix["distance_m"][a][b]
    return_travel = matrix["duration_s"][b][a]
    return_distance = matrix["distance_m"][b][a]
    start = 600
    arrival = start + travel
    departure = arrival + order["service_duration_s"]
    end = departure + return_travel
    return {
        "metadata": {"status": "feasible", "has_solution": True},
        "routes": [{
            "vehicle_id": vehicle["vehicle_id"],
            "distance_m": distance + return_distance,
            "duration_s": end - start,
            "stops": [
                {"node_id": depot, "order_ids": [], "stop_kind": "depot_start", "arrival_at_s": start, "service_start_at_s": start, "departure_at_s": start, "load_weight_kg": order["weight_kg"], "load_volume_l": order["volume_l"]},
                {"node_id": destination, "order_ids": [order["order_id"]], "stop_kind": "delivery", "arrival_at_s": arrival, "service_start_at_s": arrival, "departure_at_s": departure, "load_weight_kg": 0, "load_volume_l": 0},
                {"node_id": depot, "order_ids": [], "stop_kind": "depot_end", "arrival_at_s": end, "service_start_at_s": end, "departure_at_s": end, "load_weight_kg": 0, "load_volume_l": 0},
            ],
        }],
        "warehouse_arrivals": [{
            "vehicle_id": vehicle["vehicle_id"],
            "warehouse_id": vehicle["warehouse_id"],
            "arrival_at_s": end,
            "order_ids": [order["order_id"]],
        }],
        "unserved_orders": [],
    }


def test_validator_accepts_plain_valid_result():
    data = one_order_case()
    report = validate_transport(request=data, result=valid_result(data))
    assert report.passed, report.violations


def test_validator_rejects_forged_travel_time():
    data = one_order_case()
    result = valid_result(data)
    result["routes"][0]["stops"][1]["arrival_at_s"] = 600
    result["routes"][0]["stops"][1]["service_start_at_s"] = 600
    result["routes"][0]["stops"][1]["departure_at_s"] = 900
    report = validate_transport(request=data, result=result)
    assert any(v.startswith("travel_time:") for v in report.violations)
