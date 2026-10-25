"""R30-E: independently derived, bounded exception-impact evidence.

Only consume the already reconciled R30-B baseline and event-sourced suffix.
Do not reinterpret a replay projection as an executable or persisted plan.
No database reads/writes or LLM inference occur in this module.
"""
from __future__ import annotations

from collections import Counter, defaultdict


def _delivery_orders(route: dict) -> list[str]:
    return [oid for stop in route.get('stops', ()) if stop.get('stop_kind') == 'delivery'
            for oid in stop.get('order_ids', ())]


def build_impact_evidence(*, baseline: dict, replay_events: list[dict],
                          next_operations: dict, interrupted_operation_ids: set[str],
                          order_changes: list[dict], event_t: int,
                          halted_vehicles: dict) -> dict:
    """Compare *effective* events, not stale geometry of halted routes.

    The resulting evidence contains old and new order-level ETAs, an explicit
    reason for non-service, vehicle delivery forecasts and warehouse operation
    changes. All delivery forecasts must correspond to an event in the merged
    suffix. A suspended truck's old route is never counted as delivery.
    """
    plan = baseline['plan']
    original_routes = {r['vehicle_id']: r for r in plan['routing']['routes']}
    old_work = {w['operation_id']: w for w in plan['warehouse']['operations']}
    original_unserved = {u['order_id'] for u in plan['routing'].get('unserved_orders', ())}
    planned_ids = {o['order_id'] for o in order_changes}

    deliveries = [e for e in replay_events if e['kind'] == 'order_delivered']
    times = {e['object_id']: e['time_s'] for e in deliveries}
    if len(times) != len(deliveries):
        raise RuntimeError('r30e_duplicate_delivery_in_event_projection')
    if not set(times).issubset(planned_ids):
        raise RuntimeError('r30e_unknown_delivered_order')

    enriched_orders = []
    for entry in order_changes:
        row = dict(entry)
        old_time, new_time = row.get('previous_delivery_at_s'), row.get('new_delivery_at_s')
        if new_time != times.get(row['order_id']):
            raise RuntimeError('r30e_order_eta_not_equal_to_replay_event:' + row['order_id'])
        old_vid, new_vid = row.get('previous_vehicle_id'), row.get('next_vehicle_id')
        reason = row.get('unserved_reason_code')
        if row['status'] == 'unserved' and not reason:
            raise RuntimeError('r30e_unserved_without_reason:' + row['order_id'])
        if row['status'] != 'unserved' and reason:
            raise RuntimeError('r30e_served_with_unserved_reason:' + row['order_id'])
        row['delivery_delta_s'] = (new_time - old_time if old_time is not None and new_time is not None else None)
        row['vehicle_changed'] = (new_vid != old_vid)
        row['time_changed'] = row['delivery_delta_s'] not in (0, None)
        row['affected'] = (row['vehicle_changed'] or row['time_changed'] or
                           (row['status'] == 'unserved' and row['order_id'] not in original_unserved))
        enriched_orders.append(row)

    predicted_by_vehicle: dict[str, list[tuple[int, str]]] = defaultdict(list)
    for e in deliveries:
        if not e.get('vehicle_id'):
            raise RuntimeError('r30e_delivery_missing_vehicle_id:' + e['object_id'])
        predicted_by_vehicle[e['vehicle_id']].append((e['time_s'], e['object_id']))
    vehicle_details = []
    vehicle_ids = ({v['vehicle_id'] for v in baseline['snapshot']['vehicles']}
                   | set(original_routes) | set(predicted_by_vehicle) | set(halted_vehicles))
    for vehicle_id in sorted(vehicle_ids):
        previous = original_routes.get(vehicle_id, {})
        planned = sorted(predicted_by_vehicle.get(vehicle_id, []))
        vehicle_details.append({
            'vehicle_id': vehicle_id,
            'previous_order_sequence': _delivery_orders(previous),
            'forecast_delivery_order_ids': [oid for _, oid in planned],
            'forecast_delivery_times_s': [{'order_id': oid, 'delivery_at_s': at} for at, oid in planned],
            'halted_at_event': vehicle_id in halted_vehicles,
            'halted_location': halted_vehicles.get(vehicle_id),
            'forecast_is_event_based': True,
        })

    operation_changes = []
    for op_id in sorted(set(old_work) | set(next_operations) | interrupted_operation_ids):
        old = old_work.get(op_id)
        new = next_operations.get(op_id)
        if op_id in interrupted_operation_ids:
            state = 'interrupted_at_event'
        elif old is None:
            state = 'new_after_event'
        elif new is None:
            state = 'cancelled_future_work'
        elif old == new and old['end_s'] <= event_t:
            state = 'completed_before_event'
        elif old == new and old['start_s'] <= event_t:
            state = 'started_before_event_preserved'
        elif old == new:
            state = 'unchanged_future_work'
        else:
            state = 'rescheduled_future_work'
        if state not in ('unchanged_future_work', 'completed_before_event', 'started_before_event_preserved'):
            operation_changes.append({'operation_id': op_id, 'status': state,
                'previous_resource_id': old.get('resource_id') if old else None,
                'new_resource_id': new.get('resource_id') if new else None,
                'previous_start_s': old.get('start_s') if old else None,
                'previous_end_s': old.get('end_s') if old else None,
                'new_start_s': new.get('start_s') if new else None,
                'new_end_s': new.get('end_s') if new else None})

    changed_eta = [o for o in enriched_orders if o['time_changed']]
    reassigned = [o for o in enriched_orders if o['vehicle_changed'] and o['status'] != 'unserved']
    warnings = ['simulation_forecast_not_live_telemetry',
                'event_sourced_replay_not_executable_dispatch_plan',
                'cannot_assume_transshipment_or_inventory_replenishment']
    return {
        'schema': 'r30e_exception_evidence_v1',
        'orders': enriched_orders,
        'vehicles': vehicle_details,
        'warehouse_operation_changes': operation_changes,
        'counts': {'affected_orders': sum(o['affected'] for o in enriched_orders),
                   'delivery_time_changed_orders': len(changed_eta),
                   'vehicle_reassigned_served_orders': len(reassigned),
                   'interrupted_operations': len(interrupted_operation_ids),
                   'changed_or_cancelled_operations': len(operation_changes),
                   'replay_predicted_delivery_orders': len(times)},
        'evidence_limits': warnings,
    }
