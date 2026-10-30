"""Forced route-change acceptance: the remaining visit order must actually change.

Complements ``test_midroad_reroute.py`` (which accepts either strategy) with a
case that *requires* ``simulated_local_reroute`` and ``route_changed=True``, and
writes the raw before/after evidence to ``artifacts/reroute_case.json``.
"""
from __future__ import annotations

import json
from pathlib import Path
from uuid import UUID

import pytest

from logistics_backend.application.integration import solve_imported
from logistics_backend.application.integration_simulation_tracks import build_tracks
from logistics_backend.application.midroad_reroute import optimize_midroad_continuation
from logistics_backend.application.timeline import build_timeline
from logistics_contracts.integration import IntegrationRun, ScenarioImport

ROOT = Path(__file__).resolve().parents[2]
SCENARIO = ROOT / 'data/scenarios/coldchain_chain_10.json'
EVIDENCE = ROOT / 'artifacts/reroute_case.json'


@pytest.fixture(scope='module')
def solved():
    scenario = ScenarioImport.model_validate(json.loads(SCENARIO.read_text(encoding='utf-8')))
    result = solve_imported(scenario, IntegrationRun(scenario_id=UUID(int=1), budget_ms=12000), UUID(int=1))
    assert result['status'] == 'checked', result.get('reason')
    timeline = build_timeline(result, run_id=UUID(int=2))
    return result, timeline, build_tracks(result, timeline)


def _remaining_order(track: dict, at_s: int) -> list[str]:
    return [s['node_id'] for s in track['stops'] if s['arrival_s'] > at_s]


def test_delay_forces_a_different_remaining_visit_order(solved):
    result, timeline, tracks = solved
    original = json.loads(json.dumps(tracks))
    vehicle = next(t for t in tracks if len(t['stops']) >= 6)
    leg = next(s for s in vehicle['segments']
               if s['kind'] == 'travel' and s['end_s'] - s['start_s'] >= 2)
    at_s = leg['start_s'] + 1
    delay_s = 90

    outcome = optimize_midroad_continuation(
        result, tracks, timeline['events'], vehicle['vehicle_id'], at_s, delay_s, 800, 'forced-reroute')

    assert outcome['status'] == 'resolved', outcome.get('reason')
    assert outcome['proposal_valid'] is True
    assert outcome['strategy'] == 'simulated_local_reroute'
    assert outcome['route_changed'] is True
    assert outcome['applied_to_simulation'] is True
    # Immutable input is never mutated.
    assert tracks == original

    changed = next(t for t in outcome['candidate_tracks'] if t['vehicle_id'] == vehicle['vehicle_id'])
    before = _remaining_order(vehicle, at_s)
    after = _remaining_order(changed, at_s)
    assert set(before) == set(after), 'no order may be dropped or duplicated'
    assert before != after, 'the remaining visit order must actually change'

    # The vehicle continues from where it is, never from the depot again.
    assert changed['segments'][0]['start_s'] <= at_s
    assert changed['start_node_id'] == vehicle['start_node_id']
    first_future = next(s for s in changed['segments'] if s['end_s'] > at_s)
    assert first_future['start_s'] <= at_s + delay_s

    # Prefix already served before the incident is preserved (no re-delivery).
    served_before = [s for s in vehicle['stops'] if s['arrival_s'] <= at_s]
    served_after = [s for s in changed['stops'] if s['arrival_s'] <= at_s]
    assert [s['node_id'] for s in served_before] == [s['node_id'] for s in served_after]

    # Unaffected vehicles keep their plan exactly.
    for old_track, new_track in zip(tracks, outcome['candidate_tracks'], strict=True):
        if old_track['vehicle_id'] != vehicle['vehicle_id']:
            assert old_track == new_track

    # No time travel and no positional jumps inside the candidate.
    for seg_a, seg_b in zip(changed['segments'], changed['segments'][1:]):
        assert seg_a['end_s'] <= seg_b['start_s']
    events = outcome['candidate_events']
    assert all(a['time_s'] <= b['time_s'] for a, b in zip(events, events[1:]))

    EVIDENCE.parent.mkdir(parents=True, exist_ok=True)
    EVIDENCE.write_text(json.dumps({
        'vehicle_id': vehicle['vehicle_id'],
        'incident_at_s': at_s,
        'delay_s': delay_s,
        'status': outcome['status'],
        'strategy': outcome['strategy'],
        'route_changed': outcome['route_changed'],
        'proposal_valid': outcome['proposal_valid'],
        'remaining_before': before,
        'remaining_after': after,
        'before_eta_s': outcome.get('before_eta_s'),
        'after_eta_s': outcome.get('after_eta_s'),
        'candidate_tracks': outcome['candidate_tracks'],
        'original_tracks': tracks,
    }, ensure_ascii=False, indent=2), encoding='utf-8')
