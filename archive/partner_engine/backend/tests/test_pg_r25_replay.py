"""R25 GeoJSON for 3D replay: solver-ordered coordinates are never invented."""
import json
from types import SimpleNamespace
from unittest.mock import patch

from app.adapters.persistence.pg_routing_preview import run_preview
from test_pg_routing_preview import sample


def _service(url):
    if '/table/v1/driving/' in url:
        count = url.split('/table/v1/driving/', 1)[1].split('?')[0].count(';') + 1
        return json.dumps({'code': 'Ok',
            'durations': [[0 if a == b else 120 for b in range(count)] for a in range(count)],
            'distances': [[0 if a == b else 1000 for b in range(count)] for a in range(count)]}).encode()
    assert '/route/v1/driving/' in url
    return json.dumps({'code': 'Ok', 'routes': [{'geometry': {'type': 'LineString',
        'coordinates': [[116.4, 39.9], [116.41, 39.91], [116.43, 39.9]]}}]}).encode()


class _FakeSolver:
    def solve(self, request):
        depot = request.snapshot.matrix.node_ids[0]
        destination = request.snapshot.orders[0].delivery_node_id
        stops = [{'node_id': key, 'stop_kind': kind, 'order_ids': order_ids,
                  'arrival_at_s': i * 120, 'departure_at_s': i * 120}
                 for i, (key, kind, order_ids) in enumerate([
                     (depot, 'depot_start', []), (destination, 'delivery', [request.snapshot.orders[0].order_id]),
                     (depot, 'depot_end', [])])]
        # Transport validator is patched: this mock only exercises the GeoJSON
        # API projection, not the route solver or its independent verification.
        return SimpleNamespace(metadata=SimpleNamespace(has_solution=True, status='feasible', raw_status='fake'),
            model_dump=lambda **kwargs: {
                'metadata': {'has_solution': True}, 'routes': [{
                    'vehicle_id': request.snapshot.vehicles[0].vehicle_id,
                    'stops': stops, 'distance_m': 2000, 'duration_s': 240,
                }], 'unserved_orders': []})


def test_osrm_replay_geojson_contains_ordered_stop_coordinates():
    data = sample()
    coordinates = {'WH:WH001': (116.4, 39.9), 'WH:WH002': (116.5, 39.9),
                   'C:C001': (116.41, 39.91), 'C:C002': (116.43, 39.9)}
    for node in data['nodes']:
        node['longitude'], node['latitude'] = coordinates[node['node_key']]
    with patch.dict('os.environ', {'OSRM_BASE_URL': 'http://127.0.0.1:5000'}), \
         patch('app.adapters.persistence.pg_routing_preview.validate_transport', return_value=SimpleNamespace(passed=True)):
        preview = run_preview(data, warehouse_code='WH001', temperature_zone='chilled',
                              travel_mode='osrm_road_estimate', solver=_FakeSolver(), road_provider=_service)
    assert preview['independent_validation'] == 'passed'
    feature = preview['demo_route_geojson']['features'][0]
    assert feature['geometry']['coordinates'][1] == [116.41, 39.91]
    assert feature['properties']['stop_coordinates'] == [
        [116.4, 39.9], [116.41, 39.91], [116.4, 39.9],
    ]
    assert feature['properties']['distance_type'] == 'OSRM_road_network_estimate'
    assert preview['database_mutated'] is False
