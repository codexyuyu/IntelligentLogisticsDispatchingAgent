"""Warehouse HTTP -> PostgreSQL queue -> spawned CP-SAT worker -> hashed result.

Run only with a migrated isolated TEST_DATABASE_URL. No solver or database fakes.
"""
from __future__ import annotations

import hashlib
import json
import socket
import threading
import time
import urllib.error
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path
from uuid import UUID, uuid4

import pytest
import uvicorn

from logistics_backend.bootstrap import Settings, create_app
from logistics_backend.cli.seed import seed
from logistics_backend.worker import Worker
from logistics_contracts.warehouse import WarehouseJobContent, WarehouseSolutionDTO
from logistics_domain.planning import content_hash

pytestmark = pytest.mark.requires_postgres
ROOT = Path(__file__).resolve().parents[2]
TOKEN = "warehouse-test-token"


class HttpResponse:
    def __init__(self, status_code, content):
        self.status_code = status_code
        self.text = content.decode("utf-8")

    def json(self):
        return json.loads(self.text)


class HttpClient:
    """Real loopback HTTP; no optional TestClient dependency or ASGI test double."""
    def __init__(self, port):
        self.base = f"http://127.0.0.1:{port}"

    def get(self, path):
        return self._request(path)

    def post(self, path, json, headers):
        return self._request(path, json, headers)

    def _request(self, path, body=None, headers=None):
        request = urllib.request.Request(self.base + path,
            data=json.dumps(body).encode() if body is not None else None,
            headers={"Authorization": f"Bearer {TOKEN}", "Content-Type": "application/json",
                     **(headers or {})})
        try:
            with urllib.request.urlopen(request, timeout=15) as response:
                return HttpResponse(response.status, response.read())
        except urllib.error.HTTPError as error:
            with error:
                return HttpResponse(error.code, error.read())


@pytest.fixture
def warehouse_api(database_url, tmp_path, monkeypatch):
    seed("tiny_master", database_url)
    scenario = json.loads((ROOT / "data/scenarios/tiny_master.json").read_text())
    # Relative result artifacts stay in the test directory, including in spawned workers.
    monkeypatch.chdir(tmp_path)
    settings = Settings(mode="test", database_url=database_url,
        scope_id=scenario["scope_id"], credentials=({
            "actor_id": str(uuid4()), "role": "operator",
            "token_sha256": hashlib.sha256(TOKEN.encode()).hexdigest()},))
    app = create_app(settings)
    sock = socket.socket()
    sock.bind(("127.0.0.1", 0))
    port = sock.getsockname()[1]
    server = uvicorn.Server(uvicorn.Config(app, log_level="error"))
    thread = threading.Thread(target=server.run, kwargs={"sockets": [sock]}, daemon=True)
    thread.start()
    try:
        deadline = time.monotonic() + 10
        while not server.started and thread.is_alive() and time.monotonic() < deadline:
            time.sleep(0.01)
        assert server.started, "warehouse test HTTP server did not start"
        yield HttpClient(port), app, scenario, tmp_path
    finally:
        server.should_exit = True
        thread.join(timeout=10)
        sock.close()
        assert not thread.is_alive(), "warehouse test HTTP server did not stop"


def request_body(scenario, with_setup=False):
    dock = scenario["docks"][0]
    worker = scenario["workers"][0]
    equipment = scenario["equipment"][0]
    first, second = str(uuid4()), str(uuid4())
    now = datetime.now(timezone.utc).replace(microsecond=0)
    def task(task_id, duration, predecessors):
        return {"id": task_id, "status": "pending", "row_version": 0,
            "schema_version": "2.0.0", "created_at": "2026-01-01T00:00:00Z",
            "updated_at": "2026-01-01T00:00:00Z", "created_by": scenario["created_by"],
            "order_id": None, "warehouse_id": dock["warehouse_id"],
            "kind": dock["supported_operations"][0], "duration_s": duration,
            "window": {"earliest_s": 0, "latest_s": 100},
            "predecessor_ids": predecessors, "requirements": [
                {"resource_kind": "dock", "eligible_ids": [dock["id"]], "units": 1},
                {"resource_kind": "worker", "eligible_ids": [worker["id"]], "units": 1},
                {"resource_kind": "equipment", "eligible_ids": [equipment["id"]], "units": 1}],
            "setup_class": "receive" if not predecessors else "load"}
    body = {"schema_version": "2.0.0", "scope": {
        "order_ids": [], "warehouse_ids": [dock["warehouse_id"]], "vehicle_ids": [],
        "epoch_utc": "2026-01-01T00:00:00Z", "horizon_s": 3600},
        "tasks": [task(first, 10, []), task(second, 15, [first])],
        "budget": {"wall_time_ms": 1000,
            "deadline_utc": (now + timedelta(seconds=45)).isoformat(),
            "max_candidates": 1, "seed": 0},
        "objective_policy": {"version": "1.0.0", "optional_unserved_penalty_cents": 0,
            "soft_late_cents_per_s": 0, "makespan_cents_per_s": 0,
            "disturbance_weights": {"assignment_change": 0, "time_shift": 0,
                "order_change": 0, "membership_change": 0}}}
    if with_setup:
        body["setup_policy"] = {"version": "1.0.0", "transitions": [{
            "resource_id": dock["id"], "from_class": "receive", "to_class": "load",
            "duration_s": 7, "cost_cents": 250}], "initial_states": [{
            "resource_id": dock["id"], "setup_class": "receive"}]}
    return body


def run_job(client, app, body):
    response = client.post("/api/v1/optimizations/warehouse", json=body,
        headers={"Idempotency-Key": str(uuid4())})
    assert response.status_code == 202, response.text
    job_id = response.json()["job_id"]
    pending = client.get(f"/api/v1/jobs/{job_id}/result")
    assert pending.status_code == 409, pending.text
    outcome = Worker(app.state.jobs.repository, app.state.jobs.registry).run_once()
    assert str(outcome.job_id) == job_id
    job = client.get(f"/api/v1/jobs/{job_id}").json()
    assert job["status"] == "completed", job
    response = client.get(f"/api/v1/jobs/{job_id}/result")
    assert response.status_code == 200, response.text
    result = response.json()
    assert result["kind"] == "warehouse"
    artifact = Path("artifacts/results") / f'{job["result_ref"]["result_id"]}.json'
    assert hashlib.sha256(artifact.read_bytes()).hexdigest() == job["result_ref"]["hash"]
    assert json.loads(artifact.read_bytes()) == result["value"]
    return job, result["value"], artifact


def test_real_warehouse_job_has_independent_validation_and_hash(warehouse_api):
    client, app, scenario, directory = warehouse_api
    body = request_body(scenario)
    job, result, artifact = run_job(client, app, body)
    assert result["status"] in ("optimal", "feasible")
    assert result["engine_metadata"]["name"] == "ortools_cp_sat"
    assert len(result["assignments"]) == 6
    by_task = {}
    for assignment in result["assignments"]:
        by_task.setdefault(assignment["task_id"], []).append(assignment)
    first, second = [by_task[t["id"]] for t in body["tasks"]]
    assert (first[0]["start_s"], first[0]["end_s"], second[0]["start_s"], second[0]["end_s"]) == (0, 10, 10, 25)
    assert {a["resource_id"] for a in first} == {
        body["tasks"][0]["requirements"][0]["eligible_ids"][0],
        body["tasks"][0]["requirements"][1]["eligible_ids"][0],
        body["tasks"][0]["requirements"][2]["eligible_ids"][0]}
    assert result["validation"]["valid"] is True
    assert not result["validation"]["violations"]
    domain = WarehouseSolutionDTO.model_validate(result).to_domain()
    assert result["solver_evidence"][0]["assignment_hash"] == content_hash(domain.assignments)
    stored = app.state.jobs.repository.load_job_request(UUID(job["job_id"]), UUID(scenario["scope_id"]))
    problem = WarehouseJobContent.model_validate_json(stored).problem.to_domain()
    assert result["validation"]["snapshot_hash"] == problem.snapshot.hash
    assert result["solver_evidence"][0]["input_hash"] == content_hash(problem)
    artifact.write_bytes(artifact.read_bytes() + b" ")
    tampered = client.get(f'/api/v1/jobs/{job["job_id"]}/result')
    assert tampered.status_code == 422, tampered.text
    assert tampered.json()["code"] == "unverified_solver_result"


def test_unknown_resource_is_not_reported_as_valid(warehouse_api):
    client, app, scenario, _ = warehouse_api
    body = request_body(scenario)
    ghost = str(uuid4())
    for task in body["tasks"]:
        task["requirements"][0]["eligible_ids"] = [ghost]
    _, result, _ = run_job(client, app, body)
    # An eligible id that is not in the snapshot is not a valid resource candidate.
    assert result["status"] == "infeasible"
    assert result["assignments"] == []
    assert result["diagnostics"]


def test_infeasible_window_does_not_return_assignments_or_valid(warehouse_api):
    client, app, scenario, _ = warehouse_api
    body = request_body(scenario)
    body["tasks"][1]["window"]["latest_s"] = 0
    _, result, _ = run_job(client, app, body)
    assert result["status"] == "infeasible"
    assert result["assignments"] == []
    assert result["validation"] is None
    assert result["diagnostics"]


def test_task_outside_snapshot_is_rejected_before_queue(warehouse_api):
    client, _, scenario, _ = warehouse_api
    body = request_body(scenario)
    body["tasks"][0]["warehouse_id"] = str(uuid4())
    response = client.post("/api/v1/optimizations/warehouse", json=body,
        headers={"Idempotency-Key": str(uuid4())})
    assert response.status_code == 422, response.text
    assert "outside the snapshot" in response.json()["message"]


def test_warehouse_setup_gap_between_changeover_classes(warehouse_api):
    client, app, scenario, directory = warehouse_api
    body = request_body(scenario, with_setup=True)
    _, result, _ = run_job(client, app, body)
    by_task = {}
    for assignment in result["assignments"]:
        by_task.setdefault(assignment["task_id"], []).append(assignment)
    first, second = [by_task[t["id"]] for t in body["tasks"]]
    assert (first[0]["start_s"], first[0]["end_s"]) == (0, 10)
    assert second[0]["start_s"] == 17, "setup must delay the next task"
    assert second[0]["end_s"] == 32
    assert result["setup_operations"], "setup operation must be explicit"
    setup = result["setup_operations"][0]
    assert setup["from_class"] == "receive" and setup["to_class"] == "load"
    assert setup["start_s"] == 10 and setup["end_s"] == 17
    assert setup["cost_cents"] == 250
    assert result["objective"]["business_cost_cents"] == 450
    assert result["validation"]["valid"] is True
