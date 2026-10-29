"""S2: deterministic ten-order warehouse chain through the real solvers."""

from __future__ import annotations

import json
from collections import Counter
from uuid import UUID, uuid4

import pytest
from scripts.generate_coldchain_chain_10 import OUTPUT, build

from logistics_backend.application.integration import solve_imported
from logistics_backend.application.scenario_import import prepare_scenario
from logistics_backend.worker import Worker
from logistics_contracts.integration import IntegrationRun, ScenarioImport


def test_fixture_is_reproducible_and_contract_valid():
    expected = json.dumps(build(), ensure_ascii=False, indent=2) + "\n"
    assert OUTPUT.read_text(encoding="utf-8") == expected
    command = ScenarioImport.model_validate_json(expected)
    assert command.source_kind == "synthetic"
    assert len(command.snapshot.orders) == 10
    assert len(command.warehouse_tasks) == 30
    assert len(command.coldchain_fields.occupancies) == 10
    assert command.snapshot.to_domain().hash == command.snapshot.hash
    checked = prepare_scenario(command)
    assert checked["status"] == "checked", checked
    assert checked["source_verified"] is False
    assert checked["backfilled_fields"] == ["snapshot.coldchain"]


def test_every_order_has_complete_precedence_and_storage_evidence():
    command = ScenarioImport.model_validate_json(OUTPUT.read_text(encoding="utf-8"))
    resources = command.snapshot.resources
    assert (len(resources.docks), len(resources.workers), len(resources.equipment), len(resources.locations)) == (
        6,
        4,
        2,
        6,
    )
    by_order = {}
    for task in command.warehouse_tasks:
        by_order.setdefault(task.order_id, {})[task.kind.value] = task
    assert set(by_order) == set(command.snapshot.scope.order_ids)
    for tasks in by_order.values():
        assert set(tasks) == {"receive", "sort", "load"}
        assert tasks["receive"].predecessor_ids == ()
        assert tasks["sort"].predecessor_ids == (tasks["receive"].id,)
        assert tasks["load"].predecessor_ids == (tasks["sort"].id,)

    cold = command.coldchain_fields
    inbound = {tasks["receive"].id for tasks in by_order.values()}
    outbound = {tasks["load"].id for tasks in by_order.values()}
    assert {occupancy.inbound_operation_id for occupancy in cold.occupancies} == inbound
    assert {occupancy.outbound_operation_id for occupancy in cold.occupancies} == outbound
    batches = {item.batch_ref for item in command.snapshot.cargo}
    assert {item.batch_id for item in cold.occupancies} == batches
    assert {item.batch_id for item in cold.batch_compatibility} == batches
    assert {item.batch_id for item in cold.exposure_limits} == batches
    location_load = Counter(item.location_id for item in cold.occupancies)
    assert len(location_load) == 6 and max(location_load.values()) == 2


def test_ten_order_pipeline_is_checked_by_real_solvers():
    command = ScenarioImport.model_validate_json(OUTPUT.read_text(encoding="utf-8"))
    result = solve_imported(command, IntegrationRun(scenario_id=UUID(int=1), budget_ms=4000), UUID(int=2))
    assert result["status"] == "checked", result.get("reason")
    assert result["warehouse_solution"]["status"] == "optimal"
    assert len(result["warehouse_solution"]["assignments"]) >= 30
    assert result["warehouse_solution"]["validation"]["valid"] is True
    assert result["transport_solution"]["status"] in ("optimal", "feasible")
    assert result["joint_validation"]["valid"] is True
    assert len(result["observations"]["handoffs"]) == 30
    assert all(item["pickup_start_s"] >= item["warehouse_ready_s"] for item in result["observations"]["handoffs"])


@pytest.mark.requires_postgres
def test_http_import_and_async_worker_on_isolated_database(warehouse_api):
    """Full API acceptance; requires only the explicitly selected TEST_DATABASE_URL."""
    client, app, _, _ = warehouse_api
    scenario = json.loads(OUTPUT.read_text(encoding="utf-8"))
    imported = client.post("/api/v1/integration/scenarios", json=scenario, headers={})
    assert imported.status_code == 200, imported.text
    body = imported.json()
    assert body["status"] == "checked", body

    accepted = client.post(
        "/api/v1/integration/runs?wait=false",
        json={"scenario_id": body["scenario_id"], "budget_ms": 12000},
        headers={"Idempotency-Key": str(uuid4())},
    )
    assert accepted.status_code == 200, accepted.text
    receipt = accepted.json()
    assert receipt["status"] == "queued"
    outcome = Worker(app.state.jobs.repository, app.state.jobs.registry).run_once()
    assert str(outcome.job_id) == receipt["job_id"]

    response = client.get(f"/api/v1/jobs/{receipt['job_id']}/result")
    assert response.status_code == 200, response.text
    result = response.json()["value"]
    assert result["status"] == "checked", result.get("reason")
    assert result["warehouse_solution"]["status"] == "optimal"
    assert len(result["warehouse_solution"]["assignments"]) >= 30
    assert result["joint_validation"]["valid"] is True
