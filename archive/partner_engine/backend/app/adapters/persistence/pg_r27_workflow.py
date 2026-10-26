"""R27 single-depot CP-SAT -> OR-Tools dry-run planning and deterministic event replay.

Verified mode strictly consumes explicitly recorded PostgreSQL operation standards.
No synthetic durations, fake stock reservations, commits, or silent fallback.
"""
from __future__ import annotations

from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
import json

from app.adapters.persistence.pg_routing_preview import (
    BridgeInputError, _datetime, _id, _pos_int, _seconds, prepare_preview,
)
from app.contracts.common import TimeWindow, Source
from app.contracts.entities import Operation, PlanningSnapshot, WarehouseResource, StockLot

R27_TABLE = 'pg_r27_work_operations'
ROOT = Path(__file__).resolve().parents[4]


def load_r27(conn) -> dict:
    found = conn.execute("""SELECT tablename FROM pg_catalog.pg_tables
        WHERE schemaname='public' AND tablename=%s""", (R27_TABLE,)).fetchall()
    if not found:
        return {'installed': False, 'operations': []}
    operations = conn.execute("""SELECT x.operation_code, o.code AS order_code,
        w.code AS warehouse_code, x.resource_code, x.operation_kind,
        x.duration_s, x.release_at, x.deadline_at, x.predecessor_code,
        x.version, x.observed_at
        FROM public.pg_r27_work_operations x
        JOIN public.delivery_orders o ON o.id=x.order_id
        JOIN public.warehouses w ON w.id=x.warehouse_id
        ORDER BY x.operation_code""").fetchall()
    return {'installed': True, 'operations': operations}


def readiness(data: dict) -> dict:
    r24 = data.get('r24')
    r27 = data.get('r27', {'installed': False, 'operations': []})
    warehouses = sorted({n['node_key'][3:] for n in data['nodes'] if n['node_key'].startswith('WH:')})
    single = warehouses == ['WH001'] and all(v['warehouse_code'] == 'WH001' for v in data['vehicles'])
    order_codes = {x['order_code'] for x in data['orders']}
    vehicle_codes = {x['vehicle_code'] for x in data['vehicles']}
    missing = {
        'order_details': sorted(order_codes - {x['order_code'] for x in (r24 or {}).get('orders', [])}),
        'vehicle_details': sorted(vehicle_codes - {x['vehicle_code'] for x in (r24 or {}).get('vehicles', [])}),
        'dock_handoffs': sorted(order_codes - {x['order_code'] for x in (r24 or {}).get('handoffs', [])}),
        'work_operations': sorted(order_codes - {x['order_code'] for x in r27['operations']}),
        'loading_operations': sorted(order_codes - {x['order_code'] for x in r27['operations'] if x['operation_kind'] == 'load'}),
    }
    r24_populated = bool(r24 and r24['zones'] and r24['lots'] and r24['resources'])
    return {
        'mode': 'pg_r27_verified_readonly', 'database_mutated': False,
        'single_warehouse': single, 'warehouse_codes': warehouses,
        'r24_tables_installed': r24 is not None, 'r27_table_installed': r27['installed'],
        'r24_reference_data_present': r24_populated,
        'missing': {key: len(value) for key, value in missing.items()},
        'missing_codes': missing, 'work_operation_count': len(r27['operations']),
        'complete_presence': bool(single and r24_populated and r27['installed']
                                  and not any(missing.values())),
        'provenance': data.get('r30a', {'installed': False, 'source_kind': 'unmarked_operator_or_legacy_rows'}),
        'note': 'presence_only; run_workflow_rechecks_all_business_and_precedence_rules',
    }


def demo_snapshot() -> PlanningSnapshot:
    path = ROOT / 'data' / 'scenarios' / 'single_warehouse_20_orders.json'
    return PlanningSnapshot.model_validate(json.loads(path.read_text(encoding='utf-8')))


def _time_window(start: datetime, end: datetime, origin: datetime, key: str) -> TimeWindow:
    left = _seconds(start, origin, key + '_start')
    right = _seconds(end, origin, key + '_end')
    if right <= left:
        raise BridgeInputError(key + ':invalid_time_window')
    return TimeWindow(start_s=left, end_s=right)


def verified_snapshot(data: dict, *, temperature_zone: str, travel_mode: str,
                      speed_kmh: int, max_orders: int, budget_ms: int,
                      road_provider=None) -> tuple[PlanningSnapshot, dict]:
    """Build an R20 snapshot from PG source rows; never accept client-created operations."""
    if not readiness(data)['single_warehouse']:
        raise BridgeInputError('r27_single_warehouse_required_run_r26_preflight_first')
    provenance = data.get('r30a', {})
    if provenance.get('source_kind') == 'explicit_synthetic_demo' and provenance.get('base_digest_sha256'):
        from tools.pg_r30a_bundle import base_fingerprint
        if base_fingerprint(data) != provenance['base_digest_sha256']:
            raise BridgeInputError('r30a_base_business_data_changed_since_demo_generation')
    if not data.get('r27', {}).get('installed'):
        raise BridgeInputError('r27_operations_table_not_installed')
    if not readiness(data)['complete_presence']:
        raise BridgeInputError('r27_business_metadata_incomplete_readiness_has_missing_codes')
    req, meta = prepare_preview(data, warehouse_code='WH001', temperature_zone=temperature_zone,
        travel_mode=travel_mode, speed_kmh=speed_kmh, max_orders=max_orders,
        budget_ms=budget_ms, business_mode='verified_r24', road_provider=road_provider)
    initial = req.snapshot
    selected = {o.order_id: o for o in initial.orders}
    r24 = data['r24']
    r27_rows = [row for row in data['r27']['operations'] if _id('ord', row['order_code']) in selected]
    if not r27_rows:
        raise BridgeInputError('r27_no_work_operations_selected')
    rows_by_order = {}
    by_code = {}
    for row in r27_rows:
        oid = _id('ord', row['order_code'])
        rows_by_order.setdefault(oid, []).append(row)
        code = _id('op', row['operation_code'])
        if code in by_code:
            raise BridgeInputError('r27_duplicate_operation_code')
        by_code[code] = row
        if row['warehouse_code'] != 'WH001':
            raise BridgeInputError('r27_operation_wrong_warehouse:' + row['operation_code'])
    for order in initial.orders:
        tasks = rows_by_order.get(order.order_id, [])
        if not tasks or not any(x['operation_kind'] == 'load' for x in tasks):
            raise BridgeInputError('r27_missing_pick_or_loading_work:' + order.order_id)
    resources_by_code = {}
    for row in r24['resources']:
        if row['warehouse_code'] == 'WH001' and row['temperature_zone'] == temperature_zone:
            resources_by_code[row['resource_code']] = row
    used_codes = {row['resource_code'] for row in r27_rows}
    for row in r27_rows:
        resource = resources_by_code.get(row['resource_code'])
        if resource is None:
            raise BridgeInputError('r27_resource_missing_or_wrong_zone:' + row['operation_code'])
        kinds = {'pick': ('cold_room', 'pre_cooler'), 'stage': ('pre_cooler', 'cold_room'), 'load': ('loading_dock',)}
        if resource['resource_kind'] not in kinds[row['operation_kind']]:
            raise BridgeInputError('r27_resource_kind_mismatch:' + row['operation_code'])
        predecessor = row['predecessor_code']
        if predecessor:
            parent = by_code.get(_id('op', predecessor))
            if parent is None or parent['order_code'] != row['order_code']:
                raise BridgeInputError('r27_predecessor_missing_or_cross_order:' + row['operation_code'])
    for order in initial.orders:
        tasks = rows_by_order[order.order_id]
        loads = [row for row in tasks if row['operation_kind'] == 'load']
        if len(loads) != 1:
            raise BridgeInputError('r27_one_loading_operation_per_order_required:' + order.order_id)
        # Loading is the final step. Otherwise a "ready" handoff could precede the real pick.
        loaded_code = loads[0]['operation_code']
        if any(row['operation_code'] != loaded_code and not _ancestor_of(row['operation_code'], loaded_code, by_code)
               for row in tasks):
            raise BridgeInputError('r27_loading_must_follow_all_order_work:' + order.order_id)
    source_origin = initial.origin_at
    # Shift the already validated route request's timeline if real work starts before deliveries.
    earliest = [source_origin]
    for row in r27_rows:
        earliest.append(_datetime(row['release_at'], 'release_at'))
    for code in used_codes:
        earliest.append(_datetime(resources_by_code[code]['available_from'], 'resource_available_from'))
    origin = min(earliest)
    shift = _seconds(source_origin, origin, 'original_snapshot_origin')
    synthetic = data.get('r30a', {}).get('source_kind') == 'explicit_synthetic_demo'
    recorded = Source(source_kind='simulation' if synthetic else 'database',
        source_ref=('r30a-explicit-synthetic-pg-demo' if synthetic else 'r27-postgresql-operator-records'),
        observed_at=datetime.now(timezone.utc), rule_version='pg-r30a-provenance' if synthetic else 'pg-r27-verified')
    shifted_orders = tuple(o.model_copy(update={
        'source': recorded,
        'service_window': TimeWindow(start_s=o.service_window.start_s + shift, end_s=o.service_window.end_s + shift),
        'freshness_deadline_s': o.freshness_deadline_s + shift,
    }) for o in initial.orders)
    shifted_vehicles = tuple(v.model_copy(update={
        'source': recorded,
        'shift_window': TimeWindow(start_s=v.shift_window.start_s + shift, end_s=v.shift_window.end_s + shift),
        'available_at_s': v.available_at_s + shift,
    }) for v in initial.vehicles)
    resources = []
    for code in sorted(used_codes):
        row = resources_by_code[code]
        window = _time_window(_datetime(row['available_from'], 'resource_available_from'),
                              _datetime(row['available_until'], 'resource_available_until'), origin,
                              'resource:' + code)
        resources.append(WarehouseResource(resource_id=_id('res', code), warehouse_id='wh_WH001',
            version=_pos_int(row['version'], 'resource_version'), resource_kind=row['resource_kind'],
            capacity_units=_pos_int(row['capacity_units'], 'capacity_units'), available_windows=(window,)))
    operations = []
    loading_windows = { _id('ord', x['order_code']): x for x in r24['handoffs'] }
    for oid, tasks in rows_by_order.items():
        for row in tasks:
            start = _datetime(row['release_at'], 'release_at')
            finish = _datetime(row['deadline_at'], 'deadline_at')
            work = _time_window(start, finish, origin, 'operation:' + row['operation_code'])
            cutoff = loading_windows[oid]
            if finish > _datetime(cutoff['loading_window_end'], 'loading_window_end'):
                raise BridgeInputError('r27_operation_after_loading_window:' + row['operation_code'])
            duration = _pos_int(row['duration_s'], 'duration_s')
            if duration > work.end_s - work.start_s:
                raise BridgeInputError('r27_operation_longer_than_window:' + row['operation_code'])
            operations.append(Operation(operation_id=_id('op', row['operation_code']), order_ids=(oid,),
                warehouse_id='wh_WH001', resource_id=_id('res', row['resource_code']),
                operation_kind=row['operation_kind'], duration_s=duration,
                release_at_s=work.start_s, deadline_at_s=work.end_s,
                predecessor_ids=(_id('op', row['predecessor_code']),) if row['predecessor_code'] else (),
                status='pending'))
    # R30-B requires the batch/expiry/zone facts validated by the R24 bridge.
    # R24 has no separate reserved/quarantined quantity fields: zero below is
    # NOT evidence of free-to-pick stock; this remains an operator snapshot,
    # never a live stock ledger or a mutation of on-hand inventory.
    used_batches = {o.batch_id for o in shifted_orders}
    stock_lots = tuple(StockLot(
        batch_id=_id('bat', row['lot_code']), warehouse_id=_id('wh', row['warehouse_code']),
        version=_pos_int(row.get('version', 1), 'lot_version'),
        temperature_zone=row['temperature_zone'],
        on_hand_units=_pos_int(row['quantity_units'], 'lot_quantity_units'),
        reserved_units=0, quarantined_units=0,
        expires_at=_datetime(row['best_before_at'], 'best_before_at'),
    ) for row in r24['lots'] if _id('bat', row['lot_code']) in used_batches)
    snapshot = initial.model_copy(update={
        'origin_at': origin, 'rule_version': 'pg-r27-verified',
        'orders': shifted_orders, 'vehicles': shifted_vehicles,
        'resources': tuple(resources), 'stock_lots': stock_lots,
        'operations': tuple(operations),
    })
    built = PlanningSnapshot.model_validate(snapshot.model_dump(mode='python'))
    from app.domain.cold_chain_rules import validate_cold_chain
    audit = validate_cold_chain(built.model_dump(mode='python'), [o.order_id for o in built.orders])
    if audit['violations']:
        raise BridgeInputError('r30d_pg_warehouse_business_invalid:' + ';'.join(
            item['rule_id'] for item in audit['violations'][:8]))
    return built, meta


def _ancestor_of(code: str, descendant: str, by_code: dict) -> bool:
    visited = set()
    cursor = descendant
    while True:
        if cursor in visited:
            raise BridgeInputError('r27_operation_precedence_cycle')
        visited.add(cursor)
        row = by_code.get(_id('op', cursor))
        if row is None or not row['predecessor_code']:
            return False
        cursor = row['predecessor_code']
        if cursor == code:
            return True


def build_events(snapshot: PlanningSnapshot, plan) -> list[dict]:
    """Deterministic read-only replay projection from validated solver timestamps."""
    if plan.validation.status != 'passed':
        raise BridgeInputError('r27_unvalidated_plan_must_not_be_replayed')
    operations = {o.operation_id: o for o in snapshot.operations}
    orders = {o.order_id: o for o in snapshot.orders}
    events: list[dict] = []
    def add(t: int, kind: str, item: str, **details):
        events.append({'time_s': t, 'kind': kind, 'object_id': item, **details})
    for work in plan.warehouse.operations:
        source = operations[work.operation_id]
        add(work.start_s, 'warehouse_work_start', work.operation_id,
            resource_id=work.resource_id, order_ids=list(source.order_ids), operation_kind=source.operation_kind)
        add(work.end_s, 'warehouse_work_finished', work.operation_id,
            resource_id=work.resource_id, order_ids=list(source.order_ids), operation_kind=source.operation_kind)
    for handoff in plan.warehouse.warehouse_handoffs:
        add(handoff.ready_at_s, 'loading_ready', handoff.order_id, warehouse_id=handoff.warehouse_id)
    for route in plan.routing.routes:
        if not route.stops:
            continue
        add(route.stops[0].departure_at_s, 'vehicle_departure', route.vehicle_id,
            order_ids=[oid for s in route.stops for oid in s.order_ids], warehouse_id=orders[route.stops[1].order_ids[0]].warehouse_id
            if len(route.stops) > 2 and route.stops[1].order_ids else None)
        for stop in route.stops:
            if stop.stop_kind == 'delivery':
                for oid in stop.order_ids:
                    add(stop.departure_at_s, 'order_delivered', oid, vehicle_id=route.vehicle_id)
        add(route.stops[-1].arrival_at_s, 'vehicle_return', route.vehicle_id)
    priority = {'warehouse_work_start':0, 'warehouse_work_finished':1, 'loading_ready':2,
                'vehicle_departure':3, 'order_delivered':4, 'vehicle_return':5}
    events.sort(key=lambda x: (x['time_s'], priority[x['kind']], x['object_id']))
    return events


def execute(snapshot: PlanningSnapshot, *, budget_ms: int = 60000,
            source: str = 'scenario_demo', extra: dict | None = None) -> dict:
    from app.application.coordinator import coordinate
    from app.domain.plan_rules import validate_plan
    if len(snapshot.warehouses) != 1:
        raise BridgeInputError('r27_requires_single_warehouse_snapshot')
    ids = tuple(o.order_id for o in snapshot.orders)
    from app.domain.cold_chain_rules import validate_cold_chain
    cold_chain_audit = validate_cold_chain(snapshot.model_dump(mode='python'), ids)
    if cold_chain_audit['violations']:
        raise BridgeInputError('r30d_coldchain_precheck_failed:' + ';'.join(
            x['rule_id'] for x in cold_chain_audit['violations'][:8]))
    plan = coordinate(snapshot=snapshot, order_ids=ids, budget_ms=budget_ms,
                      max_coordination_rounds=1, coordination_mode='sequential')
    if plan.validation.status != 'passed':
        raise BridgeInputError('r27_cross_domain_plan_validation_failed')
    delivery_finished = {oid: stop.departure_at_s
        for route in plan.routing.routes for stop in route.stops
        if stop.stop_kind == 'delivery' for oid in stop.order_ids}
    cold_chain_delivery_audit = validate_cold_chain(
        snapshot.model_dump(mode='python'), ids, delivered_at_s=delivery_finished)
    if cold_chain_delivery_audit['violations']:
        raise BridgeInputError('r30d_actual_delivery_coldchain_violation:' + ';'.join(
            issue['rule_id'] for issue in cold_chain_delivery_audit['violations'][:8]))
    issues = validate_plan(snapshot=snapshot.model_dump(mode='python'), order_ids=ids,
        warehouse=plan.warehouse.model_dump(mode='python'), routing=plan.routing.model_dump(mode='python'))
    if issues:
        raise BridgeInputError('r27_cross_domain_violations:' + ';'.join(x['rule_id'] for x in issues))
    if source == 'verified_postgres':
        handoffs = {h.order_id: h for h in plan.warehouse.warehouse_handoffs}
        ops = {o.order_id: o for o in snapshot.orders}
        limits = (extra or {}).get('handoff_limits', {})
        for route in plan.routing.routes:
            if not route.stops: continue
            departure = route.stops[0].departure_at_s
            for stop in route.stops:
                for oid in stop.order_ids:
                    if oid not in ops: continue
                    limit = limits.get(oid)
                    if limit is not None and (handoffs[oid].ready_at_s > limit or departure > limit):
                        raise BridgeInputError('r27_loading_window_violated:' + oid)
    from app.adapters.persistence.pg_r28_reconciliation import reconcile
    events = build_events(snapshot, plan)
    reconciliation = reconcile(snapshot, plan, events)
    return {'mode': 'r28_reconciled_dry_run_not_executable', 'source': source, 'database_mutated': False,
            'business_plans_mutated': False, 'validated': True,
            'snapshot': snapshot.model_dump(mode='json'), 'plan': plan.model_dump(mode='json'),
            'events': events, 'reconciliation': reconciliation,
            'cold_chain_audit': cold_chain_delivery_audit,
            'meta': {k:v for k,v in (extra or {}).items() if k != 'handoff_limits'},
            'note': 'solver_results_not_device_telemetry; warehouse_paths_and_racks_are_visual_only'}
