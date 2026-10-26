"""AC: opt-in, isolated storage for non-executable R21 routing simulations.

Never touches dispatch_plans/routes/route_stops, or the shared PlanningSnapshotStore.
The preview is recomputed by the server before saving; clients cannot submit routes.
"""
from __future__ import annotations

import json
import os
import re
from uuid import uuid4


class SimulationArchiveError(ValueError):
    pass


def _connection():
    if not os.environ.get('PGPASSWORD'):
        raise SimulationArchiveError('PGPASSWORD_not_configured')
    try:
        import psycopg
        from psycopg.rows import dict_row
    except ImportError as exc:
        raise RuntimeError('psycopg_not_installed') from exc
    return psycopg.connect(
        host=os.environ.get('PGHOST', '127.0.0.1'),
        port=int(os.environ.get('PGPORT', '5432')),
        dbname=os.environ.get('PGDATABASE', 'coldchain_db'),
        user=os.environ.get('PGUSER', 'postgres'),
        password=os.environ['PGPASSWORD'],
        connect_timeout=8,
        row_factory=dict_row,
    )


def validate_saveable_preview(preview: dict) -> None:
    """Refuse invalid/partial output; 'passed' is necessary but not sufficient."""
    if (preview.get('mode') != 'simulation_preview_not_executable'
            or preview.get('database_mutated') is not False
            or preview.get('plan_written') is not False
            or preview.get('independent_validation') != 'passed'
            or preview.get('distance_type') not in ('PostGIS_straight_line_not_driving_distance', 'OSRM_road_network_estimate')
            or preview.get('estimated_duration_type') not in ('synthetic_not_road_travel_time', 'osrm_profile_estimate_not_live_traffic')
            or (preview.get('distance_type') == 'OSRM_road_network_estimate') != (preview.get('estimated_duration_type') == 'osrm_profile_estimate_not_live_traffic')
            or not preview.get('assumptions')):
        raise SimulationArchiveError('preview_not_validated_simulation_only')
    result = preview.get('result') or {}
    if result.get('unserved_orders') or not result.get('routes'):
        raise SimulationArchiveError('preview_unserved_or_empty_routes')
    if not result.get('metadata', {}).get('has_solution'):
        raise SimulationArchiveError('preview_solver_has_no_solution')
    visited, vehicles = [], []
    for route in result['routes']:
        vehicle = route.get('vehicle_id')
        if not vehicle or vehicle in vehicles:
            raise SimulationArchiveError('preview_duplicated_vehicle')
        vehicles.append(vehicle)
        for stop in route.get('stops', []):
            if stop.get('stop_kind') == 'delivery':
                visited.extend(stop.get('order_ids') or [])
    if (not visited or len(visited) != len(set(visited))
            or len(visited) != preview.get('selected_orders')):
        raise SimulationArchiveError('preview_order_coverage_mismatch')


def straight_line_geojson(preview: dict, nodes: list[dict]) -> dict:
    """Route *schematics* from existing PostGIS positions, never road geometry."""
    coordinates_by_id = {}
    for node in nodes:
        key = str(node['node_key'])
        if key.startswith('WH:'):
            ident = 'node_' + key[3:]
        elif key.startswith('C:'):
            ident = 'node_' + key[2:]
        else:
            continue
        if node.get('longitude') is None or node.get('latitude') is None:
            continue
        lon, lat = float(node['longitude']), float(node['latitude'])
        if not -180 <= lon <= 180 or not -90 <= lat <= 90:
            raise SimulationArchiveError('invalid_coordinates')
        coordinates_by_id[ident] = [lon, lat]
    features = []
    for route in preview['result']['routes']:
        coords = []
        for stop in route['stops']:
            point = coordinates_by_id.get(stop['node_id'])
            if point is None:
                raise SimulationArchiveError('missing_coordinate_for_route_stop')
            coords.append(point)
        if len(coords) < 2:
            raise SimulationArchiveError('route_has_fewer_than_two_stops')
        features.append({'type': 'Feature',
            'geometry': {'type': 'LineString', 'coordinates': coords},
            'properties': {'vehicle_id': route['vehicle_id'],
                           'route_distance_m': route['distance_m'],
                           'distance_type': 'PostGIS_straight_line_not_driving_distance'}})
    return {'type': 'FeatureCollection', 'features': features}


def save_preview(preview: dict, params: dict, nodes: list[dict], *, connection_factory=None) -> str:
    """Single INSERT in its own table. Connection context commits or rolls back."""
    validate_saveable_preview(preview)
    payload = dict(preview)
    if preview['distance_type'] == 'OSRM_road_network_estimate':
        geo = preview.get('demo_route_geojson')
        if (not isinstance(geo, dict) or geo.get('type') != 'FeatureCollection'
                or len(geo.get('features', [])) != len(preview['result']['routes'])
                or any(feature.get('properties', {}).get('distance_type') != 'OSRM_road_network_estimate'
                       or feature.get('geometry', {}).get('type') != 'LineString'
                       for feature in geo['features'])):
            raise SimulationArchiveError('osrm_road_geometry_missing_or_malformed')
        payload['demo_route_geojson'] = geo
    else:
        payload['demo_route_geojson'] = straight_line_geojson(preview, nodes)
    payload['archived_as'] = 'simulation_only_not_executable'
    payload['archive_warning'] = ('Saved only in isolated pg_simulation_previews; ' 
                                  'the original R21 preview never wrote an executable plan.')
    code = 'SIMR22_' + uuid4().hex[:24]
    factory = connection_factory or _connection
    with factory() as conn:
        with conn.transaction():
            conn.execute('''INSERT INTO public.pg_simulation_previews
                  (preview_code, warehouse_code, temperature_zone,
                   selected_orders, selected_vehicles, request_parameters, preview_payload)
                  VALUES (%s, %s, %s, %s, %s, %s::jsonb, %s::jsonb)''',
                (code, preview['warehouse_code'], preview['temperature_zone'],
                 preview['selected_orders'], preview['selected_vehicles'],
                 json.dumps(params, ensure_ascii=False),
                 json.dumps(payload, ensure_ascii=False)))
    return code


def list_previews(*, limit: int = 20, connection_factory=None) -> list[dict]:
    if not 1 <= limit <= 50:
        raise SimulationArchiveError('invalid_limit')
    factory = connection_factory or _connection
    with factory() as conn:
        conn.execute('SET TRANSACTION ISOLATION LEVEL REPEATABLE READ, READ ONLY')
        rows = conn.execute('''SELECT preview_code, created_at, warehouse_code,
                           temperature_zone, selected_orders, selected_vehicles
                    FROM public.pg_simulation_previews
                    ORDER BY created_at DESC, preview_code DESC LIMIT %s''', (limit,)).fetchall()
    return [{**r, 'created_at': r['created_at'].isoformat() if hasattr(r['created_at'], 'isoformat') else r['created_at']}
            for r in rows]


def get_preview(code: str, *, connection_factory=None) -> dict | None:
    if not re.fullmatch(r'SIMR22_[0-9a-f]{24}', code):
        raise SimulationArchiveError('invalid_simulation_preview_code')
    factory = connection_factory or _connection
    with factory() as conn:
        conn.execute('SET TRANSACTION ISOLATION LEVEL REPEATABLE READ, READ ONLY')
        row = conn.execute('''SELECT preview_code, created_at, preview_payload
                     FROM public.pg_simulation_previews WHERE preview_code = %s''', (code,)).fetchone()
    if row is None:
        return None
    payload = row['preview_payload']
    if isinstance(payload, str):
        payload = json.loads(payload)
    return {'preview_code': row['preview_code'],
            'created_at': row['created_at'].isoformat() if hasattr(row['created_at'], 'isoformat') else row['created_at'],
            'mode': 'simulation_only_not_executable', 'preview': payload}
