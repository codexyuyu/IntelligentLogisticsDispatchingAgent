"""Pure calculation tests: never access PostgreSQL, worker or OR-Tools."""
from logistics_backend.application.simulation_comparison import compare_simulated_delay


def _fixture():
    result = {'transport_problem': {
        'matrix': {'node_ids': ['depot', 'a', 'b'], 'distance_m': [[0, 1000, 2000], [1000, 0, 1000], [2000, 1000, 0]]},
        'nodes': [{'id': 'na', 'location_id': 'a'}, {'id': 'nb', 'location_id': 'b'}],
        'snapshot': {'orders': [{'id': 'o1', 'external_ref': 'O-1', 'soft_due_at_s': 100},
                                {'id': 'o2', 'external_ref': 'O-2', 'soft_due_at_s': 200}],
                     'vehicles': [{'id': 'v1', 'rate_cents_per_km': 200, 'fixed_cost_cents': 5000}]},
        'policy': {'soft_late_cents_per_s': 5},
    }}
    track = {'vehicle_id': 'v1', 'start_node_id': 'depot', 'end_node_id': 'depot',
             'stops': [{'node_id': 'na', 'kind': 'delivery', 'order_id': 'o1', 'arrival_s': 90},
                       {'node_id': 'nb', 'kind': 'delivery', 'order_id': 'o2', 'arrival_s': 180}],
             'segments': [{'from_node_id': 'depot', 'to_node_id': 'na', 'kind': 'travel', 'start_s': 0, 'end_s': 90},
                          {'from_node_id': 'na', 'to_node_id': 'nb', 'kind': 'travel', 'start_s': 90, 'end_s': 180},
                          {'from_node_id': 'nb', 'to_node_id': 'depot', 'kind': 'return', 'start_s': 180, 'end_s': 270}]}
    events = [{'kind': 'order_delivered', 'vehicle_id': 'v1', 'order_id': 'o1', 'time_s': 90},
              {'kind': 'order_delivered', 'vehicle_id': 'v1', 'order_id': 'o2', 'time_s': 180},
              {'kind': 'vehicle_return', 'vehicle_id': 'v1', 'time_s': 270}]
    return result, track, events


def test_identical_hold_proposals_have_no_claimed_savings():
    result, track, events = _fixture()
    comparison = compare_simulated_delay(result, [track], events, [track], events, [track], events, 'v1', 5)
    assert comparison['delta_vs_hold']['objective_saved_cents'] == 0
    assert comparison['delta_vs_hold']['improves_objective'] is False
    assert comparison['route_changed'] is False
    assert comparison['simple_hold']['distance_m'] == 4000


def test_soft_due_penalty_and_segment_fractions_are_recomputed():
    result, track, events = _fixture()
    delayed_events = [{**e, 'time_s': e['time_s']+90} for e in events]
    partial = {'vehicle_id': 'v1', 'start_node_id': 'depot', 'end_node_id': 'depot', 'stops': track['stops'],
        'distance_m': 999_999,  # deliberately stale; must not be used
        'segments': [
            {'from_node_id': 'depot', 'to_node_id': 'na', 'kind': 'travel', 'start_s': 0, 'end_s': 40, 'start_fraction': 0, 'end_fraction': 0.4},
            {'from_node_id': 'depot', 'to_node_id': 'na', 'kind': 'hold', 'start_s': 40, 'end_s': 130},
            {'from_node_id': 'depot', 'to_node_id': 'na', 'kind': 'travel', 'start_s': 130, 'end_s': 180, 'start_fraction': 0.4, 'end_fraction': 1},
            *track['segments'][1:],
        ]}
    comparison = compare_simulated_delay(result, [track], events, [partial], delayed_events,
                                          [track], events, 'v1', 40)
    assert comparison['simple_hold']['distance_m'] == 4000
    assert comparison['simple_hold']['total_late_s'] == 150
    assert comparison['candidate']['total_late_s'] == 0
    assert comparison['delta_vs_hold']['objective_saved_cents'] == 750
    assert comparison['delta_vs_hold']['improves_objective'] is True
