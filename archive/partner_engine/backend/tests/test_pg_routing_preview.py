"""AC's narrow regression tests. No DB server, no OR-Tools wheel required here."""
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from app.adapters.persistence.pg_routing_preview import (
    BridgeInputError, load_view_data, prepare_preview, run_preview,
)
from app.main import app

ORIGIN = datetime(2026, 10, 18, 8, tzinfo=timezone.utc)


def sample():
    return {
        'orders': [
            {'order_code': 'ORD001', 'customer_code': 'C001', 'weight_kg': Decimal('15'),
             'min_temp_c': Decimal('2'), 'max_temp_c': Decimal('6'),
             'window_start': ORIGIN, 'window_end': ORIGIN + timedelta(hours=3),
             'service_minutes': 10},
            {'order_code': 'ORD002', 'customer_code': 'C002', 'weight_kg': Decimal('12'),
             'min_temp_c': Decimal('2'), 'max_temp_c': Decimal('6'),
             'window_start': ORIGIN + timedelta(minutes=15), 'window_end': ORIGIN + timedelta(hours=4),
             'service_minutes': 15},
        ],
        'vehicles': [
            {'vehicle_code': 'V001', 'warehouse_code': 'WH001', 'capacity_kg': Decimal('100'),
             'min_temp_c': Decimal('-10'), 'max_temp_c': Decimal('8')},
            {'vehicle_code': 'V002', 'warehouse_code': 'WH002', 'capacity_kg': Decimal('100'),
             'min_temp_c': Decimal('-10'), 'max_temp_c': Decimal('8')},
        ],
        'nodes': [{'node_key': key} for key in ('WH:WH001', 'WH:WH002', 'C:C001', 'C:C002')],
        'distance_matrix': [
            {'from_node': a, 'to_node': b, 'distance_m': Decimal(str(
                0 if a == b else (1000 if (a == 'WH:WH001' or b == 'WH:WH001') else 4000)
            ))}
            for a in ('WH:WH001', 'WH:WH002', 'C:C001', 'C:C002')
            for b in ('WH:WH001', 'WH:WH002', 'C:C001', 'C:C002')
        ],
    }


def build(data=None):
    return prepare_preview(data or sample(), warehouse_code='WH001', temperature_zone='chilled')


def test_contract_real_view_values_and_explicit_simulation_fields():
    req, meta = build()
    assert len(req.snapshot.orders) == 2
    assert len(req.snapshot.vehicles) == 1
    assert req.snapshot.orders[0].weight_kg == 15
    assert req.snapshot.orders[0].volume_l == 15  # explicit synthetic only
    assert req.snapshot.orders[0].service_duration_s == 600
    assert req.snapshot.orders[0].service_window.start_s == 0
    assert req.snapshot.orders[1].service_window.start_s == 900
    assert req.snapshot.matrix.duration_s[0][1] == 120
    assert req.snapshot.orders[0].source.source_kind == 'simulation'
    assert req.warehouse_handoffs[0].ready_at_s == 0
    assert meta['distance_type'] == 'PostGIS_straight_line_not_driving_distance'
    assert meta['plan_written'] is False
    assert meta['selected_orders'] == 2
    assert meta['selected_vehicles'] == 1


def test_non_integer_weight_not_coerced():
    data = sample()
    data['orders'][0]['weight_kg'] = Decimal('15.5')
    with pytest.raises(BridgeInputError, match='weight_kg'):
        build(data)


def test_cross_zero_zone_rejected():
    data = sample()
    data['orders'][0]['min_temp_c'] = Decimal('-2')
    with pytest.raises(BridgeInputError, match='cross_zero'):
        build(data)


def test_vehicle_must_cover_complete_order_temperature_band():
    data = sample()
    data['vehicles'][0]['max_temp_c'] = Decimal('4')
    with pytest.raises(BridgeInputError, match='no_vehicle_covers'):
        build(data)


def test_matrix_gap_rejected():
    data = sample()
    data['distance_matrix'].pop()
    with pytest.raises(BridgeInputError, match='distance_matrix_incomplete'):
        build(data)


def test_r20_solver_is_actually_called_using_routingrequest():
    class FakeSolver:
        def solve(self, request):
            assert request.__class__.__name__ == 'RoutingRequest'
            return SimpleNamespace(metadata=SimpleNamespace(
                has_solution=False, status='no_solution_within_budget', raw_status='stub_no_solution'),
                model_dump=lambda **kwargs: {'status': 'unavailable'},
            )
    payload = run_preview(sample(), warehouse_code='WH001', temperature_zone='chilled', solver=FakeSolver())
    assert payload['solver'] == 'R20 OrToolsRoutingSolver (unchanged)'
    assert payload['independent_validation'] == 'not_applicable_no_solution'
    assert payload['database_mutated'] is False


def test_local_endpoints_disabled_by_default(monkeypatch):
    monkeypatch.delenv('PG_DEMO_ENABLED', raising=False)
    client = TestClient(app)
    assert client.get('/local-pg/pg-preview/orders').status_code == 503
    assert client.post('/local-pg/pg-preview/route', json={
        'warehouse_code': 'WH001', 'temperature_zone': 'chilled',
        'acknowledge_simulation_only': True,
    }).status_code == 503


def test_local_read_endpoints_and_acknowledgement(monkeypatch):
    monkeypatch.setenv('PG_DEMO_ENABLED', '1')
    with patch('app.api.routes.postgres_demo.load_view_data', return_value=sample()):
        client = TestClient(app)
        assert client.get('/local-pg/pg-preview/summary').json()['orders'] == 2
        orders = client.get('/local-pg/pg-preview/orders').json()
        assert orders['count'] == 2
        assert orders['rows'][0]['weight_kg'] == '15'
        assert client.get('/local-pg/pg-preview/vehicles').json()['count'] == 2
        assert client.post('/local-pg/pg-preview/route', json={
            'warehouse_code': 'WH001', 'temperature_zone': 'chilled'
        }).status_code == 422


def test_read_only_transaction_and_whitelisted_sql_queries():
    class Conn:
        def __init__(self): self.sql = []
        def __enter__(self): return self
        def __exit__(self, *_): pass
        def execute(self, query):
            self.sql.append(query.strip())
            return self
        def fetchall(self): return []
        def fetchone(self): return None
    conn = Conn()
    result = load_view_data(lambda: conn)
    assert all(not value for value in result.values())
    assert conn.sql[0] == 'SET TRANSACTION ISOLATION LEVEL REPEATABLE READ, READ ONLY'
    assert len(conn.sql) == 6  # R29 marker existence is checked read-only
    assert all(q.startswith('SELECT ') for q in conn.sql[1:])


def test_public_api_is_separate_from_r20_shared_openapi():
    primary = app.openapi()
    assert '/local-pg/pg-preview/orders' not in primary['paths']
    assert '/api/v1/planning-jobs' in primary['paths']
    client = TestClient(app)
    local_openapi = client.get('/local-pg/openapi.json').json()
    assert '/pg-preview/orders' in local_openapi['paths']
    assert '/pg-preview/route' in local_openapi['paths']


def test_pg_password_required_not_leaked(monkeypatch):
    monkeypatch.setenv('PG_DEMO_ENABLED', '1')
    monkeypatch.delenv('PGPASSWORD', raising=False)
    client = TestClient(app)
    result = client.get('/local-pg/pg-preview/summary')
    assert result.status_code == 503
    assert result.json()['detail'] == 'PGPASSWORD_not_configured'
