"""Bounded DeepSeek tool collaboration for the synthetic breakdown demonstration.

The model only selects read/solve/compare tools. The server supplies all evidence,
executes the unmodified OR-Tools solver, checks tool order, and never approves.
No database writes, no invented routes, no approval side effects.
"""
from __future__ import annotations

import json

from logistics_agents.llm import ChatMessage
from logistics_backend.application import fault_rescue_showcase as fixture

TOOL_SEQUENCE = ('get_incident_context', 'solve_rescue_dispatch', 'compare_rescue_plans')
TOOL_DEFS = tuple({
    'type': 'function',
    'function': {
        'name': name,
        'description': description,
        'parameters': {'type': 'object', 'additionalProperties': False, 'properties': {}, 'required': []},
    },
} for name, description in (
    ('get_incident_context', '读取固定三车八单场景中故障车辆、故障时刻、交接点、待接管订单、其他车辆和容量'),
    ('solve_rescue_dispatch', '调用真实 OR-Tools RoutingModel 计算跨车交接与配送路线，不批准方案'),
    ('compare_rescue_plans', '对比真实求解结果与故障后不救援的交付、费用、里程和迟到数据'),
))
SYSTEM = (
    '你是冷链调度系统的受控异常处置智能体。必须按顺序分别调用工具：'
    'get_incident_context、solve_rescue_dispatch、compare_rescue_plans；每次只调用一个工具，'
    '工具参数必须是空对象 {}。只能根据工具返回的事实做判断，不能写调度路线、车辆位置、'
    '交付率或收益，不能批准或修改数据库。即使工具显示求解无解也要调用 compare_rescue_plans 获取状态。'
    '所有工具调用由后端审核后执行。最后用简洁中文给操作员解释异常、接管结果及审批注意事项。'
)


def _context() -> dict:
    baseline, time_s = fixture._baseline()
    return {
        'case_id': 'wenchang-three-truck-breakdown-v1',
        'incident': {'kind': 'vehicle_breakdown', 'vehicle_id': fixture.VEHICLES[1],
                     'at_s': time_s, 'handoff_node': fixture.HANDOFF, 'vehicle_unavailable': True},
        'vehicles': [{'vehicle_id': vehicle, 'capacity': fixture.VEHICLE_CAPACITY,
                      'planned_orders': list(orders)} for vehicle, orders in fixture.ROUTES.items()],
        'rescue_orders': ['demo-o4', 'demo-o5'],
        'constraints': {'pickup_before_delivery': True, 'freeze_completed_stops': True,
                        'hard_horizon_s': fixture.HORIZON, 'soft_due_s': dict(fixture.SOFT_DUES),
                        'travel_speed_mps': fixture.METERS_PER_SECOND},
        'delivery_status': {'completed_at_failure': [s['node_id'] for s in baseline[fixture.VEHICLES[1]]['stops']
                                                     if s['kind'] == 'delivery' and s['departure_s'] <= time_s]},
        'synthetic_demo': True,
    }


def _comparison(rescue: dict) -> dict:
    metrics = rescue.get('metrics') or {}
    stranded = metrics.get('no_rescue') or {}
    candidate = metrics.get('candidate') if rescue.get('candidate_valid') and rescue.get('status') == 'solved' else None
    return {
        'solver_status': rescue.get('status'), 'candidate_valid': rescue.get('candidate_valid', False),
        'failure_reason': rescue.get('reason'), 'no_rescue': stranded,
        'candidate': candidate,
        'recovered_orders': rescue.get('recovered_orders') if candidate else None,
        'cost_delta_cents': candidate['objective_cents'] - stranded['objective_cents'] if candidate else None,
        'distance_delta_m': candidate['distance_m'] - stranded['distance_m'] if candidate else None,
        'approval_required': True, 'approval_performed': False,
        'note': '原计划仅作参考；恢复订单是主要指标，费用和里程变化不得声称必然改善。',
    }


def collaborate(provider, budget_ms: int = 1800) -> dict:
    """Returns evidence and tool trace, never an auto-approved decision.

    A missing key or a failed model tool call MUST NOT be described as AI success.
    Existing manual OR-Tools endpoint remains the explicit fallback.
    """
    trace: list[dict] = []
    output = {'ai_status': 'model_unavailable', 'model': None, 'reply': '',
              'tool_trace': trace, 'rescue': None, 'comparison': None,
              'approval_required': True, 'approval_performed': False}
    if not provider.configured:
        output['error_code'] = 'deepseek_not_configured'
        return output

    messages = [ChatMessage('system', SYSTEM),
                ChatMessage('user', '请分析冷藏车02发生故障的三车八单场景，按顺序调用工具完成救援求解和方案对比。')]
    for expected in TOOL_SEQUENCE:
        try:
            reply = provider.complete(tuple(messages), tools=TOOL_DEFS)
            output['model'] = reply.model
        except Exception:
            output.update(ai_status='model_failed', error_code='deepseek_request_failed')
            return output
        calls = reply.tool_calls
        if len(calls) != 1 or calls[0].name != expected:
            output.update(ai_status='model_invalid_tool_call', error_code=f'expected_{expected}')
            return output
        call = calls[0]
        try:
            args = json.loads(call.arguments)
        except (TypeError, ValueError):
            args = None
        if args != {}:
            output.update(ai_status='model_invalid_tool_call', error_code='invalid_tool_arguments')
            return output
        if expected == 'get_incident_context':
            result = _context()
        elif expected == 'solve_rescue_dispatch':
            try:
                result = fixture.solve_breakdown_showcase(budget_ms)
            except Exception:
                output.update(ai_status='solver_failed', error_code='rescue_solver_failed')
                return output
            output['rescue'] = result
        else:
            result = _comparison(output['rescue'])
            output['comparison'] = result
        trace.append({'tool': expected, 'requested_by': 'deepseek_function_call',
                      'executed_by': 'backend', 'ok': True, 'model': reply.model})
        messages.append(ChatMessage('assistant', reply.content, tool_calls=calls))
        # Avoid feeding full routes / coordinates to the LLM; use verified, bounded evidence.
        safe_result = result
        if expected == 'solve_rescue_dispatch':
            safe_result = {'solver': result['solver'], 'status': result['status'],
                           'candidate_valid': result['candidate_valid'], 'reason': result.get('reason'),
                           'rescue_assignments': result.get('rescue_assignments'),
                           'recovered_orders': result.get('recovered_orders')}
        messages.append(ChatMessage('tool', json.dumps(safe_result, ensure_ascii=False, default=str)[:9000],
                                    tool_call_id=call.id, name=expected))
    try:
        final = provider.complete(tuple(messages))
        if final.tool_calls or not final.content.strip():
            raise ValueError('unexpected_final_model_response')
        output.update(ai_status='model_success', model=final.model,
                      reply=final.content.strip()[:4500], error_code=None)
    except Exception:
        output.update(ai_status='model_explanation_failed', error_code='deepseek_explanation_failed')
    return output
