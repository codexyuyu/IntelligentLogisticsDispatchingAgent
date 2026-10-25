"""AC: localhost-only PostgreSQL read/solve, opt-in isolated simulation archive."""
from __future__ import annotations
import os
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field, ConfigDict
from typing import Literal

from app.adapters.persistence.pg_routing_preview import BridgeInputError, load_view_data, public_rows, run_preview
from app.adapters.persistence.pg_simulation_archive import (
    SimulationArchiveError, save_preview, list_previews, get_preview,
)

router = APIRouter(prefix='/pg-preview', tags=['PostgreSQL local simulation (optional archive)'])


class PreviewRequest(BaseModel):
    model_config = ConfigDict(extra='forbid')
    warehouse_code: str = Field(min_length=1, max_length=40)
    temperature_zone: Literal['chilled', 'frozen']
    speed_kmh: int = Field(default=30, ge=1, le=100)
    travel_mode: Literal['straight_line_simulation', 'osrm_road_estimate'] = 'straight_line_simulation'
    business_mode: Literal['legacy_simulation', 'verified_r24'] = 'legacy_simulation'
    budget_ms: int = Field(default=5000, ge=500, le=20000)
    max_orders: int = Field(default=20, ge=1, le=20)
    acknowledge_simulation_only: Literal[True]


class SavePreviewRequest(PreviewRequest):
    acknowledge_store_simulation_only: Literal[True]

def _check_access(request: Request):
    # Not an authenticated production API. Default disabled and local-only.
    if os.environ.get('PG_DEMO_ENABLED') != '1':
        raise HTTPException(status_code=503, detail='pg_preview_disabled_set_PG_DEMO_ENABLED_1_for_local_testing')
    if not request.client or request.client.host not in ('127.0.0.1', '::1', 'testclient'):
        raise HTTPException(status_code=403, detail='pg_preview_localhost_only')


def _load(*, enrich=False):
    try:
        return load_view_data(include_r27=True) if enrich else load_view_data()
    except BridgeInputError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from None
    except Exception as exc:
        # Do not leak DSN/password/raw SQL or internal database details.
        raise HTTPException(status_code=503, detail=f'pg_unavailable:{type(exc).__name__}') from None


@router.get('/summary', operation_id='get_pg_preview_summary')
def summary(request: Request):
    _check_access(request)
    data = _load()
    warehouse_nodes = sorted(x['node_key'].removeprefix('WH:') for x in data['nodes'] if x['node_key'].startswith('WH:'))
    return {'mode': 'database_readonly', 'database_mutated': False,
            'orders': len(data['orders']), 'vehicles': len(data['vehicles']),
            'nodes': len(data['nodes']), 'distance_pairs': len(data['distance_matrix']),
            'warehouses': sorted({x['warehouse_code'] for x in data['vehicles']}),
            'warehouse_nodes': warehouse_nodes, 'r26_single_warehouse_ready': warehouse_nodes == ['WH001'] and all(v['warehouse_code'] == 'WH001' for v in data['vehicles']),
            'r29_active_warehouse': data.get('r29_active_depot'),
            'distance_type': 'PostGIS_straight_line'}


@router.get('/orders', operation_id='get_pg_preview_orders')
def orders(request: Request):
    _check_access(request)
    return public_rows(_load(), 'orders')


@router.get('/vehicles', operation_id='get_pg_preview_vehicles')
def vehicles(request: Request):
    _check_access(request)
    return public_rows(_load(), 'vehicles')


@router.get('/readiness', operation_id='get_pg_r24_business_readiness')
def business_readiness(request: Request):
    _check_access(request)
    from app.adapters.persistence.pg_r24_business import readiness
    try:
        return readiness(_load(enrich=True))
    except HTTPException as exc:
        if 'r24_tables_missing' in str(exc.detail):
            return readiness({})
        raise


@router.post('/route', operation_id='run_pg_simulated_r20_route')
def route(request: Request, body: PreviewRequest):
    _check_access(request)
    try:
        return run_preview(_load(enrich=body.business_mode == 'verified_r24'), warehouse_code=body.warehouse_code,
            temperature_zone=body.temperature_zone, speed_kmh=body.speed_kmh,
            budget_ms=body.budget_ms, max_orders=body.max_orders,
            travel_mode=body.travel_mode, business_mode=body.business_mode)
    except ValueError as exc:
        from app.adapters.matrix.osrm import OsrmUnavailable
        raise HTTPException(status_code=503 if isinstance(exc, OsrmUnavailable) else 422,
                            detail=str(exc)) from None
    except RuntimeError as exc:
        if str(exc).startswith('OR-Tools is required'):
            raise HTTPException(status_code=503, detail='ortools_missing_install_backend_requirements') from None
        raise


def _check_write_access(request: Request):
    _check_access(request)
    if os.environ.get('PG_PREVIEW_WRITE_ENABLED') != '1':
        raise HTTPException(status_code=503, detail='simulation_archive_disabled_use_explicit_r22_local_starter')


def _archive_error(exc: Exception) -> HTTPException:
    if isinstance(exc, SimulationArchiveError):
        return HTTPException(status_code=422, detail=str(exc))
    # Missing optional table is a known first-use issue, not a fake success.
    if type(exc).__name__ == 'UndefinedTable':
        return HTTPException(status_code=503, detail='simulation_archive_table_missing_run_setup_first')
    # Safe error type only; never expose SQL, DSN or credentials.
    return HTTPException(status_code=503, detail=f'simulation_archive_unavailable:{type(exc).__name__}')


@router.post('/saved', operation_id='save_pg_simulation_preview')
def save_simulated_preview(request: Request, body: SavePreviewRequest):
    """Re-run R20 + independent validation on fresh PG read before archiving.

    Never accepts a client-provided route/plan. Never writes into business plans.
    """
    _check_write_access(request)
    data = _load(enrich=body.business_mode == 'verified_r24')
    try:
        preview = run_preview(data, warehouse_code=body.warehouse_code,
            temperature_zone=body.temperature_zone, speed_kmh=body.speed_kmh,
            budget_ms=body.budget_ms, max_orders=body.max_orders,
            travel_mode=body.travel_mode, business_mode=body.business_mode)
        params = body.model_dump(exclude={'acknowledge_simulation_only',
                                          'acknowledge_store_simulation_only'})
        preview_code = save_preview(preview, params, data['nodes'])
    except (BridgeInputError, SimulationArchiveError) as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from None
    except RuntimeError as exc:
        if str(exc).startswith('OR-Tools is required'):
            raise HTTPException(status_code=503, detail='ortools_missing_install_backend_requirements') from None
        raise _archive_error(exc) from None
    except Exception as exc:
        raise _archive_error(exc) from None
    return {'preview_code': preview_code, 'mode': 'simulation_only_not_executable',
            'storage': 'public.pg_simulation_previews', 'database_mutated': True,
            'business_plans_mutated': False, 'selected_orders': preview['selected_orders'],
            'independent_validation': preview['independent_validation'],
            'distance_type': preview['distance_type']}


@router.get('/saved', operation_id='list_pg_simulation_previews')
def saved_list(request: Request, limit: int = 20):
    _check_access(request)
    try:
        items = list_previews(limit=limit)
    except Exception as exc:
        raise _archive_error(exc) from None
    return {'mode': 'simulation_only_not_executable', 'count': len(items), 'items': items}


@router.get('/saved/{preview_code}', operation_id='get_pg_simulation_preview')
def saved_detail(request: Request, preview_code: str):
    _check_access(request)
    try:
        item = get_preview(preview_code)
    except Exception as exc:
        raise _archive_error(exc) from None
    if item is None:
        raise HTTPException(status_code=404, detail='simulation_preview_not_found')
    return item


@router.get('/saved/{preview_code}/geojson', operation_id='get_pg_simulation_preview_geojson')
def saved_geojson(request: Request, preview_code: str):
    _check_access(request)
    try:
        item = get_preview(preview_code)
    except Exception as exc:
        raise _archive_error(exc) from None
    if item is None:
        raise HTTPException(status_code=404, detail='simulation_preview_not_found')
    features = item['preview'].get('demo_route_geojson')
    if not features:
        raise HTTPException(status_code=404, detail='simulation_preview_geojson_not_saved')
    return features


@router.get('/saved/{preview_code}/map', response_class=HTMLResponse,
            operation_id='view_pg_simulation_preview_map')
def saved_map(request: Request, preview_code: str):
    """Tiny read-only map for archived simulation routes; not navigable roads."""
    _check_access(request)
    try:
        item = get_preview(preview_code)
    except Exception as exc:
        raise _archive_error(exc) from None
    if item is None:
        raise HTTPException(status_code=404, detail='simulation_preview_not_found')
    # Preview code has been strictly checked (SIMR22_[a-f0-9]{24}) in get_preview.
    page = """<!doctype html><html lang="zh-CN"><head><meta charset="utf-8">
<title>R22 冷链模拟路线示意地图</title><meta name="viewport" content="width=device-width,initial-scale=1">
<link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css">
<style>body{font:15px system-ui,'Microsoft YaHei',sans-serif;margin:0;color:#233}header{padding:12px 18px;background:#f2f6f7}
#map{height:75vh}small{color:#565656}strong{color:#973600}</style></head><body>
<header><b>R24 冷链路线模拟回放</b> · __CODE__<p><strong>非可执行调度：可能为 PostGIS 直线示意或 OSRM 道路估计；均不是实时道路导航。</strong>
<br><small>可能使用 OSRM 道路估计或 PostGIS 直线示意，具体以路线来源标注为准；不可用于实际调度。</small></p></header>
<div id="map"></div><script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
<script>
const map=L.map('map').setView([39.9,116.4],11);
L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png',
 {attribution:'© OpenStreetMap contributors',maxZoom:18}).addTo(map);
fetch('geojson').then(r=>{if(!r.ok)throw Error('读取失败');return r.json()}).then(data=>{
 const colors=['#0067b9','#a34b00','#148560','#8d43ab','#8c1818'];
 const groups=[];
 (data.features||[]).forEach((feature,i)=>{
   const layer=L.geoJSON(feature,{style:{color:colors[i%colors.length],weight:5,opacity:.8}}).addTo(map);
   layer.bindPopup('车辆：'+String(feature.properties.vehicle_id)+'<br>规划距离：'+String(feature.properties.route_distance_m)+' m<br>来源：'+String(feature.properties.distance_type));
   groups.push(layer);
 });
 if(groups.length){const all=L.featureGroup(groups);map.fitBounds(all.getBounds().pad(.15));}
 else{alert('未找到路线数据');}
}).catch(e=>alert('地图数据读取失败：'+e.message));
</script></body></html>"""
    return HTMLResponse(page.replace('__CODE__', preview_code))


class R27WorkflowRequest(BaseModel):
    """Explicit dry-run. PostgreSQL mode never substitutes synthetic business parameters."""
    model_config = ConfigDict(extra='forbid')
    source: Literal['single_warehouse_demo', 'verified_postgres']
    temperature_zone: Literal['chilled', 'frozen'] = 'chilled'
    travel_mode: Literal['straight_line_simulation', 'osrm_road_estimate'] = 'straight_line_simulation'
    speed_kmh: int = Field(default=30, ge=1, le=100)
    max_orders: int = Field(default=20, ge=1, le=20)
    budget_ms: int = Field(default=60000, ge=10000, le=120000)
    acknowledge_dry_run_only: Literal[True]


@router.get('/r27/readiness', operation_id='get_r27_workflow_readiness')
def r27_readiness(request: Request):
    _check_access(request)
    from app.adapters.persistence.pg_r27_workflow import readiness
    try:
        return readiness(load_view_data(include_r27=True))
    except BridgeInputError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from None
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f'pg_unavailable:{type(exc).__name__}') from None


@router.get('/r28/diagnostics', operation_id='get_r28_readonly_diagnostics')
def r28_diagnostics(request: Request):
    _check_access(request)
    from app.adapters.persistence.pg_r28_diagnostics import diagnostics
    from app.adapters.persistence.pg_simulation_archive import _connection
    from tools.pg_r26_single_warehouse import inspect
    try:
        data = load_view_data(include_r27=True)
        with _connection() as conn:
            conn.execute('SET TRANSACTION READ ONLY')
            warehouse_report = inspect(conn)
            conn.rollback()
        return diagnostics(data, warehouse_report)
    except BridgeInputError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from None
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f'r28_diagnostics_unavailable:{type(exc).__name__}') from None


@router.post('/r27/workflow', operation_id='run_r27_readonly_closed_loop')
def r27_workflow(request: Request, body: R27WorkflowRequest):
    _check_access(request)
    from app.adapters.persistence.pg_r27_workflow import demo_snapshot, execute, verified_snapshot
    try:
        if body.source == 'single_warehouse_demo':
            if body.travel_mode != 'straight_line_simulation':
                raise BridgeInputError('r27_demo_does_not_claim_osrm_road_routes')
            return execute(demo_snapshot(), budget_ms=body.budget_ms,
                source='scenario_demo', extra={'scenario':'single_warehouse_20_orders',
                    'business_facts':'all_synthetic', 'road_facts':'scenario_travel_matrix'})
        data = load_view_data(include_r27=True)
        snapshot, meta = verified_snapshot(data, temperature_zone=body.temperature_zone,
            travel_mode=body.travel_mode, speed_kmh=body.speed_kmh,
            max_orders=body.max_orders, budget_ms=min(body.budget_ms, 20000))
        from app.adapters.persistence.pg_routing_preview import _datetime, _id, _seconds
        limits = {_id('ord', row['order_code']): _seconds(
            _datetime(row['loading_window_end'], 'loading_window_end'), snapshot.origin_at, 'loading_window_end')
            for row in data['r24']['handoffs']
            if _id('ord', row['order_code']) in {o.order_id for o in snapshot.orders}}
        provenance = data.get('r30a', {'source_kind':'unmarked_operator_or_legacy_rows'})
        synthetic = provenance.get('source_kind') == 'explicit_synthetic_demo'
        return execute(snapshot, budget_ms=body.budget_ms,
            source='postgres_synthetic_demo' if synthetic else 'verified_postgres',
            extra={'warehouse_code':'WH001', 'selected_temperature_zone':body.temperature_zone,
                   'distance_type':meta['distance_type'],
                   'business_facts':'r30a_explicit_synthetic_demo' if synthetic else 'postgres_operator_supplied_unverified_origin',
                   'provenance':provenance, 'handoff_limits':limits})
    except BridgeInputError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from None
    except ValueError as exc:
        from app.adapters.matrix.osrm import OsrmUnavailable
        raise HTTPException(status_code=503 if isinstance(exc, OsrmUnavailable) else 422,
                            detail=str(exc)) from None
    except RuntimeError as exc:
        if 'OR-Tools is required' in str(exc):
            raise HTTPException(status_code=503, detail='ortools_missing_install_backend_requirements') from None
        raise HTTPException(status_code=422, detail=f'r27_solver_or_validation_failed:{str(exc)[:260]}') from None
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f'r27_unavailable:{type(exc).__name__}') from None


@router.get('/r30a/readiness', operation_id='get_r30a_data_driven_readiness')
def r30a_readiness(request: Request):
    _check_access(request)
    from app.adapters.persistence.pg_r27_workflow import readiness
    try:
        data = load_view_data(include_r27=True)
        report = readiness(data)
        report['mode'] = 'r30a_postgresql_to_cpsat_to_ortools_readonly'
        report['execution'] = 'dry_run_only_no_business_mutations'
        report['provenance_warning'] = ('explicitly_synthetic_csv_values_not_real_business_facts'
            if report['provenance']['source_kind'] == 'explicit_synthetic_demo'
            else 'operator_supplied_values_have_no_independent_real_world_attestation')
        return report
    except BridgeInputError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from None
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f'r30a_status_unavailable:{type(exc).__name__}') from None


class R30BRescheduleRequest(R27WorkflowRequest):
    """Each request re-runs and verifies R30-A from its authoritative source.

    Client-supplied plan snapshots and SQL are never accepted. No writes.
    """
    event_type: Literal['vehicle_breakdown', 'delivery_delay', 'warehouse_resource_failure', 'inventory_quarantine']
    object_id: str = Field(min_length=3, max_length=70)
    occurred_at_s: int = Field(ge=0, le=8640000)
    delay_s: int = Field(default=0, ge=0, le=86400)


@router.post('/r30b/reschedule', operation_id='run_r30b_readonly_exception_reschedule')
def r30b_reschedule(request: Request, body: R30BRescheduleRequest):
    _check_access(request)
    from app.adapters.persistence.pg_r30b_reschedule import ExceptionSpec, RescheduleInputError, run_reschedule
    try:
        baseline = r27_workflow(request, body)
        result = run_reschedule(baseline=baseline, spec=ExceptionSpec(
            event_type=body.event_type, object_id=body.object_id,
            occurred_at_s=body.occurred_at_s, delay_s=body.delay_s), budget_ms=body.budget_ms)
        return result
    except RescheduleInputError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from None
    except HTTPException:
        raise
    except RuntimeError as exc:
        if 'OR-Tools is required' in str(exc):
            raise HTTPException(status_code=503, detail='ortools_missing_install_backend_requirements') from None
        raise HTTPException(status_code=422, detail=f'r30b_validation_or_solver_failed:{str(exc)[:260]}') from None
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f'r30b_unavailable:{type(exc).__name__}') from None
