import json
from pathlib import Path
from fastapi.testclient import TestClient

from app.main import app
from app.application.runtime import runtime
from app.contracts.common import SolveMetadata, ValidationReport
from app.contracts.http import JobAccepted
from app.contracts.planning import CandidatePlan, RoutingResult, WarehouseScheduleResult

ROOT = Path(__file__).resolve().parents[2]
SCENARIO = ROOT / "data/scenarios/two_warehouses_20_orders.json"
client = TestClient(app)


def reset_runtime():
    runtime.snapshots.clear()
    runtime.jobs.clear()
    runtime.plans.clear()
    runtime.idempotency.clear()


def test_scenario_import_is_real():
    reset_runtime()
    raw = json.loads(SCENARIO.read_text(encoding="utf-8"))
    response = client.post(
        "/api/v1/scenarios/import",
        headers={"Idempotency-Key": "scenario-int"},
        json={"scenario_id": "scn_demo", "snapshot": raw},
    )
    assert response.status_code == 201
    assert response.json()["validation"]["status"] == "passed"


def test_planning_job_is_wired_to_build_candidate_plan(monkeypatch):
    reset_runtime()
    raw = json.loads(SCENARIO.read_text(encoding="utf-8"))
    imported = client.post(
        "/api/v1/scenarios/import",
        headers={"Idempotency-Key": "scenario-int-2"},
        json={"scenario_id": "scn_demo", "snapshot": raw},
    )
    assert imported.status_code == 201

    empty_meta = SolveMetadata(
        status="feasible", raw_status="TEST", engine="test", engine_version="0",
        has_solution=True, proof_scope="test", solve_ms=0,
    )
    empty_validation = ValidationReport(
        status="passed", validator_version="test", checked_rule_ids=("test.rule",), violations=()
    )
    routing = RoutingResult(
        snapshot_id="snap_initial", snapshot_version=1, metadata=empty_meta,
        routes=(), warehouse_arrivals=(), unserved_orders=()
    )
    warehouse = WarehouseScheduleResult(
        snapshot_id="snap_initial", snapshot_version=1, metadata=empty_meta,
        operations=(), warehouse_handoffs=()
    )
    plan = CandidatePlan(
        plan_id="plan_test_1", snapshot_id="snap_initial", snapshot_version=1, version=1,
        plan_hash="0" * 64, routing=routing, warehouse=warehouse, validation=empty_validation
    )
    monkeypatch.setattr("app.application.http_services._build_candidate_plan", lambda snapshot, body: plan)

    response = client.post(
        "/api/v1/planning-jobs",
        headers={"Idempotency-Key": "planning-int"},
        json={
            "snapshot_id": "snap_initial",
            "expected_snapshot_version": 1,
            "order_ids": ["ord_001"],
            "budget_ms": 10000,
            "max_coordination_rounds": 1,
        },
    )
    assert response.status_code == 202
    assert response.json()["status"] == "succeeded"
    job_id = response.json()["job_id"]

    job = client.get(f"/api/v1/jobs/{job_id}")
    assert job.status_code == 200
    assert job.json()["status"] == "succeeded"
    assert job.json()["plan_id"] == "plan_test_1"

    plan_response = client.get("/api/v1/plans/plan_test_1")
    assert plan_response.status_code == 200
    assert plan_response.json()["status"] == "validated"


def test_planning_job_missing_snapshot_returns_controlled_error():
    reset_runtime()
    response = client.post(
        "/api/v1/planning-jobs",
        headers={"Idempotency-Key": "missing-snapshot"},
        json={
            "snapshot_id": "snap_missing",
            "expected_snapshot_version": 1,
            "order_ids": ["ord_001"],
            "budget_ms": 10000,
            "max_coordination_rounds": 1,
        },
    )
    assert response.status_code == 404
    assert response.json()["code"] == "not_found"
