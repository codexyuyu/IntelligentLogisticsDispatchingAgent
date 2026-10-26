"""R24: OSRM Table/Route adapter; roads are profile estimates, NOT live traffic.

Never called from an OR-Tools callback. Configured service URL is operator-supplied,
not caller-supplied. No fake straight-line fallback if a road call fails.
"""
from __future__ import annotations

import json
import os
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from math import ceil, isfinite
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlencode, urlsplit
from urllib.request import Request, urlopen


class OsrmUnavailable(ValueError):
    pass


def _endpoint() -> str:
    raw = os.environ.get('OSRM_BASE_URL', '').strip().rstrip('/')
    parts = urlsplit(raw)
    if (not raw or parts.scheme not in ('http', 'https') or not parts.hostname
            or parts.username or parts.password or parts.query or parts.fragment
            or parts.path not in ('', '/') or len(raw) > 240):
        raise OsrmUnavailable('osrm_base_url_not_configured_or_invalid')
    return raw


def _request(path: str, params: dict, *, fetch=None) -> dict:
    endpoint = _endpoint()
    url = endpoint + path + '?' + urlencode(params)
    if len(url) > 7000:
        raise OsrmUnavailable('osrm_request_too_long')
    try:
        if fetch is None:
            req = Request(url, headers={'User-Agent': 'ColdchainR24/1.0', 'Accept': 'application/json'})
            with urlopen(req, timeout=8) as response:
                if response.headers.get('Content-Length') and int(response.headers['Content-Length']) > 3_000_000:
                    raise OsrmUnavailable('osrm_response_too_large')
                raw = response.read(3_000_001)
                if len(raw) > 3_000_000:
                    raise OsrmUnavailable('osrm_response_too_large')
        else:
            raw = fetch(url)
        document = json.loads(raw)
    except (HTTPError, URLError, TimeoutError, OSError, ValueError, UnicodeError) as exc:
        if isinstance(exc, OsrmUnavailable):
            raise
        raise OsrmUnavailable('osrm_service_unreachable_or_invalid_response') from None
    if not isinstance(document, dict) or document.get('code') != 'Ok':
        raise OsrmUnavailable('osrm_no_road_solution')
    return document


def _metric(value, label: str) -> int:
    try:
        v = Decimal(str(value))
        if not v.is_finite() or v < 0:
            raise ValueError()
        return max(0, int(v.to_integral_value(rounding=ROUND_HALF_UP)))
    except (ValueError, TypeError, InvalidOperation):
        raise OsrmUnavailable('osrm_invalid_' + label) from None


def _coords(nodes: list[dict], keys: list[str]) -> str:
    lookup = {str(row['node_key']): row for row in nodes}
    pts = []
    for key in keys:
        if key not in lookup:
            raise OsrmUnavailable('osrm_missing_coordinate')
        try:
            lon, lat = (float(lookup[key][field]) for field in ('longitude', 'latitude'))
        except (TypeError, ValueError, KeyError):
            raise OsrmUnavailable('osrm_missing_coordinate') from None
        if not isfinite(lon) or not isfinite(lat) or not -180 <= lon <= 180 or not -90 <= lat <= 90:
            raise OsrmUnavailable('osrm_invalid_coordinate')
        pts.append(f'{lon:.7f},{lat:.7f}')
    return ';'.join(pts)


def road_matrix(nodes: list[dict], keys: list[str], *, fetch=None) -> tuple[tuple[tuple[int, ...], ...], tuple[tuple[int, ...], ...]]:
    """Return (duration_s, distance_m) in supplied node order. Reject unreachable/null arcs."""
    if not 1 < len(keys) <= 25 or len(set(keys)) != len(keys):
        raise OsrmUnavailable('osrm_invalid_node_count')
    coords = _coords(nodes, keys)
    result = _request('/table/v1/driving/' + coords, {'annotations': 'duration,distance'}, fetch=fetch)
    durations, distances = result.get('durations'), result.get('distances')
    n = len(keys)
    if any(not isinstance(x, list) or len(x) != n for matrix in (durations, distances)
           for x in (matrix if isinstance(matrix, list) else [])) or not all(isinstance(m, list) and len(m) == n for m in (durations, distances)):
        raise OsrmUnavailable('osrm_invalid_matrix_shape')
    def convert(matrix, label):
        return tuple(tuple(0 if i == j else max(1, _metric(val, label)) for j, val in enumerate(row))
                     for i, row in enumerate(matrix))
    return convert(durations, 'duration'), convert(distances, 'distance')


def road_geometry(nodes: list[dict], stop_keys: list[str], *, fetch=None) -> dict:
    """Full road-polyline geometry of one solver-ordered vehicle route, no rerouting of stop order."""
    if not 2 <= len(stop_keys) <= 25:
        raise OsrmUnavailable('osrm_invalid_route_stops')
    coords = _coords(nodes, stop_keys)
    result = _request('/route/v1/driving/' + coords,
                      {'overview': 'full', 'geometries': 'geojson', 'steps': 'false'}, fetch=fetch)
    routes = result.get('routes')
    if not isinstance(routes, list) or not routes:
        raise OsrmUnavailable('osrm_no_road_solution')
    geo = routes[0].get('geometry')
    if not isinstance(geo, dict) or geo.get('type') != 'LineString':
        raise OsrmUnavailable('osrm_invalid_geometry')
    points = geo.get('coordinates')
    if not isinstance(points, list) or not 2 <= len(points) <= 25000:
        raise OsrmUnavailable('osrm_invalid_geometry')
    for point in points:
        if (not isinstance(point, list) or len(point) != 2 or
                any(not isinstance(x, (int, float)) or not isfinite(x) for x in point) or
                not -180 <= point[0] <= 180 or not -90 <= point[1] <= 90):
            raise OsrmUnavailable('osrm_invalid_geometry')
    return geo
