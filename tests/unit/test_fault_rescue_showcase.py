"""Regression for the independently solved fault-transfer demonstration.

Requires the project's pinned OR-Tools environment; never touches PostgreSQL.
"""
from __future__ import annotations

import pytest
from importlib.util import find_spec
from logistics_backend.application.fault_rescue_showcase import (  # noqa: E402
    VEHICLES, _baseline, _continuation_at, _simple_no_rescue, _metrics,
    solve_breakdown_showcase, POINTS,
)


def test_rescue_does_not_drop_in_service_delivery():
    original, time_s = _baseline()
    prefix, pending, location, ready_at = _continuation_at(
        original[VEHICLES[0]]['stops'], time_s, VEHICLES[0], dict(POINTS))
    assert prefix[-1]['node_id'] == 'demo-o1'
    assert ready_at > time_s
    assert 'demo-o1' not in pending
    assert 'demo-o2' in pending


def test_stranded_counterfactual_marks_unserved_orders():
    original, time_s = _baseline()
    no_rescue = _simple_no_rescue(original, time_s, dict(POINTS))
    score = _metrics(no_rescue, POINTS)
    assert score['total_orders'] == 8
    assert score['delivered_orders'] == 6
    assert score['undelivered_order_ids'] == ['demo-o4','demo-o5']
    broken = next(route for route in no_rescue if route['vehicle_id'] == VEHICLES[1])
    assert broken['stops'][-1]['kind'] == 'broken_down'
    assert broken['stops'][-1]['node_id'] == 'demo-o3'


@pytest.mark.skipif(find_spec('ortools') is None, reason='OR-Tools is not installed in this runtime')
def test_real_solver_recovers_fault_vehicle_orders_with_pickup_before_delivery():
    result = solve_breakdown_showcase(2500)
    assert result['status'] == 'solved', result.get('reason')
    assert result['candidate_valid']
    assert result['metrics']['no_rescue']['delivered_orders'] == 6
    assert result['metrics']['candidate']['delivered_orders'] == 8
    assert result['recovered_orders'] == 2
    assert set(result['reassigned_order_ids']) == {'demo-o4','demo-o5'}
    rescue_vehicle_ids = set(VEHICLES) - {result['failure_vehicle_id']}
    for rescued_order, vehicle_id in result['rescue_assignments'].items():
        assert vehicle_id in rescue_vehicle_ids
        route = next(row for row in result['candidate'] if row['vehicle_id'] == vehicle_id)
        nodes = [s['node_id'] for s in route['stops']]
        assert nodes.index('demo-pickup-' + rescued_order) < nodes.index(rescued_order)
    fault_route = next(row for row in result['candidate'] if row['vehicle_id'] == VEHICLES[1])
    assert all(s['node_id'] not in ('demo-o4','demo-o5') for s in fault_route['stops'])


def _build_independent_candidate_from_seed():
    """Create a physically feasible rescue for tests, without an optimizer."""
    from logistics_backend.application import fault_rescue_showcase as f
    baseline, fault = f._baseline()
    points = dict(f.POINTS)
    frozen, own, starts, ready = {}, {}, {}, {}
    vehicles = (f.VEHICLES[0], f.VEHICLES[2])
    for vehicle in vehicles:
        frozen[vehicle], own[vehicle], starts[vehicle], ready[vehicle] = f._continuation_at(
            baseline[vehicle]['stops'], fault, vehicle, points)
    pickups = {order: f'demo-pickup-{order}' for order in f.ROUTES[f.VEHICLES[1]][1:]}
    points.update({pickup: points[f.HANDOFF] for pickup in pickups.values()})
    seeds = f._construct_rescue_seeds(starts, ready, own, pickups, points)
    assert seeds
    _, selected = seeds[0]
    candidate = [{'vehicle_id': f.VEHICLES[1], 'stops': [
        *[dict(s) for s in baseline[f.VEHICLES[1]]['stops']
          if s['kind'] != 'depot_end' and s['departure_s'] <= fault],
        f._stop(f.HANDOFF, fault, f.HORIZON, 'broken_down')]}]
    for index, vehicle in enumerate(vehicles):
        route, last, now = [dict(s) for s in frozen[vehicle]], starts[vehicle], ready[vehicle]
        for node in selected[index]:
            now += f._travel(last, node, points)
            kind = 'pickup' if node in pickups.values() else 'delivery'
            duration = f.TRANSFER_SERVICE_S if kind == 'pickup' else f.STOP_SERVICE_S
            route.append(f._stop(node, now, now + duration, kind))
            now += duration
            last = node
        now += f._travel(last, f.DEPOT, points)
        route.append(f._stop(f.DEPOT, now, now, 'depot_end'))
        candidate.append({'vehicle_id': vehicle, 'stops': route})
    return candidate, frozen, own, pickups, points, fault


def test_already_delivered_start_is_not_delivered_twice():
    from logistics_backend.application import fault_rescue_showcase as f
    # This was the immediate cause of INFEASIBLE: O1 is already unloaded,
    # while vehicle 01 STARTS with the remaining O2 unit (load 1).
    pickup_nodes = {'demo-pickup-demo-o4', 'demo-pickup-demo-o5'}
    assert f._load_change('demo-o1', pickup_nodes, at_vehicle_start=True) == 0
    assert f._service_seconds('demo-o1', pickup_nodes, at_vehicle_start=True) == 0
    assert f._load_change('demo-o2', pickup_nodes) == -1
    assert f._service_seconds('demo-o2', pickup_nodes) == f.STOP_SERVICE_S
    assert f._load_change('demo-pickup-demo-o4', pickup_nodes) == 1
    assert f._load_change('demo-o4', pickup_nodes) == -1


def test_constructive_rescue_and_independent_checker():
    from logistics_backend.application import fault_rescue_showcase as f
    candidate, frozen, own, pickups, points, fault = _build_independent_candidate_from_seed()
    assert not f._validate_candidate(candidate, frozen, own, pickups, points, fault)
    metric = f._metrics(candidate, points)
    assert metric['delivered_orders'] == 8
    assert metric['undelivered_orders'] == 0
    # Simulate a false instant jump at the first post-failure visit.
    broken = [dict(route) for route in candidate]
    broken[1] = {'vehicle_id': broken[1]['vehicle_id'], 'stops': [dict(s) for s in broken[1]['stops']]}
    broken[1]['stops'][len(frozen[broken[1]['vehicle_id']])]['arrival_s'] = fault
    assert any('轨迹不连续' in error for error in
               f._validate_candidate(broken, frozen, own, pickups, points, fault))


def test_constructive_seed_can_split_cargo_across_trucks():
    from logistics_backend.application import fault_rescue_showcase as f
    base, fault = f._baseline()
    points, starts, ready, own = dict(f.POINTS), {}, {}, {}
    for v in (f.VEHICLES[0], f.VEHICLES[2]):
        _, own[v], starts[v], ready[v] = f._continuation_at(base[v]['stops'], fault, v, points)
    pickups = {order: f'demo-pickup-{order}' for order in ('demo-o4', 'demo-o5')}
    points.update({p: points[f.HANDOFF] for p in pickups.values()})
    seeds = f._construct_rescue_seeds(starts, ready, own, pickups, points)
    assert len(seeds) >= 4
    # Cross-vehicle handoff is not hardcoded to truck 01: both destinations
    # appear on the available trucks across the enumeration.
    assert any('demo-o4' in routes[0] and 'demo-o5' in routes[1] for _, routes in seeds)
    assert any('demo-o5' in routes[0] and 'demo-o4' in routes[1] for _, routes in seeds)
