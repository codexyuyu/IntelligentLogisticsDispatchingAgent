"""R30-C: localhost-only DeepSeek chat + real R27/R30B tool orchestration.

No SQL, shell, write/commit tool or external API key ever exposed to the model.
Read/solve requests use the existing PostgreSQL preview access guard.
"""
from __future__ import annotations
import json
from typing import Any, Literal
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, ConfigDict, Field

from app.adapters.llm.gateway import DeepSeekGateway, ModelUnavailable, model_status
from app.adapters.llm.prompts import build_prompt
from app.api.routes import postgres_demo as pg

router = APIRouter(prefix='/pg-preview/r30c', tags=['R30-C DeepSeek local demo'])
Source = Literal['single_warehouse_demo', 'verified_postgres']
Zone = Literal['chilled', 'frozen']
EventType = Literal['vehicle_breakdown', 'delivery_delay', 'warehouse_resource_failure', 'inventory_quarantine']

class ChatTurn(BaseModel):
    model_config = ConfigDict(extra='forbid')
    role: Literal['user', 'assistant']
    content: str = Field(min_length=1, max_length=1800)

class ChatRequest(BaseModel):
    model_config = ConfigDict(extra='forbid')
    message: str = Field(min_length=1, max_length=1800)
    history: list[ChatTurn] = Field(default_factory=list, max_length=8)
    source: Source = 'single_warehouse_demo'
    temperature_zone: Zone = 'chilled'
    budget_ms: int = Field(default=60000, ge=10000, le=120000)

class QuickRequest(BaseModel):
    """Explicit user-driven real solver fallback, not AI inference."""
    model_config = ConfigDict(extra='forbid')
    action: Literal['get_business_status', 'generate_joint_plan', 'simulate_exception']
    source: Source = 'single_warehouse_demo'
    temperature_zone: Zone = 'chilled'
    budget_ms: int = Field(default=60000, ge=10000, le=120000)
    event_type: EventType = 'vehicle_breakdown'
    object_id: str | None = Field(default=None, max_length=70)
    occurred_at_s: int | None = Field(default=None, ge=0)
    delay_s: int = Field(default=900, ge=0, le=86400)

class ExceptionArgs(BaseModel):
    model_config = ConfigDict(extra='forbid')
    event_type: EventType
    object_id: str | None = Field(default=None, max_length=70)
    occurred_at_s: int | None = Field(default=None, ge=0)
    delay_s: int = Field(default=900, ge=0, le=86400)

TOOLS = [
    {'type': 'function', 'function': {'name': 'get_business_status',
        'description': '只读查询当前选定数据来源下的仓库/订单/车辆概况；不生成路线',
        'parameters': {'type': 'object', 'properties': {}, 'additionalProperties': False}}},
    {'type': 'function', 'function': {'name': 'generate_joint_plan',
        'description': '使用现有真实 CP-SAT + OR-Tools 生成仓运联合方案并运行 R28 对账，仅只读仿真',
        'parameters': {'type': 'object', 'properties': {}, 'additionalProperties': False}}},
    {'type': 'function', 'function': {'name': 'simulate_exception',
        'description': '通过 R30-B 调用真实异常后缀重排和独立验证；对车辆号输入 V002 或 veh_V002，时间不确定时留空由当前路线确定',
        'parameters': {'type': 'object', 'properties': {
            'event_type': {'type': 'string', 'enum': ['vehicle_breakdown', 'delivery_delay', 'warehouse_resource_failure', 'inventory_quarantine']},
            'object_id': {'type': 'string', 'description': '需要处理的车辆/资源/库存批次的编号；未知时留空'},
            'occurred_at_s': {'type': 'integer', 'minimum': 0, 'description': '距调度仿真起点的秒数；不明确时省略'},
            'delay_s': {'type': 'integer', 'minimum': 0, 'maximum': 86400, 'description': '配送延误秒数'}},
            'required': ['event_type'], 'additionalProperties': False}}},
]


def _base_request(ctx: ChatRequest | QuickRequest) -> dict:
    return {
        'source': ctx.source, 'temperature_zone': ctx.temperature_zone,
        'travel_mode': 'straight_line_simulation', 'speed_kmh': 30, 'max_orders': 20,
        'budget_ms': ctx.budget_ms, 'acknowledge_dry_run_only': True,
    }


def _overview(request: Request, ctx: ChatRequest | QuickRequest) -> dict:
    if ctx.source == 'single_warehouse_demo':
        from app.adapters.persistence.pg_r27_workflow import demo_snapshot
        snap = demo_snapshot()
        return {'data_source': 'synthetic_scenario_no_database', 'warehouse_codes': [w.warehouse_id for w in snap.warehouses],
                'orders': len(snap.orders), 'vehicles': len(snap.vehicles),
                'warehouse_resources': len(snap.resources), 'has_executed_solver': False,
                'database_mutated': False, 'read_only': True}
    result = pg.summary(request)
    return {'data_source': 'postgresql_recorded_business_data_check_provenance',
            'warehouses': result['warehouses'], 'orders': result['orders'], 'vehicles': result['vehicles'],
            'single_active_warehouse': result['r26_single_warehouse_ready'],
            'distance_type': result['distance_type'], 'has_executed_solver': False,
            'database_mutated': False, 'read_only': True}


def _workflow(request: Request, ctx: ChatRequest | QuickRequest) -> dict:
    result = pg.r27_workflow(request, pg.R27WorkflowRequest(**_base_request(ctx)))
    if not (result.get('validated') and result['reconciliation']['status'] == 'passed'
            and result['plan']['validation']['status'] == 'passed'
            and result['database_mutated'] is False and result['business_plans_mutated'] is False):
        raise HTTPException(status_code=422, detail='r30c_underlying_plan_not_verified')
    return result


def _plan_summary(result: dict) -> dict:
    plan = result['plan']; reconcile = result['reconciliation']
    snapshot_ops = {o['operation_id']: o for o in result['snapshot'].get('operations', [])}
    vehicle_details = []
    for route in plan['routing']['routes']:
        vehicle_details.append({
            'vehicle_id': route['vehicle_id'], 'distance_m': route.get('distance_m'),
            'departure_at_s': route['stops'][0]['departure_at_s'] if route['stops'] else None,
            'order_sequence': [oid for stop in route.get('stops', []) if stop.get('stop_kind') == 'delivery'
                               for oid in stop.get('order_ids', [])],
        })
    warehouse_work = [{
        'operation_id': op['operation_id'], 'operation_kind': snapshot_ops.get(op['operation_id'], {}).get('operation_kind'),
        'order_ids': snapshot_ops.get(op['operation_id'], {}).get('order_ids', []),
        'resource_id': op['resource_id'], 'start_s': op.get('start_s'), 'end_s': op.get('end_s'),
    } for op in plan['warehouse']['operations']]
    return {'tool': 'generate_joint_plan', 'status': 'verified_readonly', 'source': result['source'],
            'warehouse': result['snapshot']['warehouses'][0]['warehouse_id'],
            'order_count': reconcile['scope_order_count'], 'planned_delivery_count': reconcile['planned_delivery_order_count'],
            'unserved_order_count': reconcile['unserved_order_count'],
            'operations': len(plan['warehouse']['operations']),
            'vehicle_route_count': len(plan['routing']['routes']),
            'route_vehicle_ids': [r['vehicle_id'] for r in plan['routing']['routes']],
            'vehicle_assignment_details': vehicle_details[:20],
            'warehouse_operations': warehouse_work[:60],
            'warehouse_work_truncated': len(warehouse_work) > 60,
            'warehouse_handoffs': [
                {'order_id': h['order_id'], 'ready_at_s': h['ready_at_s']}
                for h in plan['warehouse']['warehouse_handoffs'][:60]],
            'cold_chain_audit': result.get('cold_chain_audit', {'status':'not_checked'}),
            'validation': plan['validation']['status'], 'r28_reconciliation': reconcile['status'],
            'database_mutated': False, 'business_plans_mutated': False,
            'route_accuracy': 'synthetic_or_postgis_not_live_navigation',
            'can_open_existing_3d_replay': True}


def _event_target(baseline: dict, spec: ExceptionArgs) -> tuple[str, int]:
    snap = baseline['snapshot']; plan = baseline['plan']
    objects = {
        'vehicle_breakdown': [v['vehicle_id'] for v in snap['vehicles']],
        'delivery_delay': [v['vehicle_id'] for v in snap['vehicles']],
        'warehouse_resource_failure': [r['resource_id'] for r in snap['resources']],
        'inventory_quarantine': [lot['batch_id'] for lot in snap.get('stock_lots', [])],
    }[spec.event_type]
    if not objects:
        raise HTTPException(status_code=422, detail='r30c_no_eligible_event_objects')
    raw = (spec.object_id or '').strip()
    # A named V002 belongs to PostgreSQL; the internal synthetic scenario uses veh_2.
    # This is an explicit demo alias, never an inferred physical vehicle identity.
    if raw.upper().startswith('V00') and raw[3:].isdigit() and spec.event_type in ('vehicle_breakdown', 'delivery_delay') and baseline['source'] == 'scenario_demo':
        raw = 'veh_' + str(int(raw[3:]))
    candidates = [raw] if raw else []
    if raw:
        prefixes = ('veh_', 'res_', 'bat_')
        if not raw.startswith(prefixes):
            candidates.extend([prefix + raw for prefix in prefixes])
        # Unambiguous match against actual snapshot IDs only; no phantom IDs.
        candidates.extend(x for x in objects if x.lower().endswith('_' + raw.lower()))
    oid = next((x for x in candidates if x in objects), None) if raw else None
    if raw and oid is None:
        raise HTTPException(status_code=422, detail='r30c_object_not_found_in_current_snapshot:' + raw[:60])
    if oid is None and spec.event_type in ('vehicle_breakdown', 'delivery_delay'):
        planned = {r['vehicle_id'] for r in plan['routing']['routes'] if len(r['stops']) > 1}
        oid = next((x for x in objects if x in planned), objects[0])
    oid = oid or objects[0]
    # The event time is in the actual computed plan, NEVER current wall clock.
    if spec.occurred_at_s is not None:
        at = spec.occurred_at_s
    elif spec.event_type in ('vehicle_breakdown', 'delivery_delay'):
        route = next((r for r in plan['routing']['routes'] if r['vehicle_id'] == oid), None)
        if not route or len(route['stops']) < 2:
            raise HTTPException(status_code=422, detail='r30c_vehicle_has_no_delivery_route_choose_active_vehicle')
        dep = route['stops'][0]['departure_at_s']
        first_arrival = route['stops'][1]['arrival_at_s']
        at = dep + max(1, (first_arrival - dep) // 2) if first_arrival > dep + 1 else dep
    else:
        # If stock/resource failure, trigger strictly before the first affected operation where possible.
        matching_ops = set()
        if spec.event_type == 'inventory_quarantine':
            affected_orders = {o['order_id'] for o in snap['orders'] if o['batch_id'] == oid}
            matching_ops = {op['operation_id'] for op in snap['operations']
                            if affected_orders.intersection(op['order_ids'])}
        work = [op for op in plan['warehouse']['operations']
                if (op['resource_id'] == oid if spec.event_type == 'warehouse_resource_failure'
                    else op['operation_id'] in matching_ops)]
        at = max(0, min((op['start_s'] for op in work), default=0) - 1)
    return oid, at


def _exception(request: Request, ctx: ChatRequest | QuickRequest, args: ExceptionArgs) -> dict:
    # R30-B itself recomputes the authoritative baseline and verifies it; this
    # first run is only to validate the target and select a real event time.
    original = _workflow(request, ctx)
    oid, at = _event_target(original, args)
    # Reuse the already verified R27 baseline: R30-B HTTP wrapper would run
    # the expensive joint solver a second time, slowing a meeting demo.
    from app.adapters.persistence.pg_r30b_reschedule import (
        ExceptionSpec, RescheduleInputError, run_reschedule,
    )
    try:
        full = run_reschedule(baseline=original, spec=ExceptionSpec(
            event_type=args.event_type, object_id=oid, occurred_at_s=at,
            delay_s=args.delay_s if args.event_type == 'delivery_delay' else 0,
        ), budget_ms=ctx.budget_ms)
    except (RescheduleInputError, RuntimeError, ValueError) as exc:
        raise HTTPException(status_code=422, detail=f'r30c_r30b_solver_or_validation_failed:{type(exc).__name__}') from None
    if full['verification']['status'] != 'passed' or full['database_mutated'] or full['business_plans_mutated']:
        raise HTTPException(status_code=422, detail='r30c_exception_verification_failed')
    return full


def _exception_summary(result: dict) -> dict:
    cmp = result['comparison']
    evidence = result.get('impact_evidence') or {}
    # The model gets bounded, proven event-based differences; it does not get
    # permission to interpret halted original route geometry as a new delivery.
    impacted = [x for x in evidence.get('orders', ()) if x.get('affected')]
    return {'tool': 'simulate_exception', 'status': 'verified_readonly', 'event': result['event'],
            'validation': result['verification']['status'],
            'baseline_r28': result['verification']['baseline_r28'],
            'suffix_accounting': result['verification']['suffix_accounting'],
            'delivered_before_event': cmp['delivered_before_event'],
            'forecast_delivered_total': cmp['forecast_delivered_total'],
            'unserved_total': cmp['unserved_total'],
            'unserved_orders': cmp['unserved_orders'][:20],
            'impact_counts': evidence.get('counts', {}),
            'affected_order_details': impacted[:25],
            'affected_details_truncated': len(impacted) > 25,
            'vehicle_delivery_forecasts': evidence.get('vehicles', [])[:12],
            'warehouse_operation_changes': evidence.get('warehouse_operation_changes', [])[:25],
            'evidence_limits': evidence.get('evidence_limits', []),
            'changed_vehicle_ids': cmp['changed_vehicle_ids'],
            'changed_warehouse_operations': len(cmp['changed_warehouse_operations']),
            'warnings': cmp['warnings'][:5], 'database_mutated': False,
            'route_accuracy': 'simulation_no_live_gps_or_road_conditions',
            'can_open_existing_3d_replay': True}


def _execute(name: str, args: dict, request: Request, ctx: ChatRequest | QuickRequest) -> tuple[dict, dict | None]:
    if name == 'get_business_status':
        if args:
            raise ValueError('get_business_status_accepts_no_parameters')
        return {'tool': name, 'status': 'read_only', **_overview(request, ctx)}, None
    if name == 'generate_joint_plan':
        if args:
            raise ValueError('generate_joint_plan_accepts_no_parameters')
        artifact = _workflow(request, ctx)
        return _plan_summary(artifact), {'kind': 'workflow', 'payload': artifact}
    if name == 'simulate_exception':
        spec = ExceptionArgs.model_validate(args)
        artifact = _exception(request, ctx, spec)
        return _exception_summary(artifact), {'kind': 'exception', 'payload': artifact}
    raise ValueError('r30c_unknown_tool')


def _error_text(exc: Exception) -> str:
    if isinstance(exc, HTTPException):
        return str(exc.detail)[:240]
    if isinstance(exc, ValueError):
        return str(exc)[:240]
    return '工具调用失败，请检查后端配置和模型参数'


@router.get('/status')
def status(request: Request):
    pg._check_access(request)
    return {'mode': 'r30c_local_readonly_deepseek', 'allowed_tools': [t['function']['name'] for t in TOOLS],
            'database_writes': False, **model_status()}


@router.post('/quick')
def quick(request: Request, body: QuickRequest):
    pg._check_access(request)
    args = body.model_dump(include={'event_type','object_id','occurred_at_s','delay_s'}, exclude_none=True) if body.action == 'simulate_exception' else {}
    result, artifact = _execute(body.action, args, request, body)
    return {'mode': 'direct_algorithm_fallback_not_ai', 'answer': '直接调用后端完成只读操作（未使用大模型推理）。',
            'calls': [result], 'artifact': artifact}


@router.post('/chat')
def chat(request: Request, body: ChatRequest):
    pg._check_access(request)
    if not model_status()['configured']:
        raise HTTPException(status_code=503, detail='deepseek_key_not_configured_use_server_env_or_quick_action')
    gateway = DeepSeekGateway()
    messages = [{'role': 'system', 'content': build_prompt()}]
    messages.extend({'role': turn.role, 'content': turn.content} for turn in body.history[-6:])
    messages.append({'role': 'user', 'content': body.message + '\n[系统选定来源: ' + body.source + ', 温区: ' + body.temperature_zone + '] '})
    calls: list[dict] = []
    artifact = None
    for _ in range(3):
        try:
            completion = gateway.complete(messages, TOOLS)
        except ModelUnavailable as exc:
            raise HTTPException(status_code=502, detail=str(exc)) from None
        tool_calls = completion.get('tool_calls') or []
        if not tool_calls:
            answer = str(completion.get('content') or '').strip()
            if not answer:
                answer = '模型未生成可显示的回答，请检查 API 配置。'
            # Model text is never proof that a solver ran; UI separately displays calls.
            return {'mode': 'deepseek_tool_calling', 'answer': answer[:3500],
                    'calls': calls, 'artifact': artifact, 'model': gateway.model}
        messages.append({'role': 'assistant', 'content': completion.get('content'), 'tool_calls': tool_calls})
        for call in tool_calls[:3]:
            name = str(call.get('function', {}).get('name') or '')
            try:
                params = json.loads(call.get('function', {}).get('arguments') or '{}')
                if not isinstance(params, dict):
                    raise ValueError('tool_parameters_must_be_object')
                result, produced = _execute(name, params, request, body)
                if produced is not None:
                    artifact = produced
            except Exception as exc:
                result = {'tool': name[:60], 'status': 'failed', 'error': _error_text(exc)}
            calls.append(result)
            messages.append({'role': 'tool', 'tool_call_id': str(call.get('id') or ''),
                             'name': name, 'content': json.dumps(result, ensure_ascii=False, default=str)})
    # Bounded turns; a verified tool result is still available if follow-up text failed.
    return {'mode': 'deepseek_tool_calling', 'answer': '模型工具调用达到演示轮次上限，请查看下方真实工具执行结果。',
            'calls': calls, 'artifact': artifact, 'model': gateway.model}
