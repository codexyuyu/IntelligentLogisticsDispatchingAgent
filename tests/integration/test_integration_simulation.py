"""Stage A HTTP/database acceptance (requires TEST_DATABASE_URL on isolated PG)."""

from __future__ import annotations

import json
from pathlib import Path
from uuid import UUID, uuid4

import pytest
from sqlalchemy import func, select

from logistics_backend.persistence.integration_models import (
    integration_simulation_incidents,
    integration_simulations,
)
from logistics_backend.worker import Worker

pytestmark = pytest.mark.requires_postgres
ROOT = Path(__file__).resolve().parents[2]


def _checked_run(client, app, scenario_id):
    submitted = client.post('/api/v1/integration/runs?wait=false',
        json={'scenario_id': scenario_id, 'budget_ms': 12000},
        headers={'Idempotency-Key': str(uuid4())})
    assert submitted.status_code == 200, submitted.text
    Worker(app.state.jobs.repository, app.state.jobs.registry).run_once()
    run_id = submitted.json()['run_id']
    run = client.get(f'/api/v1/integration/runs/{run_id}')
    assert run.status_code == 200 and run.json()['status'] == 'checked', run.text
    return run_id


def test_simulation_routes_delay_approval_and_rejection_persist(warehouse_api):
    client, app, _, _ = warehouse_api
    fixture = json.loads((ROOT / 'data/scenarios/coldchain_chain_10.json').read_text(encoding='utf-8'))
    imported = client.post('/api/v1/integration/scenarios', json=fixture, headers={})
    assert imported.status_code == 200, imported.text
    scenario_id = imported.json()['scenario_id']
    run_id = _checked_run(client, app, scenario_id)
    start = client.post(f'/api/v1/integration/runs/{run_id}/simulation', json={}, headers={})
    assert start.status_code == 200, start.text
    baseline = start.json()
    assert baseline['source_kind'] == 'simulated_from_planned'
    assert baseline['input_source_kind'] == 'synthetic'
    assert baseline['reconciliation']['scope_orders'] == 10
    assert baseline['operational_schedule_mutated'] is False
    assert baseline['inventory_mutated'] is False
    assert baseline['tracks']
    again = client.post(f'/api/v1/integration/runs/{run_id}/simulation', json={}, headers={})
    assert again.status_code == 200 and again.json()['simulation_id'] == baseline['simulation_id']
    departure = next(e for e in baseline['events'] if e['kind'] == 'vehicle_departure')
    time_s, vehicle = departure['time_s'] + 1, departure['vehicle_id']
    command = {'vehicle_id': vehicle, 'time_s': time_s, 'delay_s': 1,
               'source_event_id': str(uuid4()), 'reason': 'isolated PG simulated delay', 'budget_ms': 300}
    incident = client.post(f'/api/v1/integration/runs/{run_id}/simulation/incidents',
        json=command, headers={})
    assert incident.status_code == 200, incident.text
    proposal = incident.json()
    assert proposal['status'] == 'pending'
    assert proposal['proposal_valid'] is True
    assert proposal['impact']['affected_order_ids']
    assert proposal['strategy'] in {'simulated_hold_resume', 'simulated_local_reroute', 'simulated_local_retimed'}
    assert proposal['s1_local_solver']['applied_to_simulation'] is (
        proposal['strategy'] != 'simulated_hold_resume')
    assert proposal['impact']['valid'] is True
    # Approval does not apply until the operator acts.
    before = client.get(f'/api/v1/integration/runs/{run_id}/simulation/state-at?time_s={time_s + 5}&view=active')
    assert before.status_code == 200 and before.json()['view'] == 'baseline'
    decision_path = f'/api/v1/integration/runs/{run_id}/simulation/incidents/{proposal["id"]}'
    approve = client.post(f'{decision_path}/approve', json={'expected_row_version': 0}, headers={})
    assert approve.status_code == 200, approve.text
    assert approve.json()['status'] == 'approved'
    retry = client.post(f'{decision_path}/approve', json={'expected_row_version': 0}, headers={})
    assert retry.status_code == 200 and retry.json()['idempotent'] is True
    forbidden = client.post(f'{decision_path}/reject', json={'expected_row_version': 1}, headers={})
    assert forbidden.status_code == 422
    after = client.get(f'/api/v1/integration/runs/{run_id}/simulation/state-at?time_s={time_s + 5}&view=active')
    assert after.status_code == 200, after.text
    assert after.json()['view'] == 'candidate'
    assert after.json()['incident_status'] == 'approved'
    assert after.json()['vehicle_positions'][vehicle]['time_s'] == time_s + 5
    assert after.json()['operational_schedule_mutated'] is False
    with app.state.engine.connect() as connection:
        sim_count = connection.execute(select(func.count()).select_from(integration_simulations)
            .where(integration_simulations.c.run_id == UUID(run_id))).scalar_one()
        incident_count = connection.execute(select(func.count()).select_from(integration_simulation_incidents)
            .where(integration_simulation_incidents.c.simulation_id == UUID(baseline['simulation_id']))).scalar_one()
    assert (sim_count, incident_count) == (1, 1)

    # Rejection is a second run, never a mutation of the approved first run.
    other_id = _checked_run(client, app, scenario_id)
    other = client.post(f'/api/v1/integration/runs/{other_id}/simulation', json={}, headers={})
    assert other.status_code == 200, other.text
    second = client.post(f'/api/v1/integration/runs/{other_id}/simulation/incidents',
        json={**command, 'source_event_id': str(uuid4())}, headers={})
    assert second.status_code == 200, second.text
    reject = client.post(f'/api/v1/integration/runs/{other_id}/simulation/incidents/{second.json()["id"]}/reject',
        json={'expected_row_version': 0}, headers={})
    assert reject.status_code == 200 and reject.json()['status'] == 'rejected'
    active = client.get(f'/api/v1/integration/runs/{other_id}/simulation/state-at?time_s={time_s + 5}&view=active')
    assert active.status_code == 200 and active.json()['view'] == 'baseline'
