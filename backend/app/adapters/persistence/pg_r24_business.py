"""R24 metadata loaded only after an explicit additive migration.

Read-only projection. No NULL coalescing to artificial business values.
"""
from __future__ import annotations

from app.adapters.persistence.pg_routing_preview import BridgeInputError

TABLES = ('pg_r24_warehouse_zones', 'pg_r24_stock_lots', 'pg_r24_order_details',
          'pg_r24_vehicle_details', 'pg_r24_resources', 'pg_r24_dock_operations')


def load_r24(conn) -> dict:
    tables = conn.execute("""SELECT tablename FROM pg_catalog.pg_tables
        WHERE schemaname='public' AND tablename = ANY(%s)""", (list(TABLES),)).fetchall()
    found = {r['tablename'] for r in tables}
    if found != set(TABLES):
        raise BridgeInputError('r24_tables_missing_run_explicit_migration_first')
    def select(query):
        return conn.execute(query).fetchall()
    return {
        'zones': select('''SELECT w.code AS warehouse_code, z.temperature_zone, z.capacity_volume_l
            FROM public.pg_r24_warehouse_zones z JOIN public.warehouses w ON w.id=z.warehouse_id'''),
        'lots': select('''SELECT l.lot_code, w.code AS warehouse_code, l.temperature_zone,
            l.quantity_units, l.best_before_at, l.observed_at, l.version
            FROM public.pg_r24_stock_lots l JOIN public.warehouses w ON w.id=l.warehouse_id'''),
        'orders': select('''SELECT d.code AS order_code, w.code AS warehouse_code, x.lot_code,
            x.quantity_units, x.volume_l, x.freshness_deadline, x.temperature_zone, x.version, x.observed_at
            FROM public.pg_r24_order_details x JOIN public.delivery_orders d ON d.id=x.order_id
            JOIN public.warehouses w ON w.id=x.warehouse_id'''),
        'vehicles': select('''SELECT v.code AS vehicle_code, x.capacity_volume_l,
            x.remaining_weight_kg, x.remaining_volume_l, x.temperature_zone,
            x.shift_start, x.shift_end, x.available_at, x.current_node_key,
            x.version, x.observed_at FROM public.pg_r24_vehicle_details x
            JOIN public.vehicles v ON v.id=x.vehicle_id'''),
        'resources': select('''SELECT w.code AS warehouse_code, r.resource_code, r.resource_kind,
             r.temperature_zone, r.capacity_units, r.available_from, r.available_until, r.version
             FROM public.pg_r24_resources r JOIN public.warehouses w ON w.id=r.warehouse_id'''),
        'handoffs': select('''SELECT d.code AS order_code, w.code AS warehouse_code,
            x.ready_at, x.loading_window_end, x.operation_status, x.resource_code,
            x.version, x.observed_at FROM public.pg_r24_dock_operations x
            JOIN public.delivery_orders d ON d.id=x.order_id
            JOIN public.warehouses w ON w.id=x.warehouse_id'''),
    }


def readiness(data: dict) -> dict:
    meta = data.get('r24')
    if meta is None:
        return {'mode': 'r24_business_metadata', 'tables_installed': False,
                'complete': False, 'message': 'run_R24_explicit_additive_migration'}
    orders = {x['order_code'] for x in data['orders']}
    vehicles = {x['vehicle_code'] for x in data['vehicles']}
    fields = {'order_details': {x['order_code'] for x in meta['orders']},
              'vehicle_details': {x['vehicle_code'] for x in meta['vehicles']},
              'handoffs': {x['order_code'] for x in meta['handoffs']}}
    missing = {
        'orders_without_r24_details': len(orders - fields['order_details']),
        'vehicles_without_r24_details': len(vehicles - fields['vehicle_details']),
        'orders_without_dock_handoffs': len(orders - fields['handoffs']),
    }
    return {'mode': 'r24_business_metadata', 'tables_installed': True,
            'provenance': data.get('r30a', {'source_kind': 'unmarked_operator_or_legacy_rows'}),
            'complete': not any(missing.values()) and bool(meta['zones']) and bool(meta['lots']) and bool(meta['resources']),
            'counts': {key: len(items) for key, items in meta.items()},
            'missing': missing, 'note': 'counts_and_presence_only_not_semantic_validation;no_auto_seed'}
