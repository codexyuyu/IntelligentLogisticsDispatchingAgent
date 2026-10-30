"""Auditable estimates for the *persisted* simulation, not the independent benchmark.

All three strategies share the same actual checked-run matrix, completed prefix,
vehicle prices and order soft deadlines. No route distance is copied from a stale
``track.distance_m`` field after rerouting.
"""
from __future__ import annotations

from decimal import Decimal, ROUND_HALF_UP


def compare_simulated_delay(result: dict, baseline_tracks: list[dict], baseline_events: list[dict],
                            held_tracks: list[dict], held_events: list[dict],
                            candidate_tracks: list[dict], candidate_events: list[dict],
                            vehicle_id: str, at_s: int) -> dict:
    problem = result['transport_problem']
    matrix = problem['matrix']
    indices = {value: index for index, value in enumerate(matrix['node_ids'])}
    nodes = {node['id']: node for node in problem['nodes']}
    orders = {order['id']: order for order in problem['snapshot']['orders']}
    vehicles = {vehicle['id']: vehicle for vehicle in problem['snapshot']['vehicles']}
    rate = vehicles[vehicle_id]['rate_cents_per_km']
    fixed = vehicles[vehicle_id]['fixed_cost_cents']
    late_rate = problem['policy']['soft_late_cents_per_s']

    def location(node: str) -> str:
        return nodes[node]['location_id'] if node in nodes else node

    def score(tracks: list[dict], events: list[dict]) -> dict:
        track = next(track for track in tracks if track['vehicle_id'] == vehicle_id)
        travelled_m = Decimal('0')
        # A frozen mid-road prefix and its resumed portion share one matrix arc.
        for segment in track['segments']:
            if segment['kind'] not in ('travel', 'return'):
                continue
            start, end = location(segment['from_node_id']), location(segment['to_node_id'])
            distance = matrix['distance_m'][indices[start]][indices[end]]
            if distance is None:
                raise ValueError('route contains a blocked matrix arc')
            fraction = Decimal(str(segment.get('end_fraction', 1))) - Decimal(str(segment.get('start_fraction', 0)))
            if fraction < 0 or fraction > 1:
                raise ValueError('invalid partial arc fraction')
            travelled_m += Decimal(distance) * fraction
        metres = int(travelled_m.quantize(Decimal('1'), rounding=ROUND_HALF_UP))
        # The same per-vehicle price and objective are used for both alternatives.
        driving = int((travelled_m * rate / 1000).quantize(Decimal('1'), rounding=ROUND_HALF_UP))
        deliveries = [event for event in events if event['kind'] == 'order_delivered'
                      and event.get('vehicle_id') == vehicle_id and event.get('order_id')]
        if len(deliveries) != len({e['order_id'] for e in deliveries}):
            raise ValueError('duplicate order delivery in projection')
        stop_by_order = {stop['order_id']: stop for stop in track['stops']
                         if stop.get('kind') == 'delivery' and stop.get('order_id')}
        eta_by_order = {item['order_id']: item['time_s'] for item in deliveries}
        ordered = sorted(eta_by_order, key=lambda oid: (eta_by_order[oid], oid))
        stop_rows = []
        for order_id in ordered:
            order = orders[order_id]
            due = order.get('soft_due_at_s')
            # Mirrors the business KPI's completion timestamp, explicitly not
            # the solver's service-start penalty instant.
            late = max(0, eta_by_order[order_id] - due) if due is not None else 0
            stop = stop_by_order.get(order_id)
            stop_rows.append({
                'order_id': order_id, 'order_ref': order.get('external_ref') or order_id[:8],
                'node_id': stop['node_id'] if stop else None,
                'arrival_s': stop['arrival_s'] if stop else eta_by_order[order_id],
                'delivered_s': eta_by_order[order_id], 'soft_due_s': due, 'late_s': late,
            })
        late_seconds = sum(item['late_s'] for item in stop_rows)
        late_count = sum(item['late_s'] > 0 for item in stop_rows)
        penalty = late_seconds * late_rate
        return {
            'distance_m': metres, 'driving_cents': driving, 'fixed_vehicle_cents': fixed,
            'late_penalty_cents': penalty, 'objective_cents': driving + fixed + penalty,
            'late_orders': late_count, 'total_late_s': late_seconds,
            'deliveries': stop_rows,
            'return_s': next((e['time_s'] for e in events if e['kind'] == 'vehicle_return'
                              and e.get('vehicle_id') == vehicle_id), None),
        }

    baseline = score(baseline_tracks, baseline_events)
    hold = score(held_tracks, held_events)
    candidate = score(candidate_tracks, candidate_events)
    # All completed/pending orders must be preserved. A cost comparison with
    # missing orders is not a valid claim of optimization.
    coverage = {row['order_id'] for row in hold['deliveries']} == {row['order_id'] for row in candidate['deliveries']}
    before_order = [row['order_id'] for row in hold['deliveries'] if row['delivered_s'] > at_s]
    after_order = [row['order_id'] for row in candidate['deliveries'] if row['delivered_s'] > at_s]
    return {
        'scope': 'affected_vehicle_full_route', 'source': 'checked_run_simulation',
        'method': 'matrix_arc_fraction_and_delivery_events',
        'distance_approximate': True,
        'late_definition': 'delivery_completion_after_soft_due',
        'soft_due_configured': any(row['soft_due_s'] is not None for row in hold['deliveries']),
        'objective_note': '行驶里程费＋车辆固定费＋订单软时效完成超期费用；不包含其他全局目标项',
        'vehicle_id': vehicle_id, 'incident_time_s': at_s,
        'baseline': baseline, 'simple_hold': hold, 'candidate': candidate,
        'route_changed': before_order != after_order,
        'coverage_preserved': coverage,
        'delta_vs_hold': {
            'distance_saved_m': hold['distance_m'] - candidate['distance_m'],
            'late_orders_reduced': hold['late_orders'] - candidate['late_orders'],
            'lateness_reduced_s': hold['total_late_s'] - candidate['total_late_s'],
            'objective_saved_cents': hold['objective_cents'] - candidate['objective_cents'],
            'improves_objective': coverage and candidate['objective_cents'] < hold['objective_cents'],
        },
    }
