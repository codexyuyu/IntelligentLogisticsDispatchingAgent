"""Generate deterministic tiny master-data scenarios (P04-01).

The generated files are plain JSON fixtures: no database and no random UUIDs. Re-running the
script must produce byte-identical files. They intentionally contain only master data and a
travel matrix so the transport API can run before warehouse/event fixtures are finished.
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from uuid import UUID, uuid5

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "scenarios"
NAMESPACE = UUID("4f2f1f6e-9e6f-5c1c-9a5b-6f7a8b9c0d1e")
EPOCH = "2026-01-01T00:00:00Z"
HORIZON = 86400
ACTOR = "00000000-0000-0000-0000-000000000001"
SCOPE = "11111111-1111-4111-8111-111111111111"


def uid(name: str) -> str:
    return str(uuid5(NAMESPACE, name))


def calendar(units: int = 1) -> dict:
    return {
        "schema_version": "2.0.0",
        "epoch_utc": EPOCH,
        "version": 0,
        "intervals": [{"start_s": 0, "end_s": HORIZON, "available_units": units}],
    }


def entity(name: str, status: str, extra: dict) -> dict:
    return {
        "id": uid(name), "status": status, "created_at": EPOCH, "updated_at": EPOCH,
        "row_version": 0, "schema_version": "2.0.0", "created_by": ACTOR, **extra,
    }


def build() -> dict:
    wh = uid("warehouse:WH1")
    zone = uid("zone:Z1")
    location = uid("location:L1")
    dock = uid("dock:D1")
    driver = uid("driver:DR1")
    vehicle = uid("vehicle:V1")
    nodes = {
        "warehouse": uid("node:WH1"),
        "p1": uid("node:P1"), "d1": uid("node:D1"),
        "p2": uid("node:P2"), "d2": uid("node:D2"),
    }
    node_list = list(nodes.values())
    distances = [
        [0, 5000, 9000, 7000, 12000],
        [5000, 0, 4000, 3000, 8000],
        [9000, 4000, 0, 6000, 3000],
        [7000, 3000, 6000, 0, 5000],
        [12000, 8000, 3000, 5000, 0],
    ]
    matrix_payload = {
        "id": uid("matrix:M1"), "version": 1, "node_ids": node_list,
        "distance_m": distances,
        "travel_s": [[(value // 10) for value in row] for row in distances],
        "source": "fixture", "observed_at": EPOCH,
        "hash": "b" * 64,
    }
    orders = []
    cargo = []
    for index, (pickup, delivery, weight, volume) in enumerate(
            ((nodes["p1"], nodes["d1"], 12000, 8000),
             (nodes["p2"], nodes["d2"], 8000, 5000)), start=1):
        order_id = uid(f"order:O{index}")
        cargo_id = uid(f"cargo:C{index}")
        orders.append(entity(f"order:O{index}", "draft", {
            "external_ref": f"T1-O{index}",
            "pickup_node_id": pickup, "delivery_node_id": delivery,
            "cargo_ids": [cargo_id],
            "pickup_window": {"earliest_s": 0, "latest_s": 3600},
            "delivery_window": {"earliest_s": 0, "latest_s": 7200},
            "service_s": 300, "soft_due_at_s": None, "must_serve": True,
            "priority": 1,
        }))
        cargo.append(entity(f"cargo:C{index}", "registered", {
            "order_id": order_id, "cargo_type": "GENERAL", "quantity_units": 1,
            "weight_g": weight, "volume_cm3": volume,
            "min_temp_decic": 0, "max_temp_decic": 80, "max_exposure_s": 3600,
            "batch_ref": f"B{index}",
        }))
    return {
        "schema_version": "2.0.0",
        "scope_id": SCOPE,
        "created_by": ACTOR,
        "warehouses": [entity("warehouse:WH1", "active", {
            "code": "WH1", "name": "Tiny Warehouse", "node_id": nodes["warehouse"],
            "timezone": "UTC", "calendar": calendar(1),
        })],
        "zones": [entity("zone:Z1", "active", {
            "warehouse_id": wh, "code": "Z1", "setpoint_decic": 40,
            "capacity_weight_g": 1000000, "capacity_volume_cm3": 1000000,
            "allowed_cargo_types": ["GENERAL"],
        })],
        "locations": [entity("location:L1", "available", {
            "zone_id": zone, "code": "L1", "capacity_weight_g": 500000,
            "capacity_volume_cm3": 500000, "calendar": calendar(1),
        })],
        "docks": [entity("dock:D1", "available", {
            "warehouse_id": wh, "code": "D1", "supported_operations": ["receive", "load"],
            "allowed_zone_ids": [zone], "calendar": calendar(1),
        })],
        "workers": [entity("worker:W1", "available", {
            "warehouse_id": wh, "skills": ["picking"], "allowed_zone_ids": [zone],
            "calendar": calendar(1), "pool_id": None,
        })],
        "equipment": [entity("equipment:E1", "available", {
            "warehouse_id": wh, "kind": "handling", "quantity_capacity": 2,
            "allowed_zone_ids": [zone], "calendar": calendar(2),
        })],
        "drivers": [entity("driver:DR1", "active", {
            "code": "DR1", "qualifications": ["general"],
            "shift": {"earliest_s": 0, "latest_s": HORIZON},
            "max_drive_s": 28800, "max_work_s": 36000,
        })],
        "vehicles": [entity("vehicle:V1", "available", {
            "code": "V1", "capacity_weight_g": 50000, "capacity_volume_cm3": 40000,
            "setpoint_decic": 40, "allowed_cargo_types": ["GENERAL"],
            "start_node_id": nodes["warehouse"], "end_node_id": nodes["warehouse"],
            "calendar": calendar(1), "driver_id": driver,
            "fixed_cost_cents": 5000, "rate_cents_per_km": 220,
        })],
        "orders": orders,
        "cargo": cargo,
        "matrices": [{
            "id": matrix_payload["id"], "version": 1, "scope_id": SCOPE,
            "hash": matrix_payload["hash"], "created_at": EPOCH,
            "payload": matrix_payload,
        }],
        "warehouse_ids": [wh], "vehicle_ids": [vehicle],
        "order_ids": [item["id"] for item in orders],
    }


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    payload = build()
    text = json.dumps(payload, ensure_ascii=False, sort_keys=True, indent=2) + "\n"
    (OUT / "tiny_master.json").write_text(text, encoding="utf-8")
    scenario_entries = [{"name": "tiny_master", "path": "tiny_master.json",
                         "sha256": hashlib.sha256(text.encode()).hexdigest()}]
    # The 10-order integration fixture has its own generator; keep its entry
    # when regenerating the canonical tiny master-data fixture.
    chain_path = OUT / "coldchain_chain_10.json"
    if chain_path.is_file():
        scenario_entries.append({"name": "coldchain_chain_10", "path": chain_path.name,
                                 "sha256": hashlib.sha256(chain_path.read_bytes()).hexdigest()})
    (OUT / "manifest.json").write_text(json.dumps({
        "schema_version": "2.0.0", "scenarios": scenario_entries,
    }, ensure_ascii=False, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    invalid = {"schema_version": "2.0.0", "scenarios": {
        "tiny_master": [{"code": "invalid_temperature", "field": "cargo.min_temp_decic",
                         "expected": "min<=max"}]}}
    (OUT / "invalid_cases.json").write_text(
        json.dumps(invalid, ensure_ascii=False, sort_keys=True, indent=2) + "\n",
        encoding="utf-8")


if __name__ == "__main__":
    main()
