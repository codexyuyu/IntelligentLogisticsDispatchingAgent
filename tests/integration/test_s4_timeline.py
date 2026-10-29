"""S4 checked-plan replay; database case requires migrated isolated PostgreSQL."""

from __future__ import annotations

import copy
import json
from pathlib import Path
from uuid import UUID, uuid4

import pytest
from sqlalchemy import func, select

from logistics_backend.application.integration import solve_imported
from logistics_backend.application.timeline import TimelineValidationError, build_timeline, state_at_time
from logistics_backend.worker import Worker
from logistics_contracts.integration import IntegrationRun, ScenarioImport

ROOT = Path(__file__).resolve().parents[2]
SCENARIO_PATH = ROOT / "data/scenarios/coldchain_chain_10.json"


@pytest.fixture(scope="module")
def planned_run():
    scenario = ScenarioImport.model_validate(json.loads(SCENARIO_PATH.read_text(encoding="utf-8")))
    result = solve_imported(scenario, IntegrationRun(scenario_id=UUID(int=1), budget_ms=4000), UUID(int=1))
    assert result["status"] == "checked", result.get("reason")
    return scenario, result


def test_s4_planned_replay_is_reconciled_and_stable(planned_run):
    _, result = planned_run
    first = build_timeline(result, run_id=UUID(int=2))
    second = build_timeline(result, run_id=UUID(int=2))
    assert first == second
    assert first["source_kind"] == "planned_validated"
    assert first["event_count"] >= 40
    assert len(first["events"]) == first["event_count"]
    assert [event["sequence"] for event in first["events"]] == list(range(first["event_count"]))
    assert [event["time_s"] for event in first["events"]] == sorted(e["time_s"] for e in first["events"])
    assert first["reconciliation"]["passed"] is True
    assert len(first["reconciliation"]["checks"]) == 7
    assert all(first["reconciliation"]["checks"].values())
    assert first["reconciliation"]["scope_orders"] == (
        first["reconciliation"]["planned_delivery_orders"] + first["reconciliation"]["explicitly_unserved_orders"]
    )
    assert len(first["reconciliation"]["order_details"]) == 10
    assert set(e["id"] for e in first["events"]).isdisjoint(
        e["id"] for e in build_timeline(result, run_id=UUID(int=3))["events"]
    )


def test_s4_state_at_event_has_all_ten_collections(planned_run):
    _, result = planned_run
    timeline = build_timeline(result)
    beginning = state_at_time(timeline, result, 0)
    finished = state_at_time(timeline, result, max(e["time_s"] for e in timeline["events"]) + 1)
    keys = (
        "completed_order_ids",
        "completed_operation_ids",
        "active_operation_ids",
        "in_transit_vehicle_ids",
        "returned_vehicle_ids",
        "not_yet_departed_vehicle_ids",
        "onboard_pending_order_ids",
        "available_depot_vehicle_ids",
        "halted_vehicle_positions",
        "interrupted_operation_ids",
    )
    assert all(key in beginning and key in finished for key in keys)
    assert beginning["completed_order_ids"] == []
    assert len(finished["completed_order_ids"]) == 10
    assert len(finished["completed_operation_ids"]) == 30
    assert finished["in_transit_vehicle_ids"] == []
    assert finished["not_yet_departed_vehicle_ids"] == []
    assert finished["active_operation_ids"] == []


def test_s4_unchecked_or_inconsistent_replay_is_rejected(planned_run):
    _, result = planned_run
    unchecked = copy.deepcopy(result)
    unchecked["joint_validation"]["valid"] = False
    with pytest.raises(TimelineValidationError, match="unvalidated_plan_must_not_be_replayed"):
        build_timeline(unchecked)
    inconsistent = copy.deepcopy(result)
    nodes = {n["id"]: n for n in inconsistent["transport_problem"]["nodes"]}
    pickup = next(s for s in inconsistent["transport_solution"]["stops"] if nodes[s["node_id"]]["kind"] == "pickup")
    pickup["service_start_s"] = 0
    pickup["departure_s"] = 1
    with pytest.raises(TimelineValidationError, match=r"before_warehouse_operations_finished|departure_before"):
        build_timeline(inconsistent)


@pytest.mark.requires_postgres
def test_s4_timeline_persists_once_and_supports_state_at(warehouse_api):
    from logistics_backend.persistence.integration_models import integration_timeline_events

    client, app, _, _ = warehouse_api
    body = json.loads(SCENARIO_PATH.read_text(encoding="utf-8"))
    imported = client.post("/api/v1/integration/scenarios", json=body, headers={})
    assert imported.status_code == 200, imported.text
    run = client.post(
        "/api/v1/integration/runs?wait=false",
        json={"scenario_id": imported.json()["scenario_id"], "budget_ms": 12000},
        headers={"Idempotency-Key": str(uuid4())},
    )
    assert run.status_code == 200, run.text
    run_id = run.json()["run_id"]
    Worker(app.state.jobs.repository, app.state.jobs.registry).run_once()
    first = client.get(f"/api/v1/integration/runs/{run_id}/timeline")
    assert first.status_code == 200, first.text
    assert first.json()["event_count"] >= 40
    assert first.json()["reconciliation"]["passed"] is True
    again = client.get(f"/api/v1/integration/runs/{run_id}/timeline")
    assert again.status_code == 200, again.text
    assert again.json() == first.json()
    with app.state.engine.connect() as connection:
        count = connection.execute(
            select(func.count())
            .select_from(integration_timeline_events)
            .where(integration_timeline_events.c.run_id == UUID(run_id))
        ).scalar_one()
    assert count == first.json()["event_count"]
    event_at = client.get(f"/api/v1/integration/runs/{run_id}/state-at?time_s=86400")
    assert event_at.status_code == 200, event_at.text
    assert len(event_at.json()["completed_operation_ids"]) == 30
    assert "halted_vehicle_positions" in event_at.json()
