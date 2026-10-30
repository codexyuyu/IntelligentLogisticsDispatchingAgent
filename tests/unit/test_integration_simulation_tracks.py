"""Stage A route/replay invariants without requiring a PostgreSQL server."""

from __future__ import annotations

import json
from copy import deepcopy
from datetime import UTC, datetime
from itertools import pairwise
from pathlib import Path
from uuid import UUID

import pytest

from logistics_backend.application.integration import solve_imported
from logistics_backend.application.integration_simulation import IntegrationSimulationService
from logistics_backend.application.integration_simulation_tracks import (
    SimulationTrackError,
    build_tracks,
    delay_impact,
    hold_and_shift,
    retime_events,
    sample_track,
)
from logistics_backend.application.timeline import build_timeline, state_at_time
from logistics_contracts.events import EventEnvelopeDTO
from logistics_contracts.integration import IntegrationRun, ScenarioImport

SCENARIO = Path(__file__).resolve().parents[2] / 'data/scenarios/coldchain_chain_10.json'


@pytest.fixture(scope='module')
def checked():
    scenario = ScenarioImport.model_validate(json.loads(SCENARIO.read_text(encoding='utf-8')))
    result = solve_imported(scenario, IntegrationRun(scenario_id=UUID(int=1), budget_ms=12000), UUID(int=1))
    assert result['status'] == 'checked', result.get('reason')
    timeline = build_timeline(result, run_id=UUID(int=2))
    return result, timeline


def incident_time(timeline):
    first = next(event for event in timeline['events'] if event['kind'] == 'vehicle_departure')
    vehicle = first['vehicle_id']
    later = next(event for event in timeline['events'] if event['kind'] == 'order_delivered'
                 and event['vehicle_id'] == vehicle and event['time_s'] > first['time_s'])
    assert later['time_s'] > first['time_s']
    return vehicle, first['time_s'] + 1


def test_schematic_tracks_match_checked_routes_and_survive_json(checked):
    result, timeline = checked
    tracks = build_tracks(result, timeline)
    assert tracks == build_tracks(result, timeline)
    assert len(tracks) == len(result['transport_solution']['candidate']['routes'])
    assert len({track['vehicle_id'] for track in tracks}) == len(tracks)
    assert json.loads(json.dumps(tracks)) == tracks
    for track in tracks:
        segments = track['segments']
        assert segments[-1]['to_node_id'] == track['end_node_id']
        assert all(s['start_s'] <= s['end_s'] for s in segments)
        assert all(a['end_s'] <= b['start_s'] for a, b in pairwise(segments))
        assert sample_track(track, segments[-1]['end_s'])['progress'] == 1


def test_midroad_hold_freezes_position_and_retains_history(checked):
    result, timeline = checked
    vehicle, time_s = incident_time(timeline)
    tracks = build_tracks(result, timeline)
    baseline = deepcopy(tracks)
    shifted = hold_and_shift(tracks, vehicle, time_s, 10)
    assert tracks == baseline
    original = next(track for track in tracks if track['vehicle_id'] == vehicle)
    later = next(track for track in shifted if track['vehicle_id'] == vehicle)
    before = sample_track(original, time_s)
    at_hold = sample_track(later, time_s + 5)
    assert (before['from_node_id'], before['to_node_id'], before['progress']) == (
        at_hold['from_node_id'], at_hold['to_node_id'], at_hold['progress'])
    assert at_hold['kind'] == 'hold'
    assert sample_track(original, time_s - 1)['progress'] == sample_track(later, time_s - 1)['progress']
    assert later['segments'][-1]['end_s'] == original['segments'][-1]['end_s'] + 10
    for a, b in zip(tracks, shifted, strict=True):
        if a['vehicle_id'] != vehicle:
            assert a == b


def test_incident_retimes_only_future_affected_vehicle_events(checked):
    result, timeline = checked
    vehicle, time_s = incident_time(timeline)
    events = timeline['events']
    candidate = retime_events(events, vehicle, time_s, 10, 'incident-1')
    assert events == timeline['events']
    assert len(candidate) == len(events) + 1
    assert sum(item['kind'] == 'transport_delay' for item in candidate) == 1
    assert [item['time_s'] for item in candidate] == sorted(item['time_s'] for item in candidate)
    assert [item['sequence'] for item in candidate] == list(range(len(candidate)))
    for item in events:
        if item['time_s'] <= time_s or item['vehicle_id'] != vehicle:
            assert any(next_item['id'] == item['id'] and next_item['time_s'] == item['time_s']
                       for next_item in candidate)
        else:
            assert any(next_item['kind'] == item['kind'] and next_item['object_id'] == item['object_id']
                       and next_item['time_s'] == item['time_s'] + 10 for next_item in candidate)
    final = state_at_time({'events': candidate}, result, max(e['time_s'] for e in candidate) + 1)
    assert len(final['completed_order_ids']) == 10
    assert len(final['completed_operation_ids']) == 30


def test_hard_constraint_violation_and_bad_input_are_rejected(checked):
    result, timeline = checked
    vehicle, time_s = incident_time(timeline)
    impact = delay_impact(result, timeline['events'], vehicle, time_s, 1)
    assert impact['affected_order_ids']
    assert impact['valid']
    assert not delay_impact(result, timeline['events'], vehicle, time_s, 100000)['valid']
    with pytest.raises(SimulationTrackError):
        hold_and_shift(build_tracks(result, timeline), vehicle, time_s, 0)
    with pytest.raises(SimulationTrackError):
        hold_and_shift(build_tracks(result, timeline), 'no-such-vehicle', time_s, 1)
    unchecked = deepcopy(result)
    unchecked['status'] = 'not_checked'
    with pytest.raises(SimulationTrackError):
        build_tracks(unchecked, timeline)


def test_s1_local_solver_is_not_misreported_as_applied_route(checked):
    result, timeline = checked
    vehicle, time_s = incident_time(timeline)
    advisory = IntegrationSimulationService._s1_advice(result, vehicle, time_s, 1, 300)
    assert advisory['status'] in {'resolved', 'not_resolved'}
    assert advisory['applied_to_simulation'] is False


def test_simulated_incident_uses_legal_transport_delay_event_contract(checked):
    result, timeline = checked
    vehicle, time_s = incident_time(timeline)
    route = next(track for track in build_tracks(result, timeline) if track['vehicle_id'] == vehicle)
    task_id = next(task for stop in route['stops'] if stop['departure_s'] >= time_s
                   for task in stop['task_ids'])
    input_data = {
        'schema_version': '2.0.0', 'source': 'integration-simulation',
        'source_event_id': 'test-incident', 'kind': 'transport_delay',
        'occurred_at_utc': datetime.now(UTC).replace(microsecond=0), 'simulation_id': UUID(int=2),
        'payload': {'kind': 'transport_delay',
                    'entity_ref': {'kind': 'transport_task', 'id': task_id, 'revision': None},
                    'transport_task_id': task_id, 'effective_at_s': time_s,
                    'additional_seconds': 1, 'reason': 'simulated delay'},
    }
    assert EventEnvelopeDTO.model_validate(input_data).to_domain().payload.additional_seconds == 1
    input_data['kind'] = 'vehicle_delay'
    with pytest.raises(ValueError):
        EventEnvelopeDTO.model_validate(input_data)


def test_new_simulation_endpoints_extend_existing_integration_router():
    from logistics_backend.api.integration import router

    available = {(route.path, method) for route in router.routes
                 for method in (getattr(route, 'methods', None) or ())}
    assert ('/integration/runs/{run_id}/simulation', 'POST') in available
    assert ('/integration/runs/{run_id}/simulation/state-at', 'GET') in available
    assert ('/integration/runs/{run_id}/simulation/incidents/{incident_id}/approve', 'POST') in available
    assert ('/integration/runs/{run_id}/simulation/incidents/{incident_id}/reject', 'POST') in available
