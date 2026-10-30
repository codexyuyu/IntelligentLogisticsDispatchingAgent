"""Algorithm enhancement acceptance checks; run with OR-Tools installed.

Does not require PostgreSQL or access to a real operational database.
"""
from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path
from uuid import UUID

import pytest

from logistics_backend.application.integration import solve_imported
from logistics_backend.application.integration_simulation_tracks import build_tracks
from logistics_backend.application.midroad_reroute import optimize_midroad_continuation
from logistics_backend.application.timeline import build_timeline
from logistics_contracts.integration import IntegrationRun, ScenarioImport
from logistics_contracts.transport import TransportProblemDTO
from logistics_domain.orders import CargoType
from logistics_domain.planning import SolveBudget, SolveStatus
from logistics_optimization.transport.solver import OrToolsTransportSolver
from datetime import datetime, UTC, timedelta

SCENARIO = Path(__file__).resolve().parents[2] / 'data/scenarios/coldchain_chain_10.json'


@pytest.fixture(scope='module')
def checked():
    scenario = ScenarioImport.model_validate(json.loads(SCENARIO.read_text(encoding='utf-8')))
    result = solve_imported(scenario, IntegrationRun(scenario_id=UUID(int=1), budget_ms=12000), UUID(int=1))
    assert result['status'] == 'checked'
    timeline = build_timeline(result, run_id=UUID(int=2))
    return result, timeline


def test_cargo_class_is_a_routing_constraint_not_only_a_validator(checked):
    result, _ = checked
    problem = TransportProblemDTO.model_validate(result['transport_problem']).to_domain()
    assert any(c.cargo_type != CargoType.FROZEN for c in problem.snapshot.cargo)
    incompatible = replace(problem, vehicles=tuple(replace(v, allowed_cargo_types=(CargoType.FROZEN,))
                                                    for v in problem.vehicles))
    budget = SolveBudget(wall_time_ms=400, deadline_utc=(datetime.now(UTC) + timedelta(seconds=60)).replace(microsecond=0),
                         max_candidates=1, seed=0, worker_count=1, deterministic_test_mode=False)
    output = OrToolsTransportSolver().solve(incompatible, budget)
    assert output.status not in (SolveStatus.OPTIMAL, SolveStatus.FEASIBLE)
    assert output.candidate is None


def test_continuation_preserves_prefix_and_all_deliveries_when_resolved(checked):
    result, timeline = checked
    tracks = build_tracks(result, timeline)
    vehicle = next(t for t in tracks if len(t['stops']) >= 4)
    leg = next(s for s in vehicle['segments'] if s['kind'] == 'travel'
               and s['end_s'] - s['start_s'] >= 2
               and any(stop['node_id'] == s['to_node_id'] and stop['sequence'] < len(vehicle['stops'])-1
                       for stop in vehicle['stops']))
    at_s = leg['start_s'] + 1
    original = json.loads(json.dumps(tracks))
    outcome = optimize_midroad_continuation(result, tracks, timeline['events'], vehicle['vehicle_id'],
                                              at_s, 30, 500, 'local-test')
    assert tracks == original  # never mutates immutable checked tracks
    if outcome['status'] == 'not_resolved':
        assert outcome['applied_to_simulation'] is False
        assert outcome['reason']
        return
    assert outcome['proposal_valid'] is True
    assert outcome['applied_to_simulation'] is True
    assert outcome['strategy'] in ('simulated_local_reroute', 'simulated_local_retimed')
    assert outcome['candidate_tracks'] != tracks
    for original_track, changed in zip(tracks, outcome['candidate_tracks'], strict=True):
        if original_track['vehicle_id'] != vehicle['vehicle_id']:
            assert original_track == changed
    old = [e for e in timeline['events'] if e['kind'] == 'order_delivered']
    new = [e for e in outcome['candidate_events'] if e['kind'] == 'order_delivered']
    assert len(old) == len(new)
    assert {e['order_id'] for e in old} == {e['order_id'] for e in new}
    original_event_ids = {e['id'] for e in timeline['events'] if e['time_s'] <= at_s}
    assert original_event_ids <= {e['id'] for e in outcome['candidate_events']}
