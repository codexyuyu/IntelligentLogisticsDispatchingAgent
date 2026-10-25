"""R28 order-level reconciliation for a validated, read-only warehouse/route plan.

All scope and lifecycle counts are computed from the same snapshot and plan;
no UI clock, database writes, synthetic signatures or inferred deliveries.
"""
from __future__ import annotations

from collections import Counter


class ReconciliationError(ValueError):
    """A purported validated plan violates order-level accounting."""


def reconcile(snapshot, plan, events: list[dict]) -> dict:
    orders = {item.order_id: item for item in snapshot.orders}
    order_ids = set(orders)
    if len(orders) != len(snapshot.orders):
        raise ReconciliationError('r28_duplicate_snapshot_order')
    operations = [work for work in plan.warehouse.operations]
    task_orders = {o.operation_id: tuple(o.order_ids) for o in snapshot.operations}
    expected_operation_ids = Counter(o.operation_id for o in snapshot.operations)
    scheduled_operation_ids = Counter(o.operation_id for o in operations)
    tasks = Counter(oid for work in operations for oid in task_orders.get(work.operation_id, ()))
    completed = Counter(h.order_id for h in plan.warehouse.warehouse_handoffs)
    served = Counter(oid for route in plan.routing.routes for stop in route.stops
                     if stop.stop_kind == 'delivery' for oid in stop.order_ids)
    unserved = Counter(item.order_id for item in plan.routing.unserved_orders)
    event_deliveries = Counter(e['object_id'] for e in events if e['kind'] == 'order_delivered')
    event_handoffs = Counter(e['object_id'] for e in events if e['kind'] == 'loading_ready')
    event_returns = Counter(e['object_id'] for e in events if e['kind'] == 'vehicle_return')
    departure_events = Counter(e['object_id'] for e in events if e['kind'] == 'vehicle_departure')
    routes = [route for route in plan.routing.routes if route.stops]
    route_vehicles = Counter(route.vehicle_id for route in routes)
    violations = []
    def problem(code, identifiers):
        if identifiers:
            violations.append({'code': code, 'order_ids': sorted(str(x) for x in identifiers)})
    def wrong_counts(counts, expected):
        return {key for key in set(counts) | set(expected) if counts[key] != expected[key]}
    expected_delivery = {oid: 1 for oid in order_ids}
    problem('scheduled_warehouse_operations_mismatch', wrong_counts(scheduled_operation_ids, expected_operation_ids))
    problem('unknown_or_duplicate_handoffs', wrong_counts(completed, expected_delivery))
    problem('unknown_or_duplicate_warehouse_operations', {oid for oid in tasks if oid not in order_ids})
    problem('missing_warehouse_operations', order_ids - set(tasks))
    problem('unknown_or_duplicate_route_deliveries', {oid for oid, n in served.items() if oid not in order_ids or n != 1})
    problem('unknown_or_duplicate_unserved', {oid for oid, n in unserved.items() if oid not in order_ids or n != 1})
    problem('route_and_unserved_overlap', set(served) & set(unserved))
    problem('unaccounted_orders', order_ids - (set(served) | set(unserved)))
    problem('event_delivery_mismatch', wrong_counts(event_deliveries, served))
    problem('event_handoff_mismatch', wrong_counts(event_handoffs, completed))
    problem('duplicate_vehicle_route', {k for k, v in route_vehicles.items() if v > 1})
    problem('vehicle_departure_event_mismatch', wrong_counts(departure_events, route_vehicles))
    problem('vehicle_return_event_mismatch', wrong_counts(event_returns, route_vehicles))
    handoffs = {h.order_id: h for h in plan.warehouse.warehouse_handoffs}
    max_end_by_order = {}
    for work in operations:
        for oid in task_orders.get(work.operation_id, ()):
            max_end_by_order[oid] = max(max_end_by_order.get(oid, 0), work.end_s)
    problem('handoff_before_warehouse_operations_finished', {
        oid for oid, handoff in handoffs.items()
        if oid in max_end_by_order and handoff.ready_at_s < max_end_by_order[oid]
    })
    for route in routes:
        depart = route.stops[0].departure_at_s
        for stop in route.stops:
            if stop.stop_kind != 'delivery':
                continue
            for oid in stop.order_ids:
                if oid in handoffs and depart < handoffs[oid].ready_at_s:
                    problem('departure_before_loading_ready', (oid,))
    # A replay timestamp must never misrepresent forecast events as signed delivery.
    if violations:
        raise ReconciliationError('r28_reconciliation_failed:' + ','.join(x['code'] for x in violations))
    delivery_details = {oid: (stop.departure_at_s, route.vehicle_id)
                        for route in plan.routing.routes for stop in route.stops
                        if stop.stop_kind == 'delivery' for oid in stop.order_ids}
    planned_ids = sorted(served)
    unserved_ids = sorted(unserved)
    return {
        'status': 'passed', 'scope_order_count': len(order_ids),
        'warehouse_operation_order_count': len(tasks),
        'loading_ready_order_count': len(completed),
        'planned_delivery_order_count': len(planned_ids),
        'unserved_order_count': len(unserved_ids),
        'planned_delivery_ids': planned_ids, 'unserved_order_ids': unserved_ids,
        'order_statuses': [
            {'order_id': oid, 'warehouse_task_count': tasks[oid], 'loading_ready': completed[oid] == 1,
             'routing_status': 'planned' if oid in served else 'unserved',
             'planned_delivery_at_s': delivery_details[oid][0] if oid in delivery_details else None,
             'planned_vehicle_id': delivery_details[oid][1] if oid in delivery_details else None,
             'loading_ready_at_s': handoffs[oid].ready_at_s,
             'unserved_reason': next((u.reason_code for u in plan.routing.unserved_orders if u.order_id == oid), None)}
            for oid in sorted(order_ids)
        ],
        'formula': 'scope_orders = planned_delivery_orders + explicitly_unserved_orders',
        'note': 'planning_forecast_only_not_actual_customer_signature',
    }
