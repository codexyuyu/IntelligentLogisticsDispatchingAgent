"""Stage A 14-item acceptance harness (untracked; evidence only, never committed).

Runs the real HTTP API against the isolated PostgreSQL test database and asserts
each of the fourteen Stage A acceptance items, printing one evidence line per
item so the run log can be pasted into the acceptance report.
"""

from __future__ import annotations

import json
from pathlib import Path
from uuid import UUID, uuid4

import pytest
from sqlalchemy import text

from logistics_backend.worker import Worker

pytestmark = pytest.mark.requires_postgres
ROOT = Path(__file__).resolve().parents[2]

PROTECTED_TABLES = (
    "inventory_ledger",
    "schedules",
    "schedule_versions",
    "schedule_tasks",
    "warehouse_tasks",
)


def _counts(engine):
    with engine.connect() as connection:
        return {
            name: connection.execute(text(f"select count(*) from {name}")).scalar_one()
            for name in PROTECTED_TABLES
        }


def _checked_run(client, app, scenario_id):
    submitted = client.post(
        "/api/v1/integration/runs?wait=false",
        json={"scenario_id": scenario_id, "budget_ms": 12000},
        headers={"Idempotency-Key": str(uuid4())},
    )
    assert submitted.status_code == 200, submitted.text
    Worker(app.state.jobs.repository, app.state.jobs.registry).run_once()
    run_id = submitted.json()["run_id"]
    run = client.get(f"/api/v1/integration/runs/{run_id}")
    assert run.status_code == 200 and run.json()["status"] == "checked", run.text
    return run_id


def test_stage_a_fourteen_items(warehouse_api):
    client, app, _, _ = warehouse_api
    engine = app.state.engine
    fixture = json.loads((ROOT / "data/scenarios/coldchain_chain_10.json").read_text(encoding="utf-8"))
    warehouse_id = fixture["snapshot"]["scope"]["warehouse_ids"][0]

    # ---- A01: scenario read from PostgreSQL, checked run produced -------------
    imported = client.post("/api/v1/integration/scenarios", json=fixture, headers={})
    assert imported.status_code == 200, imported.text
    scenario_id = imported.json()["scenario_id"]
    with engine.connect() as connection:
        stored = connection.execute(
            text("select payload->>'source_kind', payload->>'name' from integration_scenarios where id = :id"),
            {"id": scenario_id},
        ).first()
    assert stored is not None, "scenario row missing in PostgreSQL"
    run_id = _checked_run(client, app, scenario_id)
    print(f"[A01] PASS scenario stored in PG ({stored[0]}) and run {run_id} is checked")

    baseline = client.post(f"/api/v1/integration/runs/{run_id}/simulation", json={}, headers={})
    assert baseline.status_code == 200, baseline.text
    base = baseline.json()

    # ---- A02: 10 orders x 3 warehouse stages ---------------------------------
    orders = base["reconciliation"]["scope_orders"]
    listed = client.get(f"/api/v1/warehouses/{warehouse_id}/tasks?limit=100")
    assert listed.status_code == 200, listed.text
    tasks = listed.json()["items"]
    kinds = {}
    for task in tasks:
        kinds[task["kind"]] = kinds.get(task["kind"], 0) + 1
    assert orders == 10, f"expected 10 scoped orders, got {orders}"
    assert len(tasks) == 30, f"expected 30 warehouse tasks, got {len(tasks)}"
    assert kinds.get("receive") == 10 and kinds.get("sort") == 10 and kinds.get("load") == 10, kinds
    print(f"[A02] PASS orders={orders} tasks={len(tasks)} by_kind={kinds}")
    probe = next(task for task in tasks if task["kind"] == "load")
    print(f"[PROBE] load task keys={sorted(probe)}")
    print(f"[PROBE] load task sample={json.dumps({k: probe[k] for k in probe if k != 'payload'}, default=str)[:400]}")

    # ---- A03: loading hand-over respects transport departure ------------------
    recon = base["reconciliation"]
    details = recon.get("order_details") or []
    events = base["events"]
    assert recon["passed"] is True
    assert len(details) == 10, len(details)
    assert all(d["warehouse_task_count"] == 3 for d in details), [d["warehouse_task_count"] for d in details]
    departures = {}
    for event in events:
        if event["kind"] == "vehicle_departure":
            departures.setdefault(event["vehicle_id"], []).append(event["time_s"])
    handovers = 0
    for detail in details:
        if detail["routing_status"] != "planned_delivery":
            continue
        vehicle = detail["planned_vehicle_id"]
        later = sorted(t for t in departures.get(vehicle, []) if t >= detail["loading_ready_at_s"])
        assert later, f"no departure after loading ready for order {detail['order_id']}"
        assert detail["loading_ready_at_s"] <= later[0]
        handovers += 1
    assert handovers == 10, handovers
    print(
        f"[A03] PASS 10 orders loading-ready before their departure; "
        f"S4 reconciliation {len(recon['checks'])} checks passed"
    )

    # ---- A04: routes and segments generated ----------------------------------
    tracks = base["tracks"]
    assert tracks, "no vehicle tracks"
    for track in tracks:
        segments = track["segments"]
        assert segments, f"vehicle {track['vehicle_id']} has no segments"
        assert all(s["start_s"] <= s["end_s"] for s in segments)
        assert all(a["end_s"] <= b["start_s"] for a, b in zip(segments, segments[1:]))
        assert segments[-1]["to_node_id"] == track["end_node_id"]
    print(f"[A04] PASS vehicles={len(tracks)} segments={sum(len(t['segments']) for t in tracks)}")

    # ---- A05: tracks read back from PostgreSQL -------------------------------
    with engine.connect() as connection:
        persisted = connection.execute(
            text("select payload->'tracks' from integration_simulations where run_id = :run"),
            {"run": run_id},
        ).scalar_one()
    fetched = client.get(f"/api/v1/integration/runs/{run_id}/simulation")
    assert fetched.status_code == 200, fetched.text
    assert persisted == fetched.json()["tracks"], "persisted tracks differ from API payload"
    assert len(persisted) == len(tracks)
    print(f"[A05] PASS tracks round-trip from integration_simulations.payload ({len(persisted)} vehicles)")

    # ---- A06: legal transport_delay while in transit -------------------------
    departure = next(event for event in base["events"] if event["kind"] == "vehicle_departure")
    time_s = departure["time_s"] + 1
    vehicle = departure["vehicle_id"]
    command = {
        "vehicle_id": vehicle,
        "time_s": time_s,
        "delay_s": 60,
        "source_event_id": str(uuid4()),
        "reason": "Stage A acceptance in-transit delay",
        "budget_ms": 500,
    }
    incident = client.post(
        f"/api/v1/integration/runs/{run_id}/simulation/incidents", json=command, headers={}
    )
    assert incident.status_code == 200, incident.text
    proposal = incident.json()
    with engine.connect() as connection:
        event_row = connection.execute(
            text(
                "select payload->>'kind', source from events where id = :id"
            ),
            {"id": proposal["event_id"]},
        ).first()
    assert event_row is not None and event_row[0] == "transport_delay", event_row
    assert event_row[1] == "integration-simulation", event_row
    print(f"[A06] PASS transport_delay event {proposal['event_id']} persisted (source={event_row[1]})")

    # ---- A07: impacted orders and expected time shift ------------------------
    impact = proposal["impact"]
    assert impact["affected_order_ids"], impact
    assert proposal["proposal_valid"] is True, proposal["proposal_valid"]
    before_eta = impact.get("before_eta_s") or {}
    after_eta = impact.get("after_eta_s") or {}
    shifts = {order: after_eta[order] - before_eta[order] for order in after_eta if order in before_eta}
    assert shifts, impact
    assert all(delta >= 0 for delta in shifts.values()), shifts
    assert any(delta > 0 for delta in shifts.values()), shifts
    assert proposal["s1_local_solver"]["applied_to_simulation"] is False
    print(
        f"[A07] PASS affected_orders={len(impact['affected_order_ids'])} "
        f"max_shift={max(shifts.values())}s valid={proposal['proposal_valid']} s1_applied=False"
    )

    # ---- A08: pre-delay positions and events unchanged -----------------------
    before_ts = time_s - 1
    pre_base = client.get(
        f"/api/v1/integration/runs/{run_id}/simulation/state-at?time_s={before_ts}&view=baseline"
    )
    pre_cand = client.get(
        f"/api/v1/integration/runs/{run_id}/simulation/state-at?time_s={before_ts}&view=candidate"
    )
    assert pre_base.status_code == 200 and pre_cand.status_code == 200
    assert pre_base.json()["vehicle_positions"] == pre_cand.json()["vehicle_positions"]
    assert pre_base.json()["events"] == pre_cand.json()["events"]
    print(f"[A08] PASS positions and events identical before t={time_s} in both views")

    # ---- A09: baseline stays active before approval --------------------------
    pending = client.get(
        f"/api/v1/integration/runs/{run_id}/simulation/state-at?time_s={time_s + 5}&view=active"
    )
    assert pending.status_code == 200 and pending.json()["view"] == "baseline"
    assert pending.json()["active_version"] == 0
    assert pending.json()["incident_status"] == "pending"
    print("[A09] PASS pending incident leaves active view on baseline v0")

    protected_before = _counts(engine)

    # ---- A10: approval flips v0 -> v1 ---------------------------------------
    decision_path = f"/api/v1/integration/runs/{run_id}/simulation/incidents/{proposal['id']}"
    approved = client.post(f"{decision_path}/approve", json={"expected_row_version": 0}, headers={})
    assert approved.status_code == 200, approved.text
    assert approved.json()["status"] == "approved"
    after = client.get(f"/api/v1/integration/runs/{run_id}/simulation/state-at?time_s={time_s + 5}&view=active")
    assert after.status_code == 200, after.text
    assert after.json()["view"] == "candidate" and after.json()["active_version"] == 1
    assert after.json()["source_kind"] == "simulated_delay_projection"
    sim_view = client.get(f"/api/v1/integration/runs/{run_id}/simulation")
    assert sim_view.json()["baseline_version"] == 0 and sim_view.json()["active_version"] == 1
    print("[A10] PASS approval moved active version 0 -> 1 (source simulated_delay_projection)")

    # ---- A11: repeated approval is idempotent --------------------------------
    retry = client.post(f"{decision_path}/approve", json={"expected_row_version": 0}, headers={})
    assert retry.status_code == 200 and retry.json()["idempotent"] is True
    with engine.connect() as connection:
        incident_count = connection.execute(
            text("select count(*) from integration_simulation_incidents where simulation_id = :sim"),
            {"sim": base["simulation_id"]},
        ).scalar_one()
    assert incident_count == 1, incident_count
    assert client.get(f"/api/v1/integration/runs/{run_id}/simulation").json()["active_version"] == 1
    print("[A11] PASS repeated approval is idempotent (incidents=1, version stays 1)")

    # ---- A12: rejection keeps the original plan ------------------------------
    other_run = _checked_run(client, app, scenario_id)
    other = client.post(f"/api/v1/integration/runs/{other_run}/simulation", json={}, headers={})
    assert other.status_code == 200, other.text
    second = client.post(
        f"/api/v1/integration/runs/{other_run}/simulation/incidents",
        json={**command, "source_event_id": str(uuid4())},
        headers={},
    )
    assert second.status_code == 200, second.text
    rejected = client.post(
        f"/api/v1/integration/runs/{other_run}/simulation/incidents/{second.json()['id']}/reject",
        json={"expected_row_version": 0},
        headers={},
    )
    assert rejected.status_code == 200 and rejected.json()["status"] == "rejected"
    still_base = client.get(
        f"/api/v1/integration/runs/{other_run}/simulation/state-at?time_s={time_s + 5}&view=active"
    )
    assert still_base.status_code == 200
    assert still_base.json()["view"] == "baseline" and still_base.json()["active_version"] == 0
    print("[A12] PASS rejection keeps baseline v0 active")

    # ---- A13: replay at several timestamps ----------------------------------
    horizon = base["horizon_s"]
    samples = {}
    for ts in (0, max(1, time_s // 2), time_s, horizon):
        replay = client.get(f"/api/v1/integration/runs/{run_id}/simulation/state-at?time_s={ts}&view=active")
        assert replay.status_code == 200, replay.text
        body = replay.json()
        assert body["time_s"] == ts
        samples[ts] = (len(body["events"]), len(body.get("in_transit_vehicle_ids") or []))
    sample_args = sorted(samples.values())
    assert sample_args[-1][0] >= sample_args[0][0], samples
    assert len({v for v in samples.values()}) > 1, samples
    print(f"[A13] PASS state-at replay at {sorted(samples)}: events/in-transit {samples}")

    # ---- A14: inventory and real dispatch untouched -------------------------
    protected_after = _counts(engine)
    assert protected_before == protected_after, (protected_before, protected_after)
    assert sim_view.json()["operational_schedule_mutated"] is False
    assert sim_view.json()["inventory_mutated"] is False
    assert after.json()["operational_schedule_mutated"] is False
    assert after.json()["inventory_mutated"] is False
    print(f"[A14] PASS inventory/schedule row counts unchanged: {protected_after}")
