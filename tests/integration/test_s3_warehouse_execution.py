"""S3: persisted task chain and inventory debits/credits from explicit completion.

The HTTP test needs an isolated, migrated PostgreSQL TEST_DATABASE_URL on port 5434.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from unittest.mock import Mock
from uuid import UUID, uuid4

import pytest
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import dialect

from logistics_backend.application.integration import solve_imported
from logistics_backend.application.warehouse_execution import movement_from_checked_run
from logistics_backend.persistence.resource_models import docks, locations
from logistics_backend.persistence.scenario_projection import _insert_checked, resolve_storage_location
from logistics_backend.worker import Worker
from logistics_contracts.integration import IntegrationRun, ScenarioImport

ROOT = Path(__file__).resolve().parents[2]
SCENARIO = ROOT / "data/scenarios/coldchain_chain_10.json"


def _scenario():
    return ScenarioImport.model_validate(json.loads(SCENARIO.read_text(encoding="utf-8")))


def _select_result(row):
    result = Mock()
    result.mappings.return_value.first.return_value = row
    return result


def test_s3_collision_uses_business_key_and_not_only_id():
    scope = UUID(int=10)
    declared = UUID(int=11)
    canonical = UUID(int=12)
    connection = Mock()
    connection.execute.side_effect = [
        Mock(),
        _select_result(None),
        _select_result({"id": canonical, "scope_id": scope}),
    ]
    row = _insert_checked(
        connection,
        locations,
        {"id": declared, "scope_id": scope, "zone_id": UUID(int=13), "code": "L1"},
        scope,
        ("zone_id", "code"),
    )
    assert row["id"] == canonical
    sql = str(connection.execute.call_args_list[0].args[0].compile(dialect=dialect()))
    assert "ON CONFLICT DO NOTHING" in sql
    assert "ON CONFLICT (id)" not in sql


def test_s3_storage_alias_follows_zone_and_location_natural_keys():
    scenario = _scenario()
    loc = next(v for v in scenario.snapshot.resources.locations if v.code == "L1")
    zone = next(v for v in scenario.snapshot.resources.zones if v.id == loc.zone_id)
    wh = next(v for v in scenario.snapshot.resources.warehouses if v.id == zone.warehouse_id)
    canonical = UUID(int=42)
    scope = UUID(int=10)
    connection = Mock()
    connection.execute.side_effect = [
        _select_result({"id": wh.id, "scope_id": scope, "code": wh.code}),
        _select_result({"id": zone.id, "scope_id": scope, "warehouse_id": wh.id, "code": zone.code}),
        _select_result(None),
        _select_result({"id": canonical, "scope_id": scope, "zone_id": zone.id, "code": loc.code}),
    ]
    assert resolve_storage_location(connection, scope, scenario.snapshot, loc.id) == canonical


def test_s3_manifest_hashes_are_file_sha256():
    manifest = json.loads((ROOT / "data/scenarios/manifest.json").read_text(encoding="utf-8"))
    assert {entry["name"] for entry in manifest["scenarios"]} == {"tiny_master", "coldchain_chain_10"}
    for entry in manifest["scenarios"]:
        actual = hashlib.sha256((ROOT / "data/scenarios" / entry["path"]).read_bytes()).hexdigest()
        assert entry["sha256"] == actual


def test_s3_planned_allocation_is_not_already_a_stock_movement():
    scenario = _scenario()
    result = solve_imported(scenario, IntegrationRun(scenario_id=UUID(int=1), budget_ms=4000), UUID(int=1))
    assert result["status"] == "checked"
    by_kind = {
        kind: next(task for task in scenario.warehouse_tasks if task.kind.value == kind)
        for kind in ("receive", "sort", "load")
    }
    incoming = movement_from_checked_run(result, scenario, by_kind["receive"].id)
    outgoing = movement_from_checked_run(result, scenario, by_kind["load"].id)
    assert incoming is not None and outgoing is not None
    assert incoming[:2] == outgoing[:2]
    assert incoming[2] == 1 and outgoing[2] == -1
    assert movement_from_checked_run(result, scenario, by_kind["sort"].id) is None


@pytest.mark.requires_postgres
def test_s3_http_task_chain_creates_append_only_ledger_on_completion(warehouse_api):
    client, app, _, _ = warehouse_api
    scenario = _scenario()
    snapshot = scenario.snapshot
    warehouse_id = snapshot.scope.warehouse_ids[0]
    order_id = snapshot.orders[0].id
    cargo_id = snapshot.cargo[0].id

    imported = client.post("/api/v1/integration/scenarios", json=scenario.model_dump(mode="json"), headers={})
    assert imported.status_code == 200, imported.text
    assert imported.json()["status"] == "checked"
    run = client.post(
        "/api/v1/integration/runs?wait=false",
        json={"scenario_id": imported.json()["scenario_id"], "budget_ms": 12000},
        headers={"Idempotency-Key": str(uuid4())},
    )
    assert run.status_code == 200, run.text
    Worker(app.state.jobs.repository, app.state.jobs.registry).run_once()
    run_id = run.json()["run_id"]
    result = client.get(f"/api/v1/integration/runs/{run_id}")
    assert result.status_code == 200 and result.json()["status"] == "checked", result.text

    listed = client.get(f"/api/v1/warehouses/{warehouse_id}/tasks?limit=100")
    assert listed.status_code == 200, listed.text
    assert listed.json()["total"] >= 30
    scoped = client.get(f"/api/v1/warehouses/{warehouse_id}/tasks?order_id={order_id}")
    assert scoped.status_code == 200, scoped.text
    assert scoped.json()["total"] == 3
    tasks = {task["kind"]: task for task in scoped.json()["items"]}

    # tiny_master is seeded first. L1/D1 share natural keys with the 10-order
    # scenario but have different UUIDs: projection must reuse existing masters.
    source_location = next(v for v in snapshot.resources.locations if v.code == "L1")
    source_dock = next(v for v in snapshot.resources.docks if v.code == "D1")
    with app.state.engine.connect() as connection:
        actual_location = connection.execute(
            select(locations.c.id).where(locations.c.zone_id == source_location.zone_id, locations.c.code == "L1")
        ).scalar_one()
        actual_dock = connection.execute(
            select(docks.c.id).where(docks.c.warehouse_id == warehouse_id, docks.c.code == "D1")
        ).scalar_one()
    assert actual_location != source_location.id
    assert actual_dock != source_dock.id
    dock_requirements = [
        req for task in tasks.values() for req in task["requirements"] if req["resource_kind"] == "dock"
    ]
    assert any(str(actual_dock) in req["eligible_ids"] for req in dock_requirements)
    assert all(str(source_dock.id) not in req["eligible_ids"] for req in dock_requirements)

    for kind in ("receive", "sort", "load"):
        task = tasks[kind]
        for next_status in ("ready", "running", "completed"):
            if task["status"] == "completed":
                break  # Safe on repeated real-database test runs.
            if task["status"] == next_status:
                continue
            if next_status == "ready" and task["status"] != "pending":
                continue
            if next_status == "running" and task["status"] != "ready":
                continue
            if next_status == "completed" and task["status"] != "running":
                continue
            response = client.post(
                f"/api/v1/warehouses/{warehouse_id}/tasks/{task['id']}/transitions",
                json={"run_id": run_id, "target_status": next_status, "expected_row_version": task["row_version"]},
                headers={},
            )
            assert response.status_code == 200, response.text
            task = response.json()
        assert task["status"] == "completed"

    inventory = client.get(f"/api/v1/inventory?cargo_id={cargo_id}")
    assert inventory.status_code == 200, inventory.text
    ledger = inventory.json()
    assert ledger["total_entries"] == 2, ledger
    assert {entry["quantity_delta"] for entry in ledger["items"]} == {1, -1}
    assert ledger["positions"][0]["quantity_units"] == 0
    assert all(entry["source_location_id"] for entry in ledger["items"])
    assert all(entry["location_id"] == ledger["positions"][0]["location_id"] for entry in ledger["items"])

    duplicate = client.post(
        f"/api/v1/warehouses/{warehouse_id}/tasks/{tasks['load']['id']}/transitions",
        json={"run_id": run_id, "target_status": "completed", "expected_row_version": 2},
        headers={},
    )
    assert duplicate.status_code == 409, duplicate.text
    assert client.get(f"/api/v1/inventory?cargo_id={cargo_id}").json()["total_entries"] == 2
