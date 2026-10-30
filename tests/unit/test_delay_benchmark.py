"""Read-only counterfactual: authentic matrix and exhaustive optimizer; no PostgreSQL."""
from __future__ import annotations

import itertools
import json
from pathlib import Path

from logistics_backend.application.delay_benchmark import solve_delay_benchmark


def test_benchmark_is_computed_not_hard_coded():
    result = solve_delay_benchmark()
    hold = result['simple_hold']
    rerouted = result['optimized_continuation']
    assert result['candidate_count'] == 6
    assert result['method'] == 'exact_enumeration'
    assert result['source_scenario'] == 'coldchain_chain_10.json'
    assert sorted(hold['order_location_ids']) == sorted(rerouted['order_location_ids'])
    assert result['before_delay']['order_location_ids'] == hold['order_location_ids']
    assert hold['delivered_orders'] == rerouted['delivered_orders'] == 3
    assert all(item['hard_window_valid'] for item in
               (result['before_delay'], hold, rerouted))
    assert rerouted['objective_cents'] < hold['objective_cents']
    assert rerouted['late_orders'] < hold['late_orders']
    assert rerouted['total_late_s'] < hold['total_late_s']
    assert result['comparison']['distance_saved_m'] < 0  # no hidden claim of mileage saving
    assert result['comparison']['objective_saved_cents'] == hold['objective_cents'] - rerouted['objective_cents']


def test_zero_delay_matches_unperturbed_optimum():
    result = solve_delay_benchmark(delay_s=0)
    assert result['before_delay'] == result['simple_hold'] == result['optimized_continuation']
    assert result['comparison']['improves_objective'] is False


def test_every_returned_arrival_is_derived_from_synthetic_matrix():
    result = solve_delay_benchmark()
    root = Path(__file__).resolve().parents[2]
    scenario = json.loads((root / 'data/scenarios/coldchain_chain_10.json').read_text(encoding='utf-8'))
    matrix = scenario['snapshot']['matrices'][0]
    index = {node: i for i, node in enumerate(matrix['node_ids'])}
    for strategy in ('before_delay', 'simple_hold', 'optimized_continuation'):
        outcome = result[strategy]
        current = index[result['assumptions']['anchor_location_id']]
        elapsed = result['assumptions']['anchor_time_s'] + (0 if strategy == 'before_delay' else 90)
        for delivery in outcome['deliveries']:
            nxt = index[delivery['location_id']]
            elapsed += matrix['travel_s'][current][nxt]
            assert elapsed == delivery['arrival_s']
            current = nxt
        elapsed += matrix['travel_s'][current][index[result['assumptions']['return_location_id']]]
        assert elapsed == outcome['last_return_s']
