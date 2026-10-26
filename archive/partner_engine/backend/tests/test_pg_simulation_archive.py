"""R22 fast unit tests (no PostgreSQL server or OR-Tools needed)."""
from datetime import datetime, timezone
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.adapters.persistence.pg_simulation_archive import (
    SimulationArchiveError, validate_saveable_preview, straight_line_geojson,
    save_preview, get_preview, list_previews,
)


def valid_preview():
    return {
        'mode': 'simulation_preview_not_executable', 'database_mutated': False,
        'plan_written': False, 'independent_validation': 'passed',
        'distance_type': 'PostGIS_straight_line_not_driving_distance',
        'estimated_duration_type': 'synthetic_not_road_travel_time',
        'assumptions': ['synthetic vehicle volume'], 'warehouse_code': 'WH001',
        'temperature_zone': 'chilled', 'selected_orders': 1, 'selected_vehicles': 1,
        'result': {'metadata': {'has_solution': True}, 'unserved_orders': [],
                   'routes': [{'vehicle_id': 'veh_V001', 'distance_m': 300,
                              'stops': [
                                  {'stop_kind': 'depot_start', 'node_id': 'node_WH001', 'order_ids': []},
                                  {'stop_kind': 'delivery', 'node_id': 'node_C001', 'order_ids': ['ord_ORD001']},
                                  {'stop_kind': 'depot_end', 'node_id': 'node_WH001', 'order_ids': []},
                              ]}]}}


def nodes():
    return [{'node_key': 'WH:WH001', 'longitude': 116.3, 'latitude': 39.9},
            {'node_key': 'C:C001', 'longitude': 116.4, 'latitude': 39.8}]


class FakeConn:
    def __init__(self, rows=None):
        self.statements = []
        self.rows = rows or []
        self.exited = False

    def __enter__(self): return self
    def __exit__(self, *_): self.exited = True
    def transaction(self): return self
    def execute(self, sql, params=None):
        self.statements.append((sql, params))
        return self
    def fetchall(self): return self.rows
    def fetchone(self): return self.rows[0] if self.rows else None


def test_only_valid_complete_simulations_saveable():
    valid = valid_preview()
    validate_saveable_preview(valid)
    for key, value in [('independent_validation', 'failed'),
                       ('mode', 'executable'), ('database_mutated', True)]:
        broken = {**valid, key: value}
        with pytest.raises(SimulationArchiveError):
            validate_saveable_preview(broken)
    broken = {**valid, 'result': {**valid['result'], 'unserved_orders': [{'order_id': 'other'}]}}
    with pytest.raises(SimulationArchiveError):
        validate_saveable_preview(broken)


def test_full_coverage_and_unique_vehicle_enforced():
    broken = valid_preview()
    broken['selected_orders'] = 2
    with pytest.raises(SimulationArchiveError, match='coverage'):
        validate_saveable_preview(broken)
    broken = valid_preview()
    broken['result']['routes'].append(broken['result']['routes'][0])
    with pytest.raises(SimulationArchiveError, match='vehicle'):
        validate_saveable_preview(broken)


def test_geojson_uses_coordinates_and_marks_straight_lines():
    data = straight_line_geojson(valid_preview(), nodes())
    feat = data['features'][0]
    assert feat['geometry']['coordinates'] == [[116.3, 39.9], [116.4, 39.8], [116.3, 39.9]]
    assert 'straight_line' in feat['properties']['distance_type']


def test_archive_writes_only_to_independent_table_and_jsonb():
    conn = FakeConn()
    code = save_preview(valid_preview(), {'speed_kmh': 30}, nodes(), connection_factory=lambda: conn)
    assert code.startswith('SIMR22_')
    assert conn.exited
    inserts = [x for x in conn.statements if x[0].lstrip().startswith('INSERT')]
    assert len(inserts) == 1
    assert 'public.pg_simulation_previews' in inserts[0][0]
    assert 'dispatch_plans' not in inserts[0][0]
    assert 'simulation_only_not_executable' in inserts[0][1][-1]
    assert 'FeatureCollection' in inserts[0][1][-1]


def test_read_is_transaction_read_only_and_code_parameterized():
    code = 'SIMR22_' + 'a' * 24
    conn = FakeConn([{'preview_code': code, 'created_at': datetime(2026, 10, 17, tzinfo=timezone.utc),
                      'preview_payload': {'archived_as': 'simulation_only_not_executable'}}])
    item = get_preview(code, connection_factory=lambda: conn)
    assert item['preview_code'] == code
    assert 'READ ONLY' in conn.statements[0][0]
    assert conn.statements[1][1] == (code,)
    with pytest.raises(SimulationArchiveError):
        get_preview("'); DROP TABLE x; --", connection_factory=lambda: conn)


def test_list_limit_parameterized():
    conn = FakeConn([])
    assert list_previews(connection_factory=lambda: conn) == []
    assert conn.statements[-1][1] == (20,)
    with pytest.raises(SimulationArchiveError):
        list_previews(limit=100)


def test_write_is_off_by_default_even_if_read_demo_enabled(monkeypatch):
    monkeypatch.setenv('PG_DEMO_ENABLED', '1')
    monkeypatch.delenv('PG_PREVIEW_WRITE_ENABLED', raising=False)
    c = TestClient(app)
    resp = c.post('/local-pg/pg-preview/saved', json={
        'warehouse_code': 'WH001', 'temperature_zone': 'chilled',
        'acknowledge_simulation_only': True, 'acknowledge_store_simulation_only': True})
    assert resp.status_code == 503
    assert 'archive_disabled' in resp.json()['detail']


def test_api_requires_explicit_double_acknowledgement(monkeypatch):
    monkeypatch.setenv('PG_DEMO_ENABLED', '1')
    monkeypatch.setenv('PG_PREVIEW_WRITE_ENABLED', '1')
    c = TestClient(app)
    r = c.post('/local-pg/pg-preview/saved', json={
        'warehouse_code': 'WH001', 'temperature_zone': 'chilled',
        'acknowledge_simulation_only': True})
    assert r.status_code == 422


def test_api_saves_recomputed_server_preview_and_reads_back(monkeypatch):
    monkeypatch.setenv('PG_DEMO_ENABLED', '1')
    monkeypatch.setenv('PG_PREVIEW_WRITE_ENABLED', '1')
    code = 'SIMR22_' + 'a' * 24
    obj = {'preview_code': code, 'created_at': '2026-10-17T10:00:00Z',
           'mode': 'simulation_only_not_executable',
           'preview': {**valid_preview(), 'demo_route_geojson': straight_line_geojson(valid_preview(), nodes())}}
    with patch('app.api.routes.postgres_demo.load_view_data', return_value={'nodes': nodes()}), \
         patch('app.api.routes.postgres_demo.run_preview', return_value=valid_preview()) as run, \
         patch('app.api.routes.postgres_demo.save_preview', return_value=code) as saved, \
         patch('app.api.routes.postgres_demo.get_preview', return_value=obj):
        client = TestClient(app)
        r = client.post('/local-pg/pg-preview/saved', json={
            'warehouse_code': 'WH001', 'temperature_zone': 'chilled',
            'acknowledge_simulation_only': True, 'acknowledge_store_simulation_only': True})
        assert r.status_code == 200, r.json()
        assert r.json()['business_plans_mutated'] is False
        assert r.json()['database_mutated'] is True
        assert run.call_count == 1
        assert saved.call_count == 1
        assert client.get('/local-pg/pg-preview/saved/' + code).json()['preview_code'] == code
        geo = client.get('/local-pg/pg-preview/saved/' + code + '/geojson')
        assert geo.status_code == 200
        assert geo.json()['type'] == 'FeatureCollection'
        map_result = client.get('/local-pg/pg-preview/saved/' + code + '/map')
        assert map_result.status_code == 200
        assert 'leaflet' in map_result.text.lower()


def test_shared_api_unchanged_and_local_archive_routes_registered():
    assert '/api/v1/planning-jobs' in app.openapi()['paths']
    local = TestClient(app).get('/local-pg/openapi.json').json()
    assert '/pg-preview/saved' in local['paths']
    assert '/pg-preview/saved/{preview_code}' in local['paths']
    assert '/pg-preview/saved/{preview_code}/geojson' in local['paths']
    assert '/local-pg/pg-preview/saved' not in app.openapi()['paths']
