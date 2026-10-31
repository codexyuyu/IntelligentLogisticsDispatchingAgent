"""Auditable natural-language dispatch workflow. All actual routes are solver-produced.

Current supported actions:
* joint_dispatch: solve the SAME checked scenario again; no invisible custom constraints.
* delay_replan: preview a real midroad incident on an existing simulation.

The user must explicitly approve a checked result. Approval only activates a
simulation version, never changes operational schedules, GPS or inventory.
"""
from __future__ import annotations

import json
from datetime import UTC, datetime
from uuid import UUID, uuid4

from sqlalchemy import select, update
from sqlalchemy.dialects.postgresql import insert

from logistics_agents.llm import ChatMessage
from logistics_backend.errors import ServiceError
from logistics_backend.persistence.dispatch_task_models import dispatch_tasks
from logistics_contracts.integration import IntegrationRun
from logistics_domain.states import ErrorCode

_TOOL = {'type': 'function', 'function': {
    'name': 'parse_dispatch_intent',
    'description': 'Extract only a supported intent, no fictitious IDs or invented priorities. If user requests specific unimplemented constraints, choose unsupported.',
    'parameters': {'type': 'object', 'additionalProperties': False,
        'properties': {
            'action': {'type': 'string', 'enum': ['joint_dispatch', 'delay_replan', 'unsupported']},
            'vehicle_id': {'type': 'string', 'description': 'Explicit known UUID only, for delay_replan'},
            'time_s': {'type': 'integer', 'minimum': 0, 'maximum': 604800},
            'delay_s': {'type': 'integer', 'minimum': 1, 'maximum': 3600},
            'reason': {'type': 'string', 'maxLength': 150}},
        'required': ['action']}}}

_SYSTEM = ("你是冷链调度指令解析器，必须调用 parse_dispatch_intent。只识别两种明确受支持的任务："
    "joint_dispatch = 按当前已校验场景的全部现有订单/车辆/仓储和原有成本时效约束重新求解；"
    "delay_replan = 当前已启动的模拟中，一辆已有车辆在明确时刻发生明确秒数的延误，需要预览局部重规划。"
    "用户要求指定新的目的地、指派指定车辆配送指定订单、增加订单、调整温控限值、改变目标权重、优先特定订单、真实车辆派车、"
    "或者没有明确必要参数时，必须 unsupported；禁止假装支持。"
    "对于 delay_replan，只从用户文本中提取真实给出的车辆 UUID、time_s 和 delay_s，缺失则 unsupported。"
    "不要伪造 UUID、道路、求解结果。不得自行批准。")


def parse_intent(message: str, provider) -> tuple[dict, str]:
    """DeepSeek function-call extraction, or an explicit conservative offline grammar."""
    if provider.configured:
        reply = provider.complete((ChatMessage('system', _SYSTEM), ChatMessage('user', message)), tools=(_TOOL,))
        calls = [c for c in reply.tool_calls if c.name == 'parse_dispatch_intent']
        if len(calls) != 1:
            raise ServiceError(ErrorCode.INVALID_INPUT, '自然语言指令无法提取为可执行任务，请补充调度要求')
        try:
            obj = json.loads(calls[0].arguments)
        except (TypeError, ValueError) as exc:
            raise ServiceError(ErrorCode.INVALID_INPUT, '模型返回的任务结构无效') from exc
        parser = 'deepseek_tool_call'
    else:
        # Explicitly reported as rule_based, never pretend LLM reasoning ran.
        import re
        m = re.search(r'(?:延误|晚点)\s*(\d+)\s*秒', message)
        vehicle = re.search(r'[0-9a-fA-F]{8}(?:-[0-9a-fA-F]{4}){3}-[0-9a-fA-F]{12}', message)
        at = re.search(r'(?:第|在)\s*(\d+)\s*秒', message)
        if m and vehicle and at:
            obj = {'action': 'delay_replan', 'vehicle_id': vehicle.group(),
                   'time_s': int(at.group(1)), 'delay_s': int(m.group(1))}
        elif any(word in message for word in ('联合调度', '联合求解', '重新求解', '全场景调度')) and not any(
            word in message for word in ('指定', '去往', '送到', '优先', '最紧', '某订单', '某地点', '地址', '派一辆', '派车到')):
            obj = {'action': 'joint_dispatch'}
        else:
            obj = {'action': 'unsupported'}
        parser = 'rule_based'
    if not isinstance(obj, dict) or obj.get('action') not in ('joint_dispatch', 'delay_replan', 'unsupported'):
        raise ServiceError(ErrorCode.INVALID_INPUT, '任务类型无效')
    action = obj['action']
    if action == 'unsupported':
        raise ServiceError(ErrorCode.INVALID_INPUT,
            '当前仅支持“按现有场景重新联合求解”或“指定车辆、发生秒数、延误秒数的模拟局部重规划”；其他调度约束尚不支持')
    if action == 'joint_dispatch':
        if set(obj) - {'action', 'reason'}:
            raise ServiceError(ErrorCode.INVALID_INPUT, '联合求解不支持指定车辆、时刻或新目的地')
        if any(word in message for word in ('指定车辆', '指定订单', '指定地点', '新地址', '新地点', '优先某', '只用一辆', '指派到')):
            raise ServiceError(ErrorCode.INVALID_INPUT, '当前联合求解只复用已校验场景的原有约束，不能新增单车指派或目的地')
        return {'action': action, 'constraints': 'unchanged_checked_scenario'}, parser
    try:
        if set(obj) - {'action', 'vehicle_id', 'time_s', 'delay_s', 'reason'}:
            raise ValueError('extra args')
        vehicle_id = str(UUID(obj['vehicle_id']))
        time_s, delay_s = obj['time_s'], obj['delay_s']
        if type(time_s) is not int or not 0 <= time_s <= 604800 or type(delay_s) is not int or not 1 <= delay_s <= 3600:
            raise ValueError('out of range')
    except (ValueError, KeyError, TypeError) as exc:
        raise ServiceError(ErrorCode.INVALID_INPUT, '车辆延误必须提供有效车辆 UUID、发生秒数和延误秒数') from exc
    return {'action': action, 'vehicle_id': vehicle_id, 'time_s': time_s, 'delay_s': delay_s}, parser


class NaturalDispatchService:
    def __init__(self, integration, simulation, provider, uow_factory):
        self.integration, self.simulation, self.provider = integration, simulation, provider
        self.uow_factory = uow_factory

    def _row(self, task_id, actor, *, lock=False):
        with self.uow_factory() as uow:
            stmt = select(dispatch_tasks).where(dispatch_tasks.c.id == task_id,
                dispatch_tasks.c.scope_id == actor.scope_id)
            row = uow.connection.execute(stmt.with_for_update() if lock else stmt).mappings().first()
        if row is None:
            raise ServiceError(ErrorCode.NOT_FOUND, '调度任务不存在')
        return dict(row)

    def _save(self, row, actor, **values):
        """CAS prevents stale approvals; the version never silently overwrites."""
        now = datetime.now(UTC)
        with self.uow_factory() as uow:
            changed = uow.connection.execute(update(dispatch_tasks).where(
                dispatch_tasks.c.id == row['id'], dispatch_tasks.c.scope_id == actor.scope_id,
                dispatch_tasks.c.row_version == row['row_version']).values(
                **values, row_version=row['row_version'] + 1, updated_at=now)
                .returning(dispatch_tasks.c.id)).first()
        if changed is None:
            raise ServiceError(ErrorCode.RESOURCE_CONFLICT, '调度任务已由其他操作更新，请刷新')
        return self.get(row['id'], actor)

    def create(self, command, actor):
        checked = self.integration.get(command.run_id, actor)
        if checked.get('status') != 'checked' or not (checked.get('joint_validation') or {}).get('valid'):
            raise ServiceError(ErrorCode.UNVERIFIED_SOLVER_RESULT, '请先选择已校验通过的联合运行')
        intent, parser = parse_intent(command.message, self.provider)
        if intent['action'] == 'delay_replan':
            sim = self.simulation.get(command.run_id, actor)
            if sim.get('incident'):
                raise ServiceError(ErrorCode.RESOURCE_CONFLICT, '此模拟已有异常，请切换到新的运行')
            from logistics_backend.application.timeline import state_at_time
            state = state_at_time({'events': sim['events']}, checked, intent['time_s'])
            if intent['vehicle_id'] not in state.get('in_transit_vehicle_ids', ()):
                raise ServiceError(ErrorCode.INVALID_INPUT, '该车辆在指定时刻不处于在途状态')
        task_id, now = uuid4(), datetime.now(UTC)
        with self.uow_factory() as uow:
            uow.connection.execute(insert(dispatch_tasks).values(
                id=task_id, scope_id=actor.scope_id, actor_id=actor.actor_id,
                source_run_id=command.run_id, candidate_run_id=None,
                status='draft', row_version=0, created_at=now, updated_at=now,
                instruction=command.message, intent=intent, parser=parser, evidence={}))
        return self.get(task_id, actor)

    def get(self, task_id, actor):
        row = self._row(task_id, actor)
        # Solve state is sourced from the real worker, not inferred from local timers.
        if row['status'] == 'solving' and row['candidate_run_id']:
            result = self.integration.get(row['candidate_run_id'], actor)
            if result.get('status') == 'checked' and (result.get('joint_validation') or {}).get('valid'):
                return self._save(row, actor, status='ready', evidence=self._joint_evidence(result))
            if result.get('status') not in ('queued', 'running'):
                return self._save(row, actor, status='failed', evidence={
                    'reason': result.get('reason') or result.get('error') or result.get('status')})
        return self._view(row)

    @staticmethod
    def _view(row):
        return {'task_id': str(row['id']), 'source_run_id': str(row['source_run_id']),
            'candidate_run_id': str(row['candidate_run_id']) if row['candidate_run_id'] else None,
            'status': row['status'], 'row_version': row['row_version'],
            'instruction': row['instruction'], 'intent': row['intent'], 'evidence': row['evidence'],
            'parser': row['parser'], 'incident_id': str(row['incident_id']) if row['incident_id'] else None}

    @staticmethod
    def _joint_evidence(result):
        return {'status': result.get('status'), 'joint_validation': result.get('joint_validation'),
            'observations': result.get('observations'),
            'candidate': result.get('candidate'),
            'transport_solution': result.get('transport_solution'),
            'source_kind': result.get('source_kind'),
            'result_kind': 'checked_joint_solver_run',
            'notice': '复用当前场景全部约束与订单；未按自然语言修改指定车辆、目标或订单优先级'}

    def preview(self, task_id, actor, expected_row_version):
        row = self._row(task_id, actor)
        if row['row_version'] != expected_row_version or row['status'] != 'draft':
            raise ServiceError(ErrorCode.RESOURCE_CONFLICT, '候选任务已提交或版本已变更')
        intent = row['intent']
        if intent['action'] == 'joint_dispatch':
            # Real OR-Tools worker job; idempotent on task UUID even after retries.
            source = self.integration.get(row['source_run_id'], actor)
            scenario_id = UUID(source['request']['scenario_id'])
            from logistics_contracts.integration import IntegrationRun
            request = IntegrationRun(scenario_id=scenario_id,
                seed=int(source['request'].get('seed', 0)),
                budget_ms=int(source['request'].get('budget_ms', 4000)))
            receipt = self.integration.run(request, actor,
                f'nl-dispatch-{task_id}', wait=False)
            run_id = UUID(receipt['run_id'])
            return self._save(row, actor, status='solving', candidate_run_id=run_id,
                evidence={'status': receipt.get('status'), 'result_kind': 'joint_solver_job',
                          'notice': '重新求解原场景；未添加未支持的特殊优先约束'})
        sim = self.simulation.get(row['source_run_id'], actor)
        if sim.get('incident'):
            raise ServiceError(ErrorCode.RESOURCE_CONFLICT, '已有异常，不能重复创建候选')
        args = intent
        checked = self.integration.get(row['source_run_id'], actor)
        projection = self.simulation.project_delay(checked, sim,
            args['vehicle_id'], args['time_s'], args['delay_s'], 2000,
            str(task_id))
        if not projection.get('proposal_valid'):
            raise ServiceError(ErrorCode.UNVERIFIED_SOLVER_RESULT, '候选方案未通过约束校验')
        evidence = {'status': 'checked', 'strategy': projection.get('strategy'),
            'route_changed': projection.get('route_changed'),
            'comparison': projection.get('comparison'),
            'local_solver': projection.get('local_solver'),
            'impact': projection.get('impact'),
            'candidate_stops': [t.get('stops', ()) for t in projection.get('candidate_tracks', ())
                if t.get('vehicle_id') == args['vehicle_id']],
            'result_kind': 'simulation_delay_projection',
            'notice': '只读候选投影；审批后仅切换模拟版本，不向真实车辆下发命令'}
        return self._save(row, actor, status='ready', evidence=evidence)

    def decide(self, task_id, actor, expected_row_version, approved, trace_id):
        row = self._row(task_id, actor)
        if row['row_version'] != expected_row_version or row['status'] != 'ready':
            raise ServiceError(ErrorCode.RESOURCE_CONFLICT, '任务不在待审批状态或审批版本已变化')
        if not approved:
            return self._save(row, actor, status='rejected')
        if row['intent']['action'] == 'joint_dispatch':
            checked = self.integration.get(row['candidate_run_id'], actor)
            if checked.get('status') != 'checked' or not (checked.get('joint_validation') or {}).get('valid'):
                raise ServiceError(ErrorCode.UNVERIFIED_SOLVER_RESULT, '候选联合方案未通过独立校验')
            simulation = self.simulation.start(row['candidate_run_id'], actor)
            return self._save(row, actor, status='approved', evidence={
                **row['evidence'], 'simulation_id': simulation.get('simulation_id'),
                'active_version': simulation.get('active_version', 0)})
        from logistics_backend.api.integration import SimulationIncidentInput
        intent = row['intent']
        # The current simulation enforces one incident; retry uses a stable source_event_id.
        incident = self.simulation.incident(row['source_run_id'], SimulationIncidentInput(
            vehicle_id=UUID(intent['vehicle_id']), time_s=intent['time_s'], delay_s=intent['delay_s'],
            source_event_id=f'agent-{task_id}', reason='人工批准的 Agent 模拟延误方案', budget_ms=2000),
            actor, trace_id)
        if not incident.get('proposal_valid'):
            raise ServiceError(ErrorCode.UNVERIFIED_SOLVER_RESULT, '实际登记的候选方案不符合硬约束')
        # Guard against changed candidate between preview and approval.
        if incident.get('strategy') != row['evidence'].get('strategy') or \
                incident.get('route_changed') != row['evidence'].get('route_changed') or \
                incident.get('comparison') != row['evidence'].get('comparison'):
            raise ServiceError(ErrorCode.RESOURCE_CONFLICT, '登记时路线决策已变化，请在异常处置页重新检查')
        decided = self.simulation.decide(row['source_run_id'], UUID(incident['id']),
            'approved', actor, incident['row_version'])
        return self._save(row, actor, status='approved', incident_id=UUID(incident['id']),
            evidence={**row['evidence'], 'incident_id': incident['id'],
                      'active_version': 1, 'approval_status': decided['status']})

    def list(self, actor, limit=15):
        with self.uow_factory() as uow:
            rows = uow.connection.execute(select(dispatch_tasks).where(
                dispatch_tasks.c.scope_id == actor.scope_id).order_by(
                dispatch_tasks.c.created_at.desc()).limit(limit)).mappings().all()
        return {'items': [self._view(r) for r in rows]}
