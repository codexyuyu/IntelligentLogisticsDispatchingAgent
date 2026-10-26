"""R30-D read-only, independent cold-chain facts audit.

Pure domain rules over *contract-shaped dicts*; no DB, solver, SDK or HTTP.
A partial report is NOT a positive stock availability certificate.  In
particular, R24 does not supply authoritative reserved/quarantined balances.
This module does not model time-dependent cold-room occupancy, pre-cooling or
cleaning, and does not invent those capabilities.
"""
from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timedelta
from typing import Any, Mapping, Sequence


RULES = (
    'coldchain.batch_exists', 'coldchain.batch_warehouse',
    'coldchain.batch_temperature', 'coldchain.batch_quantity',
    'coldchain.batch_expiry', 'coldchain.operation_resource',
    'coldchain.operation_order_scope',
)
# Only asserted when the operation comes from the recorded PostgreSQL
# resource/operation standard (older scenario aliases use 'dock', 'loading').
PG_RESOURCE_KINDS = {
    'pick': frozenset({'cold_room', 'pre_cooler'}),
    'stage': frozenset({'pre_cooler', 'cold_room'}),
    'load': frozenset({'loading_dock'}),
}


def _dt(value: Any) -> datetime:
    if isinstance(value, datetime):
        return value
    return datetime.fromisoformat(str(value).replace('Z', '+00:00'))


def validate_cold_chain(snapshot: Mapping[str, Any], order_ids: Sequence[str],
                        delivered_at_s: Mapping[str, int] | None = None) -> dict[str, Any]:
    """Return explicit failed/partial/passed rules for selected orders only.

    Validates known *snapshot* facts, not a live enterprise ledger. Unknown
    reservation/quarantine balances are always identified for PG R27 snapshots.
    """
    violations: list[dict[str, Any]] = []
    not_checked: list[str] = []
    order_map = {o['order_id']: o for o in snapshot.get('orders', ())}
    selected = set(order_ids)
    lots_rows = list(snapshot.get('stock_lots', ()))
    lots = {lot['batch_id']: lot for lot in lots_rows}
    resources = {r['resource_id']: r for r in snapshot.get('resources', ())}
    pg_verified = snapshot.get('rule_version') == 'pg-r27-verified'

    def fail(rule: str, objects: Sequence[str], reason: str) -> None:
        violations.append({'rule_id': rule, 'object_ids': list(objects), 'message': reason})

    unknown = selected - order_map.keys()
    for oid in sorted(unknown):
        fail('coldchain.operation_order_scope', [oid], 'selected order absent from snapshot')
    demand = defaultdict(int)
    earliest_delivery = defaultdict(list)
    for oid in sorted(selected & order_map.keys()):
        order = order_map[oid]
        batch_id = order['batch_id']
        lot = lots.get(batch_id)
        if lot is None:
            if lots_rows or pg_verified:
                fail('coldchain.batch_exists', [oid, batch_id], 'order refers to unavailable batch')
            elif 'coldchain.stock_lots_absent' not in not_checked:
                not_checked.append('coldchain.stock_lots_absent')
            continue
        if lot['warehouse_id'] != order['warehouse_id']:
            fail('coldchain.batch_warehouse', [oid, batch_id], 'stock batch belongs to another warehouse')
        if lot['temperature_zone'] != order['temperature_zone']:
            fail('coldchain.batch_temperature', [oid, batch_id], 'stock batch temperature is incompatible')
        demand[batch_id] += int(order['quantity_units'])
        # A freshness deadline is a latest allowed time, not an assertion
        # that delivery actually happens then. Use the real delivery completion
        # when known; pre-solve can only prove expiry when even the earliest
        # customer service window is already beyond the lot expiry.
        compare_at = (delivered_at_s[oid] if delivered_at_s is not None and oid in delivered_at_s
                      else int(order['service_window']['start_s']))
        earliest_delivery[batch_id].append(int(compare_at))

    for batch_id, requested in sorted(demand.items()):
        lot = lots[batch_id]
        on_hand = int(lot['on_hand_units'])
        reserved = int(lot['reserved_units'])
        quarantined = int(lot['quarantined_units'])
        if pg_verified:
            # R24 persisted lot count but not live reserve/quarantine balances.
            # Never claim authoritative free stock by subtracting default zero.
            if 'coldchain.pg_live_reservation_and_quarantine_unknown' not in not_checked:
                not_checked.append('coldchain.pg_live_reservation_and_quarantine_unknown')
            if requested > on_hand:
                fail('coldchain.batch_quantity', [batch_id], 'selected demand exceeds recorded on-hand stock')
        elif requested > max(0, on_hand - reserved - quarantined):
            fail('coldchain.batch_quantity', [batch_id], 'selected demand exceeds snapshot available stock')
        try:
            expiry = _dt(lot['expires_at'])
            origin = _dt(snapshot['origin_at'])
            expiry_target = origin + timedelta(seconds=max(earliest_delivery[batch_id]))
            if expiry < expiry_target:
                fail('coldchain.batch_expiry', [batch_id], 'batch expires before known or earliest possible delivery completion')
        except (ValueError, TypeError, KeyError, OverflowError):
            if 'coldchain.expiry_not_verifiable' not in not_checked:
                not_checked.append('coldchain.expiry_not_verifiable')

    for op in snapshot.get('operations', ()):
        if op.get('order_ids') and not selected.intersection(op['order_ids']):
            continue
        if pg_verified:
            resource = resources.get(op['resource_id'])
            kinds = PG_RESOURCE_KINDS.get(op['operation_kind'])
            if resource is None or kinds is None or resource['resource_kind'] not in kinds or resource['warehouse_id'] != op['warehouse_id']:
                fail('coldchain.operation_resource', [op['operation_id']], 'recorded task/resource kind or warehouse mismatch')
        for oid in op.get('order_ids', ()):
            if oid in selected and order_map.get(oid, {}).get('warehouse_id') != op['warehouse_id']:
                fail('coldchain.operation_order_scope', [op['operation_id'], oid], 'operation and order warehouses differ')

    # These contracts do NOT prove storage occupancy, pre-cooling or product
    # changeover; list them even in scenarios where all current rules passed.
    not_checked.extend(('coldchain.time_dependent_room_capacity',
                        'coldchain.precooling_and_cleaning_changeover'))
    return {
        'status': 'failed' if violations else 'partial' if not_checked else 'passed',
        'checked_rule_ids': list(RULES),
        'violations': violations,
        'not_checked_rule_ids': not_checked,
        'source_kind': 'postgresql_recorded_snapshot' if pg_verified else 'declared_snapshot',
        'read_only': True,
    }
