"""Read-only, exactly solved counterfactual for the cold-chain delay showcase.

This *small* fixture is an independently specified three-delivery subproblem
using the existing synthetic travel matrix. The exact enumerator is an actual
optimizer (not a hard-coded desired route or benefit). It must never be
presented as a result from the production OR-Tools multi-vehicle solver.
"""
from __future__ import annotations

import json
from itertools import permutations
from pathlib import Path


ROOT = Path(__file__).resolve().parents[5]
CASE_PATH = ROOT / 'data/benchmarks/delay_replanning_v1.json'


def solve_delay_benchmark(*, delay_s: int | None = None) -> dict:
    """Compute all six legal visit orders twice under exactly the same objective.

    First solve without the disruption; holding keeps that *original* order and
    adds the same delay. Rerouting optimizes only the remaining three stops.
    All alternatives have the same frozen prefix, matrix and service rules.
    """
    case = json.loads(CASE_PATH.read_text(encoding='utf-8'))
    source = json.loads((ROOT / 'data/scenarios' / case['source_scenario']).read_text(encoding='utf-8'))
    matrix = source['snapshot']['matrices'][0]
    distance = matrix['distance_m']
    travel = matrix['travel_s']
    stops = case['stops']
    indices = [item['location_index'] for item in stops]
    if len(indices) != len(set(indices)) or len(indices) > 8 or len(indices) < 2:
        raise ValueError('benchmark requires 2-8 distinct delivery locations')
    if len(distance) != len(travel) or any(len(row) != len(distance) for row in distance + travel):
        raise ValueError('invalid benchmark travel matrix')
    shift = case['delay_s'] if delay_s is None else delay_s
    if not isinstance(shift, int) or not 0 <= shift <= 1200:
        raise ValueError('delay_s must be an integer between 0 and 1200')
    by_location = {stop['location_index']: stop for stop in stops}

    def score(order: tuple[int, ...], delay: int) -> dict:
        node = case['start_location_index']
        clock = case['prefix_end_s'] + delay
        metres = 0
        late_seconds = 0
        events = []
        for destination in order:
            arc_m = distance[node][destination]
            arc_s = travel[node][destination]
            if arc_m is None or arc_s is None:
                raise ValueError('benchmark contains blocked travel arc')
            metres += arc_m
            clock += arc_s
            due = by_location[destination]['soft_due_s']
            lateness = max(0, clock - due)
            late_seconds += lateness
            events.append({
                'location_id': matrix['node_ids'][destination],
                'name': by_location[destination]['name'],
                'arrival_s': clock, 'soft_due_s': due,
                'late_s': lateness,
            })
            clock += case['stop_service_s']
            node = destination
        arc_m = distance[node][case['return_location_index']]
        arc_s = travel[node][case['return_location_index']]
        if arc_m is None or arc_s is None:
            raise ValueError('benchmark return arc is blocked')
        metres += arc_m
        clock += arc_s
        driving_cents = (metres * case['distance_rate_cents_per_km'] + 500) // 1000
        late_cents = late_seconds * case['soft_late_cents_per_s']
        return {
            'order': [by_location[index]['name'] for index in order],
            'order_location_ids': [matrix['node_ids'][index] for index in order],
            'deliveries': events,
            'distance_m': metres,
            'driving_cents': driving_cents,
            'fixed_vehicle_cents': case['fixed_vehicle_cents'],
            'soft_late_cents': late_cents,
            'objective_cents': driving_cents + late_cents + case['fixed_vehicle_cents'],
            'late_orders': sum(event['late_s'] > 0 for event in events),
            'total_late_s': late_seconds,
            'hard_window_valid': all(e['arrival_s'] <= case['hard_window_latest_s'] for e in events),
            'last_return_s': clock,
            'delivered_orders': len(events),
        }

    orders = list(permutations(indices))
    # Deterministic tie-breaking is independent of hash seed / machine state.
    base = min((score(p, 0) for p in orders), key=lambda x: (x['objective_cents'], x['order_location_ids']))
    baseline_indices = tuple(matrix['node_ids'].index(node_id) for node_id in base['order_location_ids'])
    hold = score(baseline_indices, shift)
    reroute = min((score(p, shift) for p in orders), key=lambda x: (x['objective_cents'], x['order_location_ids']))
    if not (base['hard_window_valid'] and hold['hard_window_valid'] and reroute['hard_window_valid']):
        raise ValueError('benchmark violates hard delivery window')
    return {
        'case_id': case['case_id'], 'name': case['name'], 'description': case['description'],
        'method': 'exact_enumeration', 'candidate_count': len(orders),
        'source_scenario': case['source_scenario'], 'matrix_hash': matrix['hash'],
        'simulation_only': True, 'not_production_routing_result': True,
        'assumptions': {
            'anchor_time_s': case['prefix_end_s'], 'delay_s': shift,
            'anchor_location_id': matrix['node_ids'][case['start_location_index']],
            'return_location_id': matrix['node_ids'][case['return_location_index']],
            'rate_cents_per_km': case['distance_rate_cents_per_km'],
            'penalty_cents_per_late_second': case['soft_late_cents_per_s'],
            'hard_window_latest_s': case['hard_window_latest_s'],
            'start_service_state': 'already_loaded_at_anchor',
        },
        'before_delay': base, 'simple_hold': hold, 'optimized_continuation': reroute,
        'comparison': {
            'route_changed': hold['order_location_ids'] != reroute['order_location_ids'],
            'distance_saved_m': hold['distance_m'] - reroute['distance_m'],
            'lateness_reduced_s': hold['total_late_s'] - reroute['total_late_s'],
            'late_orders_reduced': hold['late_orders'] - reroute['late_orders'],
            'objective_saved_cents': hold['objective_cents'] - reroute['objective_cents'],
            'improves_objective': reroute['objective_cents'] < hold['objective_cents'],
        },
    }
