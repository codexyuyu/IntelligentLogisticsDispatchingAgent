"""R24 behavior checks without a PostgreSQL server, OSRM service or OR-Tools wheel."""
import json
from datetime import timedelta
from unittest.mock import patch
from decimal import Decimal
from fastapi.testclient import TestClient
import pytest

from app.adapters.matrix.osrm import OsrmUnavailable, road_matrix, road_geometry
from app.adapters.persistence.pg_routing_preview import BridgeInputError, prepare_preview
from app.adapters.persistence.pg_r24_business import readiness
from app.adapters.persistence.pg_simulation_archive import validate_saveable_preview, SimulationArchiveError
from app.main import app
from test_pg_routing_preview import ORIGIN, sample


def coords():
    return [{'node_key': 'WH:WH001', 'longitude': 116.4, 'latitude': 39.9},
            {'node_key': 'C:C001', 'longitude': 116.42, 'latitude': 39.9}]


def fake_table(url):
    assert '/table/v1/driving/' in url and 'annotations=duration%2Cdistance' in url
    return json.dumps({'code': 'Ok', 'durations': [[0, 67.3], [75.1, 0]],
                       'distances': [[0, 1250.3], [1330.9, 0]]}).encode()


def fake_geometry(url):
    assert '/route/v1/driving/' in url
    return json.dumps({'code': 'Ok', 'routes': [{'geometry': {'type': 'LineString',
                   'coordinates': [[116.4, 39.9], [116.41, 39.905], [116.42, 39.9]]}}]}).encode()


def test_road_matrix_real_source_no_distance_to_time_conversion():
    with patch.dict('os.environ', {'OSRM_BASE_URL': 'http://127.0.0.1:5000'}):
        t, d = road_matrix(coords(), ['WH:WH001', 'C:C001'], fetch=fake_table)
    assert t == ((0, 67), (75, 0))
    assert d == ((0, 1250), (1331, 0))
    assert t[0][1] != 150  # not synthetic km/h travel time


def test_road_geometry_is_not_straight_line():
    with patch.dict('os.environ', {'OSRM_BASE_URL': 'http://127.0.0.1:5000'}):
        geo = road_geometry(coords(), ['WH:WH001', 'C:C001'], fetch=fake_geometry)
    assert len(geo['coordinates']) == 3


@pytest.mark.parametrize('payload', [
    {'code': 'Ok', 'durations': [[0, None], [1,0]], 'distances': [[0,20],[20,0]]},
    {'code': 'NoRoute'},
    {'code': 'Ok', 'durations': [[0,1]], 'distances': [[0,2]]},
])
def test_road_unreachable_or_malformed_fails_closed(payload):
    with patch.dict('os.environ', {'OSRM_BASE_URL': 'http://127.0.0.1:5000'}):
        with pytest.raises(OsrmUnavailable):
            road_matrix(coords(), ['WH:WH001', 'C:C001'], fetch=lambda _: json.dumps(payload).encode())


def test_osrm_requires_explicit_configuration():
    with patch.dict('os.environ', {}, clear=True):
        with pytest.raises(OsrmUnavailable, match='not_configured'):
            road_matrix(coords(), ['WH:WH001', 'C:C001'], fetch=fake_table)


def test_r24_readiness_without_seed():
    assert readiness({})['tables_installed'] is False
    assert readiness({'orders':[{'order_code':'ORD001'}], 'vehicles':[{'vehicle_code':'V001'}],
                      'r24':{'orders': [], 'vehicles': [], 'handoffs': [], 'zones': [], 'lots': [], 'resources': []}})['complete'] is False


def metadata():
    return {'zones': [{'warehouse_code':'WH001','temperature_zone':'chilled','capacity_volume_l':1000}],
      'lots':[{'lot_code': 'L001','warehouse_code':'WH001','temperature_zone':'chilled',
               'quantity_units':100, 'best_before_at': ORIGIN+timedelta(days=7)}],
      'orders':[{'order_code':code,'warehouse_code':'WH001','lot_code':'L001','quantity_units':3,
                'volume_l':vol, 'freshness_deadline': ORIGIN+timedelta(hours=6),
                'temperature_zone':'chilled','version':1} for code,vol in [('ORD001',30),('ORD002',40)]],
      'vehicles':[{'vehicle_code':'V001','temperature_zone':'chilled',
                  'capacity_volume_l':70,'remaining_weight_kg':100,'remaining_volume_l':70,
                  'current_node_key':'WH:WH001','shift_start':ORIGIN-timedelta(hours=1),
                  'shift_end': ORIGIN+timedelta(hours=12),'available_at':ORIGIN-timedelta(minutes=10),'version':1},
                 {'vehicle_code':'V002','temperature_zone':'chilled',
                  'capacity_volume_l':70,'remaining_weight_kg':100,'remaining_volume_l':70,
                  'current_node_key':'WH:WH002','shift_start':ORIGIN-timedelta(hours=1),
                  'shift_end': ORIGIN+timedelta(hours=12),'available_at':ORIGIN-timedelta(minutes=10),'version':1}],
      'resources':[{'warehouse_code':'WH001','resource_code':'DOCK1','resource_kind':'loading_dock',
          'temperature_zone':'chilled','available_from':ORIGIN-timedelta(days=1),
          'available_until':ORIGIN+timedelta(days=1)}],
      'handoffs':[{'order_code':code,'warehouse_code':'WH001',
                   'resource_code':'DOCK1','ready_at':ORIGIN+timedelta(minutes=5),
                   'loading_window_end':ORIGIN+timedelta(hours=5)} for code in ('ORD001','ORD002')]}


def test_verified_r24_uses_real_volumes_lot_and_ready_times():
    data = sample()
    data['r24'] = metadata()
    req, meta = prepare_preview(data, warehouse_code='WH001', temperature_zone='chilled', business_mode='verified_r24')
    assert [o.volume_l for o in req.snapshot.orders] == [30, 40]
    assert req.snapshot.orders[0].batch_id == 'bat_L001'
    assert req.snapshot.vehicles[0].capacity_volume_l == 70
    assert req.warehouse_handoffs[0].ready_at_s > 0
    assert req.snapshot.vehicles[0].available_at_s > 0
    assert meta['business_mode'] == 'verified_r24'
    assert not any('没有体积字段' in line for line in meta['assumptions'])


def test_missing_verified_record_blocks_not_synthetic():
    data = sample(); data['r24'] = metadata()
    data['r24']['orders'] = data['r24']['orders'][:-1]
    with pytest.raises(BridgeInputError, match='r24_order_details_missing'):
        prepare_preview(data, warehouse_code='WH001', temperature_zone='chilled', business_mode='verified_r24')


def test_osrm_preview_matrix_uses_road_times():
    data = sample()
    def osrm_table(url):
        n = 3
        return json.dumps({'code':'Ok','durations':[[0 if i == j else 111 for j in range(n)] for i in range(n)],
                   'distances':[[0 if i == j else 2222 for j in range(n)] for i in range(n)]}).encode()
    data['nodes'] = [dict(row, longitude=116.4+i*0.01, latitude=39.9) for i,row in enumerate(data['nodes'])]
    with patch.dict('os.environ', {'OSRM_BASE_URL':'http://127.0.0.1:5000'}):
        req, meta = prepare_preview(data, warehouse_code='WH001', temperature_zone='chilled',
              travel_mode='osrm_road_estimate', road_provider=osrm_table)
    assert req.snapshot.matrix.duration_s[0][1] == 111
    assert req.snapshot.matrix.distance_m[0][1] == 2222
    assert meta['distance_type'] == 'OSRM_road_network_estimate'


def test_old_api_and_old_mode_still_work():
    data=sample()
    _, meta=prepare_preview(data, warehouse_code='WH001', temperature_zone='chilled')
    assert meta['travel_mode'] == 'straight_line_simulation'
    assert meta['business_mode'] == 'legacy_simulation'
    with patch.dict('os.environ', {'PG_DEMO_ENABLED':'1'}), \
         patch('app.api.routes.postgres_demo.load_view_data', return_value=data):
        client = TestClient(app)
        assert client.get('/local-pg/pg-preview/summary').status_code == 200


def test_archive_rejects_osrm_when_geometry_missing():
    from app.adapters.persistence.pg_simulation_archive import save_preview
    preview = {'mode':'simulation_preview_not_executable', 'database_mutated':False,
         'plan_written':False, 'independent_validation':'passed',
         'distance_type':'OSRM_road_network_estimate', 'estimated_duration_type':'osrm_profile_estimate_not_live_traffic',
         'assumptions':['osrm estimate'], 'selected_orders':1,
         'result':{'metadata':{'has_solution':True}, 'unserved_orders':[],
           'routes':[{'vehicle_id':'veh_V001','stops':[{'stop_kind':'delivery','order_ids':['ord_ORD001']},]}]}}
    with pytest.raises(SimulationArchiveError, match='geometry_missing'):
        save_preview(preview, {}, [])
