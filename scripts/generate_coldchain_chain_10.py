"""Build the deterministic ten-order cold-chain integration fixture.

The source fixture supplies known-valid contract shapes and a versioned travel
matrix. IDs, operation chains, inventory occupancy and snapshot hash are rebuilt
from typed domain values. No database or live order data is accessed.
"""

from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path
from uuid import UUID, uuid5

from logistics_contracts.coldchain import ColdChainSnapshotDTO
from logistics_contracts.entities import CargoDTO, DriverDTO, OrderDTO, VehicleDTO
from logistics_contracts.integration import ScenarioImport
from logistics_contracts.mapping import snapshot_dto
from logistics_contracts.planning import (
    PlanningScopeDTO,
    ResourceBundleDTO,
    ResourceRevisionDTO,
    TravelMatrixDTO,
)
from logistics_domain.planning import PlanningSnapshot

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "data/scenarios/partner_coldchain_synthetic.json"
OUTPUT = ROOT / "data/scenarios/coldchain_chain_10.json"
NAMESPACE = UUID("d38c591a-574e-48b1-9741-79454d769118")
ORDER_COUNT = 10


def uid(name: str) -> str:
    return str(uuid5(NAMESPACE, f"coldchain-chain-10:{name}"))


def copy_with(source: dict, **changes) -> dict:
    return {**deepcopy(source), **changes}


def revision(kind: str, identity: str) -> dict:
    return {"entity_ref": {"kind": kind, "id": identity, "revision": 0}, "row_version": 0}


def build() -> dict:
    base = json.loads(BASE.read_text(encoding="utf-8"))
    raw = deepcopy(base)
    raw["name"] = "县域冷链十订单入库-分拣-装车联动演示 (合成数据)"
    raw["source_ref"] = "deterministic synthetic 10x3 chain derived from partner coldchain fixture"
    snapshot = raw["snapshot"]
    resources = snapshot["resources"]
    warehouse_id = resources["warehouses"][0]["id"]

    orders, cargo, tasks = [], [], []
    dock_template = resources["docks"][0]
    worker_template = resources["workers"][0]
    equipment_template = resources["equipment"][0]
    location_template = resources["locations"][0]
    templates = {
        "dock": dock_template,
        "worker": worker_template,
        "equipment": equipment_template,
        "location": location_template,
    }
    counts = {"dock": 6, "worker": 4, "equipment": 2, "location": 6}
    bindings = {b["resource_id"]: b for b in resources["calendars"]}

    # Keep the original warehouse and zone; replace the other resource lists.
    resources["calendars"] = [deepcopy(bindings[warehouse_id])]
    for kind, count in counts.items():
        key = {"dock": "docks", "worker": "workers", "equipment": "equipment", "location": "locations"}[kind]
        resources[key] = []
        for index in range(1, count + 1):
            identity = uid(f"{kind}:{index}")
            item = copy_with(templates[kind], id=identity)
            if kind in ("dock", "location"):
                item["code"] = f"{kind[0].upper()}{index}"
            if kind == "dock":
                item["supported_operations"] = ["receive", "load"]
            if kind == "location":
                item["capacity_weight_g"] = 500000
                item["capacity_volume_cm3"] = 100000
            resources[key].append(item)
            binding = copy_with(bindings[templates[kind]["id"]], resource_id=identity)
            resources["calendars"].append(binding)

    vehicles, drivers = [], []
    for index in range(1, 5):
        driver_id = uid(f"driver:{index}")
        vehicle_id = uid(f"vehicle:{index}")
        drivers.append(copy_with(snapshot["drivers"][0], id=driver_id, code=f"CC-DR{index}"))
        vehicles.append(
            copy_with(
                snapshot["vehicles"][0],
                id=vehicle_id,
                code=f"CC-V{index}",
                driver_id=driver_id,
                capacity_weight_g=60000,
                capacity_volume_cm3=40000,
            )
        )
    snapshot["drivers"] = drivers
    snapshot["vehicles"] = vehicles
    snapshot["scope"]["vehicle_ids"] = [v["id"] for v in vehicles]
    raw["available_at_s"] = {v["id"]: 0 for v in vehicles}

    dock_ids = [item["id"] for item in resources["docks"]]
    worker_ids = [item["id"] for item in resources["workers"]]
    equipment_ids = [item["id"] for item in resources["equipment"]]
    location_ids = [item["id"] for item in resources["locations"]]
    occupancies, exposures, compatibility = [], [], []
    for index in range(1, ORDER_COUNT + 1):
        order_id, cargo_id = uid(f"order:{index}"), uid(f"cargo:{index}")
        source_index = (index - 1) % 2
        order = copy_with(
            base["snapshot"]["orders"][source_index],
            id=order_id,
            external_ref=f"CC10-O{index:02d}",
            cargo_ids=[cargo_id],
        )
        order["pickup_window"] = {"earliest_s": 100, "latest_s": 3600}
        order["delivery_window"] = {"earliest_s": 0, "latest_s": 7200}
        item = copy_with(
            base["snapshot"]["cargo"][source_index], id=cargo_id, order_id=order_id, batch_ref=f"cc10-batch-{index:02d}"
        )
        orders.append(order)
        cargo.append(item)

        previous = None
        task_ids = {}
        assigned = [
            ("receive", 25, ("dock", "worker")),
            ("sort", 30, ("worker", "equipment")),
            ("load", 25, ("dock", "worker")),
        ]
        for step, duration, kinds in assigned:
            task_id = uid(f"task:{index}:{step}")
            task_ids[step] = task_id
            requirements = []
            for kind in kinds:
                pool = {"dock": dock_ids, "worker": worker_ids, "equipment": equipment_ids}[kind]
                offset = 2 if step == "load" else (1 if step == "sort" else 0)
                requirements.append(
                    {"resource_kind": kind, "eligible_ids": [pool[(index - 1 + offset) % len(pool)]], "units": 1}
                )
            tasks.append(
                {
                    "id": task_id,
                    "status": "pending",
                    "created_at": "2026-01-01T00:00:00Z",
                    "updated_at": "2026-01-01T00:00:00Z",
                    "row_version": 0,
                    "schema_version": "2.0.0",
                    "created_by": order["created_by"],
                    "order_id": order_id,
                    "warehouse_id": warehouse_id,
                    "kind": step,
                    "duration_s": duration,
                    "window": {"earliest_s": 0, "latest_s": 3600},
                    "predecessor_ids": [previous] if previous else [],
                    "requirements": requirements,
                    "setup_class": step,
                    "required_skills": [],
                }
            )
            previous = task_id

        batch = item["batch_ref"]
        occupancies.append(
            {
                "occupancy_id": uid(f"occupancy:{index}"),
                "batch_id": batch,
                "location_id": location_ids[(index - 1) % len(location_ids)],
                "capacity_use": [{"unit": "volume_cm3", "amount": item["volume_cm3"]}],
                "origin": "planned_inbound",
                "inbound_operation_id": task_ids["receive"],
                "outbound_operation_id": task_ids["load"],
                "declared_start_s": None,
            }
        )
        exposures.append(
            {
                "limit_id": uid(f"exposure:{index}"),
                "batch_id": batch,
                "max_exposure_s": 86400,
                "scopes": ["in_warehouse"],
                "rule_version": "cc10-1",
                "source": "synthetic",
            }
        )
        compatibility.append(
            {
                "batch_id": batch,
                "warehouse_id": warehouse_id,
                "temperature_zone": "chilled",
                "min_temperature_decic": 0,
                "max_temperature_decic": 80,
                "compatibility_class": None,
            }
        )

    snapshot["orders"] = orders
    snapshot["cargo"] = cargo
    raw["warehouse_tasks"] = tasks
    snapshot["scope"]["order_ids"] = [o["id"] for o in orders]
    snapshot["id"] = uid("snapshot")
    revisions = []
    for kind, items in (
        ("order", orders),
        ("cargo", cargo),
        ("vehicle", vehicles),
        ("driver", drivers),
        ("warehouse", resources["warehouses"]),
        ("zone", resources["zones"]),
        ("location", resources["locations"]),
        ("dock", resources["docks"]),
        ("worker", resources["workers"]),
        ("equipment", resources["equipment"]),
    ):
        revisions.extend(revision(kind, entity["id"]) for entity in items)
    snapshot["revisions"] = revisions

    cold = raw["coldchain_fields"]
    cold["rule_version"] = "cc10-1"
    cold["zones"][0]["capacities"] = [{"unit": "volume_cm3", "amount": 1000000}]
    cold["storage_locations"] = [
        {
            "location_id": loc["id"],
            "warehouse_id": warehouse_id,
            "zone_id": resources["zones"][0]["id"],
            "version": 1,
            "capacities": [{"unit": "volume_cm3", "amount": 100000}],
            "available_windows": [],
            "capacity_periods": [
                {"start_s": 0, "end_s": 86400, "capacities": [{"unit": "volume_cm3", "amount": 100000}]}
            ],
        }
        for loc in resources["locations"]
    ]
    cold["occupancies"] = occupancies
    cold["exposure_limits"] = exposures
    cold["batch_compatibility"] = compatibility

    # Parse each nested DTO independently, then use the canonical domain factory.
    # Passing the old hash through PlanningSnapshotDTO would be rejected by design.
    typed = PlanningSnapshot.create(
        id=UUID(snapshot["id"]),
        scope=PlanningScopeDTO.model_validate(snapshot["scope"]).to_domain(),
        orders=tuple(OrderDTO.model_validate(o).to_domain() for o in orders),
        cargo=tuple(CargoDTO.model_validate(c).to_domain() for c in cargo),
        vehicles=tuple(VehicleDTO.model_validate(v).to_domain() for v in vehicles),
        drivers=tuple(DriverDTO.model_validate(d).to_domain() for d in drivers),
        resources=ResourceBundleDTO.model_validate(resources).to_domain(),
        inventory=(),
        revisions=tuple(ResourceRevisionDTO.model_validate(r).to_domain() for r in revisions),
        matrices=tuple(TravelMatrixDTO.model_validate(m).to_domain() for m in snapshot["matrices"]),
    )
    raw["snapshot"] = snapshot_dto(typed).model_dump(mode="json")
    # Validate the complete source contract before emitting a single byte.
    ColdChainSnapshotDTO.model_validate(cold)
    return ScenarioImport.model_validate(raw).model_dump(mode="json")


def main() -> None:
    result = build()
    # newline="\n" keeps the emitted bytes identical on every platform; the
    # manifest digest is computed over raw file bytes.
    OUTPUT.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    print(
        f"Generated {OUTPUT.relative_to(ROOT)}: {len(result['snapshot']['orders'])} orders, "
        f"{len(result['warehouse_tasks'])} warehouse tasks"
    )


if __name__ == "__main__":
    main()
