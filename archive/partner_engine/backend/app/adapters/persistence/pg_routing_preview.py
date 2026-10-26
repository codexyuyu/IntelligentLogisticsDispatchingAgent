"""AC: read existing PostgreSQL views and preview with the REAL R20 RoutingSolver.

This is an opt-in, non-executable SIMULATION adapter, not a PlanningSnapshotStore.
Unsupported business facts are visible assumptions, never persisted or declared real.
"""
from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from math import ceil
from os import environ
import re

from app.contracts.common import Source, TimeWindow, SolveBudget
from app.contracts.entities import Order, Vehicle, Warehouse, TravelMatrix, PlanningSnapshot
from app.contracts.planning import RoutingRequest, WarehouseHandoff
from app.domain.transport_rules import validate_transport


ASSUMPTIONS = (
    "演示模式，不是正式仓运联合调度，不能确认或写入数据库",
    "订单所属仓库按 PostGIS 直线距离选择最近仓库，不是原业务分仓",
    "没有道路时长：用直线距离与用户指定的假设速度估算行驶秒数，非真实路程/ETA",
    "没有体积字段：假设 1 kg 对应 1 L；车辆假设等量的容积容量，仅用于求解演示",
    "没有库存/装车作业：假设所有货物在快照起点已就绪、装车窗口覆盖整个演示期",
    "没有真实班次/实时位置：假设车辆在所属仓库未发车，演示班次覆盖订单窗口和缓冲期",
    "无独立保鲜截止：暂以服务窗口末端+卸货服务时长作为模拟截止",
    "温区仅以明确数值边界分组；单趟同车只承载一个温区，车辆须覆盖选中订单的完整温度范围",
    "分批/件数/版本/来源缺失字段为模拟占位，不是生产业务事实",
    "每次只独立预览一个仓库的一个温区；不同预览之间车辆可能重复，不能合并成正式计划",
)


class BridgeInputError(ValueError):
    """Input cannot safely be converted into an explicit routing simulation."""


def _id(prefix: str, key: object) -> str:
    raw = str(key)
    if not re.fullmatch(r"[A-Za-z0-9_-]{1,55}", raw):
        raise BridgeInputError(f"unsupported_code_for_contract:{prefix}")
    return f"{prefix}_{raw}"


def _pos_int(raw: object, key: str) -> int:
    try:
        num = Decimal(str(raw))
        if not num.is_finite() or num <= 0 or num != num.to_integral_value():
            raise ValueError()
        return int(num)
    except (ValueError, TypeError, ArithmeticError):
        raise BridgeInputError(f"{key}:must_be_positive_whole_number") from None


def _distance_int(raw: object) -> int:
    try:
        value = Decimal(str(raw))
        if not value.is_finite() or value < 0:
            raise ValueError()
        return int(value.to_integral_value(rounding='ROUND_HALF_UP'))
    except (ValueError, TypeError, ArithmeticError):
        raise BridgeInputError('invalid_distance_m') from None


def _datetime(raw: object, field: str) -> datetime:
    try:
        dt = raw if isinstance(raw, datetime) else datetime.fromisoformat(str(raw))
        if dt.tzinfo is None or dt.utcoffset() is None:
            raise ValueError()
        return dt.astimezone(timezone.utc)
    except (TypeError, ValueError):
        raise BridgeInputError(f"{field}:must_have_timezone") from None


def _seconds(dt: datetime, origin: datetime, field: str) -> int:
    n = (dt - origin).total_seconds()
    if n < 0 or not n.is_integer():
        raise BridgeInputError(f"{field}:requires_nonnegative_integral_seconds")
    return int(n)


def _temp_zone(row: dict, *, item: str) -> str:
    minimum = Decimal(str(row['min_temp_c']))
    maximum = Decimal(str(row['max_temp_c']))
    if not minimum.is_finite() or not maximum.is_finite() or minimum > maximum:
        raise BridgeInputError(f"{item}:invalid_temperature")
    if maximum < 0:
        return 'frozen'
    if minimum >= 0:
        return 'chilled'
    raise BridgeInputError(f"{item}:cross_zero_temperature_needs_manual_policy")


def _serialize(value):
    """JSON-safe view projection; decimals are exact strings, never floats."""
    if isinstance(value, (Decimal, datetime)):
        return value.isoformat() if isinstance(value, datetime) else str(value)
    if isinstance(value, dict):
        return {k: _serialize(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_serialize(v) for v in value]
    return value


def load_view_data(connection_factory=None, *, include_r24=False, include_r27=False) -> dict:
    """Single repeatable-read, read-only transaction; does not use any write SQL."""
    if connection_factory is None:
        if not environ.get('PGPASSWORD'):
            raise BridgeInputError('PGPASSWORD_not_configured')
        try:
            import psycopg
            from psycopg.rows import dict_row
        except ImportError as exc:
            raise RuntimeError('psycopg_not_installed') from exc
        def connection_factory():
            return psycopg.connect(
                host=environ.get('PGHOST', '127.0.0.1'),
                port=int(environ.get('PGPORT', '5432')),
                dbname=environ.get('PGDATABASE', 'coldchain_db'),
                user=environ.get('PGUSER', 'postgres'),
                password=environ['PGPASSWORD'],
                connect_timeout=8,
                row_factory=dict_row,
            )
    with connection_factory() as conn:
        conn.execute('SET TRANSACTION ISOLATION LEVEL REPEATABLE READ, READ ONLY')
        orders = conn.execute('''SELECT order_code, customer_code, weight_kg,
                        min_temp_c, max_temp_c, window_start, window_end, service_minutes
                        FROM v_dispatch_orders ORDER BY order_code''').fetchall()
        vehicles = conn.execute('''SELECT vehicle_code, warehouse_code, capacity_kg,
                        min_temp_c, max_temp_c FROM v_dispatch_vehicles ORDER BY vehicle_code''').fetchall()
        nodes = conn.execute('''SELECT node_key, node_type, node_name, longitude, latitude
                        FROM v_dispatch_nodes ORDER BY node_key''').fetchall()
        distances = conn.execute('''SELECT from_node, to_node, distance_m
                        FROM v_dispatch_distance_matrix ORDER BY from_node, to_node''').fetchall()
        # R29: WH002 may remain physically for untouched historical routes.
        # Only *new* planning input excludes a consciously retired depot.
        # No view DDL and no mutations to archived plans or routes.
        retired_depot = None
        marker_exists = conn.execute("""SELECT 1 FROM pg_catalog.pg_tables
            WHERE schemaname='public' AND tablename='pg_r29_retired_warehouses'""").fetchone()
        if marker_exists:
            retirement = conn.execute("""SELECT w.code AS retired_code, a.code AS active_code
               FROM public.pg_r29_retired_warehouses r
               JOIN public.warehouses w ON w.id=r.warehouse_id
               JOIN public.warehouses a ON a.id=r.active_warehouse_id""").fetchall()
            if retirement:
                if len(retirement) != 1 or retirement[0]['retired_code'] != 'WH002' or retirement[0]['active_code'] != 'WH001':
                    raise BridgeInputError('r29_retired_warehouse_marker_inconsistent')
                retired_depot = retirement[0]['retired_code']
                if any(row['warehouse_code'] != 'WH001' for row in vehicles):
                    raise BridgeInputError('r29_retired_warehouse_vehicle_state_inconsistent')
                retired_node = 'WH:' + retired_depot
                if not any(n['node_key'] == retired_node for n in nodes):
                    raise BridgeInputError('r29_retired_warehouse_node_missing')
                nodes = [n for n in nodes if n['node_key'] != retired_node]
                distances = [d for d in distances if d['from_node'] != retired_node
                             and d['to_node'] != retired_node]
        if include_r24 or include_r27:
            from app.adapters.persistence.pg_r24_business import load_r24
            try:
                r24 = load_r24(conn)
            except BridgeInputError:
                if not include_r27:
                    raise
                r24 = None
        if include_r27:
            from app.adapters.persistence.pg_r27_workflow import load_r27
            r27 = load_r27(conn)
            from app.adapters.persistence.pg_r30a_provenance import load_provenance
            r30a = load_provenance(conn)
    result = {'orders': orders, 'vehicles': vehicles, 'nodes': nodes, 'distance_matrix': distances}
    if retired_depot:
        result['r29_active_depot'] = {'active_warehouses': ['WH001'],
                                      'retired_historical_fk_warehouse': retired_depot,
                                      'physical_historical_warehouse_retained': True}
    if include_r24 or include_r27:
        result['r24'] = r24
    if include_r27:
        result['r27'] = r27
        result['r30a'] = r30a
    return result


def public_rows(data: dict, section: str, limit: int = 100) -> dict:
    if section not in ('orders', 'vehicles'):
        raise BridgeInputError('unsupported_section')
    rows = data[section]
    return {'mode': 'database_readonly', 'count': len(rows), 'rows': _serialize(rows[:limit])}


def _distance_lookup(data: dict):
    nodes = [x['node_key'] for x in data['nodes']]
    if len(nodes) != len(set(nodes)) or not nodes:
        raise BridgeInputError('invalid_nodes')
    keys = set(nodes)
    distances = {}
    for item in data['distance_matrix']:
        key = (item['from_node'], item['to_node'])
        if key in distances or key[0] not in keys or key[1] not in keys:
            raise BridgeInputError('invalid_distance_pairs')
        distances[key] = _distance_int(item['distance_m'])
    if len(distances) != len(keys) ** 2:
        raise BridgeInputError('distance_matrix_incomplete')
    if any(distances[n, n] != 0 for n in nodes):
        raise BridgeInputError('matrix_diagonal_not_zero')
    return distances


def prepare_preview(data: dict, *, warehouse_code: str, temperature_zone: str,
                    speed_kmh: int = 30, budget_ms: int = 5000, max_orders: int = 20,
                    travel_mode: str = 'straight_line_simulation',
                    business_mode: str = 'legacy_simulation', road_provider=None) -> tuple[RoutingRequest, dict]:
    if not 1 <= speed_kmh <= 100 or not 500 <= budget_ms <= 20000 or not 1 <= max_orders <= 20:
        raise BridgeInputError('invalid_preview_limits')
    if temperature_zone not in ('chilled', 'frozen'):
        raise BridgeInputError('invalid_temperature_zone')
    if travel_mode not in ('straight_line_simulation', 'osrm_road_estimate'):
        raise BridgeInputError('unsupported_travel_mode')
    if business_mode not in ('legacy_simulation', 'verified_r24'):
        raise BridgeInputError('unsupported_business_mode')
    verified = business_mode == 'verified_r24'
    r24 = data.get('r24') if verified else None
    if verified and r24 is None:
        raise BridgeInputError('r24_metadata_not_loaded')
    extra_orders = {row['order_code']: row for row in r24['orders']} if verified else {}
    extra_vehicles = {row['vehicle_code']: row for row in r24['vehicles']} if verified else {}
    extra_handoffs = {row['order_code']: row for row in r24['handoffs']} if verified else {}
    extra_lots = {row['lot_code']: row for row in r24['lots']} if verified else {}
    extra_resources = {(row['warehouse_code'],row['resource_code']): row for row in r24['resources']} if verified else {}
    zone_keys = {(row['warehouse_code'], row['temperature_zone']) for row in r24['zones']} if verified else set()
    warehouses = sorted({v['warehouse_code'] for v in data['vehicles']})
    if warehouse_code not in warehouses:
        raise BridgeInputError('warehouse_not_in_vehicles')
    distances = _distance_lookup(data)
    by_order = []
    omitted_zone = 0
    omitted_other_warehouse = 0
    for item in data['orders']:
        customer = 'C:' + str(item['customer_code'])
        candidate = [(distances['WH:' + wh, customer], wh) for wh in warehouses]
        nearest_wh = (extra_orders[item['order_code']]['warehouse_code']
                      if verified and item['order_code'] in extra_orders else min(candidate)[1])
        if verified and item['order_code'] not in extra_orders:
            raise BridgeInputError('r24_order_details_missing:' + item['order_code'])
        if nearest_wh != warehouse_code:
            omitted_other_warehouse += 1
            continue
        zone = _temp_zone(item, item=f"order:{item['order_code']}")
        if verified and extra_orders[item['order_code']]['temperature_zone'] != zone:
            raise BridgeInputError('r24_order_temperature_mismatch:' + item['order_code'])
        if zone != temperature_zone:
            omitted_zone += 1
            continue
        by_order.append(item)
    by_order.sort(key=lambda x: x['order_code'])
    selected = by_order[:max_orders]
    if not selected:
        raise BridgeInputError('no_orders_for_selected_warehouse_and_zone')

    # Conservative protection against R20's binary zone model: every included
    # vehicle must be able to maintain the entire numeric interval of every
    # selected order, not merely overlap with it.
    selected_vehicles = []
    for v in data['vehicles']:
        if v['warehouse_code'] != warehouse_code:
            continue
        v_min = Decimal(str(v['min_temp_c']))
        v_max = Decimal(str(v['max_temp_c']))
        if v_min > v_max:
            raise BridgeInputError('invalid_vehicle_temperature')
        if verified and v['vehicle_code'] not in extra_vehicles:
            raise BridgeInputError('r24_vehicle_details_missing:' + v['vehicle_code'])
        if verified and extra_vehicles[v['vehicle_code']]['temperature_zone'] != temperature_zone:
            continue
        if all(v_min <= Decimal(str(o['min_temp_c'])) and v_max >= Decimal(str(o['max_temp_c'])) for o in selected):
            selected_vehicles.append(v)
    if not selected_vehicles:
        raise BridgeInputError('no_vehicle_covers_all_selected_temperature_intervals')

    start_dates = [_datetime(o['window_start'], 'window_start') for o in selected]
    end_dates = [_datetime(o['window_end'], 'window_end') for o in selected]
    origin_candidates = list(start_dates)
    if verified:
        if (warehouse_code, temperature_zone) not in zone_keys:
            raise BridgeInputError('r24_warehouse_temperature_zone_missing')
        lot_demand = {}
        for raw in selected:
            detail = extra_orders[raw['order_code']]
            lot = extra_lots.get(detail['lot_code'])
            op = extra_handoffs.get(raw['order_code'])
            if not lot or not op:
                raise BridgeInputError('r24_stock_lot_or_dock_missing:' + raw['order_code'])
            resource = extra_resources.get((warehouse_code, op['resource_code']))
            if not resource or resource['resource_kind'] != 'loading_dock' or resource['temperature_zone'] != temperature_zone:
                raise BridgeInputError('r24_dock_resource_missing_or_wrong_zone')
            if not (_datetime(resource['available_from'], 'resource_from') <= _datetime(op['ready_at'], 'ready_at')
                    < _datetime(op['loading_window_end'], 'loading_window_end')
                    <= _datetime(resource['available_until'], 'resource_until')):
                raise BridgeInputError('r24_loading_window_outside_resource_availability')
            if (lot['warehouse_code'] != warehouse_code or lot['temperature_zone'] != temperature_zone
                    or op['warehouse_code'] != warehouse_code
                    or _pos_int(detail['quantity_units'], 'quantity_units') > _pos_int(lot['quantity_units'], 'lot_quantity_units')):
                raise BridgeInputError('r24_lot_dock_warehouse_or_quantity_conflict:' + raw['order_code'])
            expiry = _datetime(lot['best_before_at'], 'best_before_at')
            if (_datetime(detail['freshness_deadline'], 'freshness_deadline') > expiry
                    or _datetime(raw['window_start'], 'window_start') > expiry):
                raise BridgeInputError('r24_order_freshness_after_lot_expiry')
            lot_demand[detail['lot_code']] = lot_demand.get(detail['lot_code'], 0) + _pos_int(detail['quantity_units'], 'quantity_units')
            if lot_demand[detail['lot_code']] > _pos_int(lot['quantity_units'], 'lot_quantity_units'):
                raise BridgeInputError('r24_stock_lot_oversubscribed')
            origin_candidates.append(_datetime(op['ready_at'], 'ready_at'))
        for raw in selected_vehicles:
            vehicle = extra_vehicles[raw['vehicle_code']]
            if vehicle['current_node_key'] != 'WH:' + warehouse_code:
                raise BridgeInputError('r24_only_depot_origin_supported')
            origin_candidates.append(_datetime(vehicle['shift_start'], 'shift_start'))
            origin_candidates.append(_datetime(vehicle['available_at'], 'available_at'))
    origin = min(origin_candidates)
    last_delivery_s = max(_seconds(t, origin, 'window_end') for t in end_dates)
    # Explicit demo-only shift and handoff horizon; no operational timing claims.
    horizon = last_delivery_s + max(7200, len(selected) * 1800)
    if verified:
        horizon = max(horizon, *(_seconds(_datetime(extra_vehicles[v['vehicle_code']]['shift_end'], 'shift_end'), origin, 'shift_end') for v in selected_vehicles))
    observed = datetime.now(timezone.utc)
    data_source = Source(source_kind='simulation', source_ref='pg-readonly-with-explicit-demo-assumptions',
                         observed_at=observed, rule_version='pg-preview-r24')
    wh_id = _id('wh', warehouse_code)
    warehouse_node = _id('node', warehouse_code)
    order_objects = []
    handoffs = []
    for raw, start, end in zip(selected, start_dates, end_dates):
        oid = _id('ord', raw['order_code'])
        start_s = _seconds(start, origin, 'window_start')
        end_s = _seconds(end, origin, 'window_end')
        service_s = _pos_int(raw['service_minutes'], 'service_minutes') * 60
        if end_s <= start_s:
            raise BridgeInputError(f"invalid_service_window:{raw['order_code']}")
        weight = _pos_int(raw['weight_kg'], 'weight_kg')
        detail = extra_orders[raw['order_code']] if verified else None
        volume = _pos_int(detail['volume_l'], 'volume_l') if verified else weight
        deadline = (_seconds(_datetime(detail['freshness_deadline'], 'freshness_deadline'), origin, 'freshness_deadline')
                    if verified else end_s + service_s)
        if deadline < start_s:
            raise BridgeInputError('r24_freshness_before_delivery_window')
        order_objects.append(Order(
            order_id=oid, version=_pos_int(detail['version'], 'order_version') if verified else 1, warehouse_id=wh_id,
            batch_id=_id('bat', detail['lot_code']) if verified else _id('bat', raw['order_code']),
            delivery_node_id=_id('node', raw['customer_code']),
            quantity_units=_pos_int(detail['quantity_units'], 'quantity_units') if verified else 1,
            weight_kg=weight, volume_l=volume,
            temperature_zone=temperature_zone,
            service_window=TimeWindow(start_s=start_s, end_s=end_s),
            service_duration_s=service_s, freshness_deadline_s=deadline,
            required=True, source=data_source,
        ))
        op = extra_handoffs[raw['order_code']] if verified else None
        ready = _seconds(_datetime(op['ready_at'], 'ready_at'), origin, 'ready_at') if verified else 0
        loading_end = (_seconds(_datetime(op['loading_window_end'], 'loading_window_end'), origin, 'loading_window_end')
                       if verified else horizon)
        if ready >= loading_end:
            raise BridgeInputError('r24_invalid_loading_window')
        handoffs.append(WarehouseHandoff(order_id=oid, warehouse_id=wh_id, ready_at_s=ready,
                                        loading_window=TimeWindow(start_s=ready, end_s=loading_end)))
    vehicle_objects = []
    for raw in selected_vehicles:
        capacity = _pos_int(raw['capacity_kg'], 'capacity_kg')
        vehicle = extra_vehicles[raw['vehicle_code']] if verified else None
        capacity_volume = _pos_int(vehicle['capacity_volume_l'], 'capacity_volume_l') if verified else capacity
        remaining_weight = _pos_int(vehicle['remaining_weight_kg'], 'remaining_weight_kg') if verified else capacity
        remaining_volume = _pos_int(vehicle['remaining_volume_l'], 'remaining_volume_l') if verified else capacity
        if remaining_weight > capacity or remaining_volume > capacity_volume:
            raise BridgeInputError('r24_vehicle_remaining_exceeds_capacity')
        shift_start = _seconds(_datetime(vehicle['shift_start'], 'shift_start'), origin, 'shift_start') if verified else 0
        shift_end = _seconds(_datetime(vehicle['shift_end'], 'shift_end'), origin, 'shift_end') if verified else horizon
        available_at = _seconds(_datetime(vehicle['available_at'], 'available_at'), origin, 'available_at') if verified else 0
        vehicle_objects.append(Vehicle(
            vehicle_id=_id('veh', raw['vehicle_code']), version=_pos_int(vehicle['version'], 'vehicle_version') if verified else 1,
            warehouse_id=wh_id, start_node_id=warehouse_node, end_node_id=warehouse_node,
            current_node_id=warehouse_node, capacity_weight_kg=capacity,
            capacity_volume_l=capacity_volume, remaining_weight_kg=remaining_weight,
            remaining_volume_l=remaining_volume, temperature_zone=temperature_zone,
            shift_window=TimeWindow(start_s=shift_start, end_s=shift_end),
            available_at_s=available_at, source=data_source,
        ))
    matrix_nodes = ['WH:' + warehouse_code] + ['C:' + str(o['customer_code']) for o in selected]
    matrix_nodes = list(dict.fromkeys(matrix_nodes))
    n = len(matrix_nodes)
    distances_m = tuple(tuple(distances[a, b] for b in matrix_nodes) for a in matrix_nodes)
    if travel_mode == 'osrm_road_estimate':
        from app.adapters.matrix.osrm import road_matrix
        duration_s, distances_m = road_matrix(data['nodes'], matrix_nodes, fetch=road_provider)
    else:
        duration_s = tuple(tuple(0 if i == j else max(1, ceil(distances_m[i][j] * 3.6 / speed_kmh))
                                 for j in range(n)) for i in range(n))
    matrix = TravelMatrix(matrix_id='mat_pgpreview', version=1,
        node_ids=tuple(_id('node', key[3:] if key.startswith('WH:') else key[2:]) for key in matrix_nodes),
        duration_s=duration_s, distance_m=distances_m, source=data_source)
    snapshot = PlanningSnapshot(
        snapshot_id='snap_pgpreview', version=1, origin_at=origin, simulation_time_s=0,
        rule_version='pg-preview-1', orders=tuple(order_objects), vehicles=tuple(vehicle_objects),
        warehouses=(Warehouse(warehouse_id=wh_id, version=1, node_id=warehouse_node,
                              temperature_zones=(temperature_zone,)),),
        resources=(), stock_lots=(), operations=(), frozen_operations=(), matrix=matrix,
    )
    routing_req = RoutingRequest(snapshot=snapshot, order_ids=tuple(o.order_id for o in order_objects),
        warehouse_handoffs=tuple(handoffs),
        budget=SolveBudget(remaining_ms=budget_ms, max_workers=1, random_seed=17))
    assumptions = list(ASSUMPTIONS)
    if verified:
        assumptions = [line for line in assumptions if not any(word in line for word in
             ('所属仓库按', '没有体积字段', '没有库存/装车作业', '没有真实班次/实时位置', '无独立保鲜截止', '分批/件数/版本'))]
        assumptions.append('R24 扩展业务字段来自数据库并已通过必要校验；仍非完整仓运执行计划')
    if travel_mode == 'osrm_road_estimate':
        assumptions = [line for line in assumptions if '没有道路时长' not in line]
        assumptions.append('OSRM driving 配置下的道路估计距离与时间，不是实时交通/天气/保温损耗承诺')
    meta = {
        'mode': 'simulation_preview_not_executable', 'database_mutated': False,
        'plan_written': False, 'warehouse_code': warehouse_code,
        'temperature_zone': temperature_zone, 'read_orders': len(data['orders']),
        'read_vehicles': len(data['vehicles']), 'selected_orders': len(selected),
        'selected_vehicles': len(selected_vehicles),
        'omitted_other_temperature': omitted_zone,
        'omitted_other_warehouse_by_nearest_distance': omitted_other_warehouse,
        'omitted_due_to_limit': len(by_order) - len(selected),
        'estimated_speed_kmh': speed_kmh if travel_mode == 'straight_line_simulation' else None,
        'travel_mode': travel_mode, 'business_mode': business_mode,
        'distance_type': ('OSRM_road_network_estimate' if travel_mode == 'osrm_road_estimate'
                          else 'PostGIS_straight_line_not_driving_distance'),
        'estimated_duration_type': ('osrm_profile_estimate_not_live_traffic' if travel_mode == 'osrm_road_estimate'
                                    else 'synthetic_not_road_travel_time'),
        'assumptions': assumptions,
    }
    return routing_req, meta


def run_preview(data: dict, *, warehouse_code: str, temperature_zone: str,
                speed_kmh: int = 30, budget_ms: int = 5000, max_orders: int = 20,
                travel_mode: str = 'straight_line_simulation',
                business_mode: str = 'legacy_simulation', solver=None, road_provider=None) -> dict:
    request, metadata = prepare_preview(data, warehouse_code=warehouse_code,
        temperature_zone=temperature_zone, speed_kmh=speed_kmh, budget_ms=budget_ms,
        max_orders=max_orders, travel_mode=travel_mode, business_mode=business_mode,
        road_provider=road_provider)
    if solver is None:
        # Import stays inside infrastructure adapter, never changes the B-owned solver.
        from app.adapters.routing.ortools_solver import OrToolsRoutingSolver
        solver = OrToolsRoutingSolver()
    result = solver.solve(request)
    if result.metadata.has_solution:
        independent = validate_transport(request=request.model_dump(mode='python'),
                                         result=result.model_dump(mode='python'))
    else:
        independent = None
    if result.metadata.has_solution and (independent is None or not independent.passed):
        raise BridgeInputError('independent_transport_validation_failed')
    outcome = {**metadata,
        'business_fact_origin': ('r30a_explicit_synthetic_demo'
            if business_mode == 'verified_r24' and data.get('r30a', {}).get('source_kind') == 'explicit_synthetic_demo'
            else 'operator_records_origin_not_independently_verified' if business_mode == 'verified_r24'
            else 'r23_synthetic_legacy_assumptions'),
        'solver': 'R20 OrToolsRoutingSolver (unchanged)',
        'solver_status': result.metadata.status,
        'solver_raw_status': result.metadata.raw_status,
        'independent_validation': ('passed' if independent and independent.passed else 'not_applicable_no_solution'),
        'result': result.model_dump(mode='json'),
    }
    if travel_mode == 'osrm_road_estimate' and result.metadata.has_solution:
        from app.adapters.matrix.osrm import road_geometry
        node_key_by_id = {}
        for row in data['nodes']:
            key = str(row['node_key'])
            if key.startswith('WH:'):
                node_key_by_id[_id('node', key[3:])] = key
            elif key.startswith('C:'):
                node_key_by_id[_id('node', key[2:])] = key
        features = []
        for vehicle_route in outcome['result']['routes']:
            keys = [node_key_by_id[stop['node_id']] for stop in vehicle_route['stops']]
            geometry = road_geometry(data['nodes'], keys, fetch=road_provider)
            # R25 additive metadata for accurate stop-to-road animation. Positions
            # come exclusively from existing PG geonodes, never approximated.
            node_lookup = {str(row['node_key']): row for row in data['nodes']}
            stop_coordinates = [[float(node_lookup[key]['longitude']), float(node_lookup[key]['latitude'])]
                                for key in keys]
            features.append({'type': 'Feature', 'geometry': geometry,
                             'properties': {'vehicle_id': vehicle_route['vehicle_id'],
                                            'route_distance_m': vehicle_route['distance_m'],
                                            'distance_type': 'OSRM_road_network_estimate',
                                            'stop_coordinates': stop_coordinates}})
        outcome['demo_route_geojson'] = {'type': 'FeatureCollection', 'features': features}
    return outcome
