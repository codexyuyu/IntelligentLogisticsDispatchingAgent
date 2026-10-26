"""R19 / B-04 three-strategy rescheduling comparison on one pre-registered event set.

Arms, all starting from the *same* baseline plan and the *same* event:
  no_reschedule    keep the plan; the affected vehicle departs exactly delay_s late
  full_reschedule  re-solve everything (CP-SAT + Routing) on the post-event snapshot
  local_reschedule B-04 path: lock unaffected routes, replan only the affected scope

Discipline inherited from R17/R18: pre-registered scenarios and a deterministic
event-selection rule, the two solving arms get the same total budget, every arm's
raw plan and failure is retained, metrics are recomputed independently from the
produced plans instead of trusting solver-reported numbers, and no percentage is
published when the arms are not comparable.

Execute from the backend directory:
  python -m tools.r19_reschedule_ablation --dry-run
  python -m tools.r19_reschedule_ablation --budget-ms 90000
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from time import perf_counter
from uuid import uuid4

from app.application.coordinator import coordinate
from app.application.handle_event import _derive_snapshot_for_event, handle_event
from app.application.runtime import runtime
from app.contracts.common import Source, ValidationReport
from app.contracts.entities import PlanningSnapshot
from app.contracts.events import DispatchEvent, EventPayload, SimulationRequest
from app.contracts.planning import CandidatePlan
from app.domain.plan_rules import validate_plan
from app.domain.transport_rules import validate_transport

from tools.r17_joint_ablation import load_snapshot
from tools.r18_multiscene_ablation import prepare_case

PROTOCOL = 'r19-b04-reschedule-strategies-1.0'
# Pre-registered cases (reused R18 stratified generator: warehouse x temperature).
CASE_DESIGNS = ((12, 17), (16, 42), (20, 66))
ARMS = ('no_reschedule', 'full_reschedule', 'local_reschedule')
# Pre-registered delay ladder. A delay only bites when it pushes the vehicle past its
# planned departure, so the ladder is chosen from the *scenario's own time scale* rather
# than from an outcome: the base family absorbs up to ~8 h (service window 28800 s) and the
# stress family up to ~4 h (14400 s), so the ladder spans 15 min to 8 h and crosses both.
DELAY_LADDER_S = (900, 3600, 14400, 28800)
OCCURRED_AT_S = 0
HORIZON_S = 1800
SIMPY_CHECK_CASE = 's20_seed66'
# Scenario families. 'base' keeps the R18 snapshot untouched (continuity with R17/R18).
# 'stress' compresses every service window and freshness deadline by this factor and adds one
# same-zone spare vehicle per warehouse, because the base family has a single vehicle per
# (warehouse, temperature zone) and 8-hour windows, which leaves a departure delay with zero
# reassignment freedom. Both families are reported in full; neither replaces the other.
FAMILIES = ('base', 'stress')
WINDOW_COMPRESSION_FACTOR = 2
SCOPE = ('synthetic equal-budget strategy comparison; not empirical county-level performance, '
         'not a significance test, and not a replacement for the accepted R17/R18 evidence')
RULES = ('统一基线：同一场景、同一族内的全部延误档共享同一基线方案；两个求解臂在每一档使用相同总预算；'
         '不重调度臂不消耗求解预算（其定义就是不重算），其代价体现在违约与延误上。')
VEHICLE_RULE = ('受影响车辆 = 基线方案中服务订单最多的车辆；并列时取 vehicle_id 字典序最小者'
                '（规则先于运行确定，不看结果）。')
DELAY_RULE = ('有效延误 = max(0, 事件后车辆可用时刻 − 基线计划发车时刻)：若车辆本就晚于该时刻发车，'
              '延误被班次表吸收，不重调度臂不发生任何位移。原始延误与有效延误同时记录。')
FAMILY_RULE = (f'base = R18 生成器原样快照；stress = 同订单同路网，服务时间窗与保鲜期限压缩 '
               f'1/{WINDOW_COMPRESSION_FACTOR}，并为每个（仓库×温区）增加一辆同型备用车。'
               '两族全部结果都报告，不挑选有利族。')


def sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def sha256_file(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def write_json_line(path: Path, payload) -> None:
    """Explicit LF: Windows text mode would emit CRLF and change published hashes."""
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + '\n', encoding='utf8', newline='\n')


def reset_runtime() -> None:
    """Each arm must start from the same runtime state; B-04 stores snapshots there."""
    runtime.snapshots.clear()
    runtime.snapshot_history.clear()
    runtime.plans.clear()
    runtime.reschedules.clear()


def choose_event_vehicle(plan: CandidatePlan) -> tuple[str, int]:
    """Deterministic pre-registered rule; never inspects outcomes."""
    counts = {}
    for route in plan.routing.routes:
        counts[route.vehicle_id] = sum(
            len(stop.order_ids) for stop in route.stops if stop.stop_kind == 'delivery'
        )
    if not counts:
        raise ValueError('baseline plan has no routes to target')
    vehicle_id = sorted(counts.items(), key=lambda item: (-item[1], item[0]))[0][0]
    return vehicle_id, counts[vehicle_id]


def build_event(*, case: str, snapshot: PlanningSnapshot, vehicle_id: str, delay_s: int) -> DispatchEvent:
    return DispatchEvent(
        event_id=f'evt_r19_{case}_{delay_s}',
        event_type='departure_delayed',
        snapshot_id=snapshot.snapshot_id,
        expected_snapshot_version=snapshot.version,
        object_id=vehicle_id,
        occurred_at_s=OCCURRED_AT_S,
        received_at=datetime.now(timezone.utc),
        source=Source(source_kind='simulation', source_ref=f'synthetic:r19:{case}:{delay_s}',
                      observed_at=datetime.now(timezone.utc), rule_version='r19-1.0'),
        payload=EventPayload(delay_s=delay_s),
    )


def planned_departure_s(plan: CandidatePlan, vehicle_id: str) -> int:
    for route in plan.routing.routes:
        if route.vehicle_id == vehicle_id and route.stops:
            return route.stops[0].departure_at_s
    raise ValueError(f'baseline plan has no departure for vehicle {vehicle_id}')


def effective_delay_s(*, derived: PlanningSnapshot, vehicle_id: str, planned_departure: int) -> int:
    """A delay only moves the route when it pushes availability past the planned departure."""
    available = next(v.available_at_s for v in derived.vehicles if v.vehicle_id == vehicle_id)
    return max(0, available - planned_departure)


def plan_hash_for(snapshot: PlanningSnapshot, version: int, routing, warehouse) -> str:
    payload = {
        'snapshot_id': snapshot.snapshot_id, 'snapshot_version': snapshot.version,
        'version': version, 'routing': routing.model_dump(mode='json'),
        'warehouse': warehouse.model_dump(mode='json'),
    }
    return hashlib.sha256(json.dumps(payload, ensure_ascii=False, sort_keys=True,
                                     separators=(',', ':')).encode()).hexdigest()


def apply_no_reschedule(*, baseline_plan: CandidatePlan, derived: PlanningSnapshot,
                        vehicle_id: str, delay_s: int) -> CandidatePlan:
    """Pure delay propagation: same sequence, every timestamp of that route moves later.

    ``delay_s`` is the *effective* delay, so a vehicle that already departs after its
    post-event availability keeps its original schedule.
    """
    def shift_stop(stop):
        return stop.model_copy(update={
            'arrival_at_s': stop.arrival_at_s + delay_s,
            'service_start_at_s': stop.service_start_at_s + delay_s,
            'departure_at_s': stop.departure_at_s + delay_s,
        })

    routes = tuple(
        route.model_copy(update={'stops': tuple(shift_stop(s) for s in route.stops)})
        if route.vehicle_id == vehicle_id else route
        for route in baseline_plan.routing.routes
    )
    arrivals = tuple(
        arrival.model_copy(update={'arrival_at_s': arrival.arrival_at_s + delay_s})
        if arrival.vehicle_id == vehicle_id else arrival
        for arrival in baseline_plan.routing.warehouse_arrivals
    )
    routing = baseline_plan.routing.model_copy(update={
        'routes': routes, 'warehouse_arrivals': arrivals,
        'snapshot_id': derived.snapshot_id, 'snapshot_version': derived.version,
    })
    version = baseline_plan.version + 1
    return CandidatePlan(
        plan_id=f'plan_{uuid4().hex[:20]}',
        snapshot_id=derived.snapshot_id, snapshot_version=derived.version, version=version,
        plan_hash=plan_hash_for(derived, version, routing, baseline_plan.warehouse),
        routing=routing, warehouse=baseline_plan.warehouse,
        validation=ValidationReport(
            status='not_checked',
            validator_version='r19-no-reschedule-carried-over-1.0',
            checked_rule_ids=('r19.baseline.carried_over',), violations=(),
        ),
    )


def order_vehicle_map(plan: CandidatePlan) -> dict[str, str]:
    mapping = {}
    for route in plan.routing.routes:
        for stop in route.stops:
            if stop.stop_kind == 'delivery':
                for order_id in stop.order_ids:
                    mapping[order_id] = route.vehicle_id
    return mapping


def plan_metrics(*, plan: CandidatePlan, snapshot: PlanningSnapshot,
                 baseline_plan: CandidatePlan, wall_ms: int) -> dict:
    """Recompute every reported number from the plan itself."""
    orders = {o.order_id: o for o in snapshot.orders}
    rows = []
    for route in plan.routing.routes:
        for stop in route.stops:
            if stop.stop_kind != 'delivery':
                continue
            for order_id in stop.order_ids:
                order = orders[order_id]
                window_end = order.service_window.end_s
                rows.append({
                    'order_id': order_id, 'vehicle_id': route.vehicle_id,
                    'service_start_s': stop.service_start_at_s, 'departure_at_s': stop.departure_at_s,
                    'service_window_end_s': window_end,
                    'freshness_deadline_s': order.freshness_deadline_s,
                    'on_time': stop.service_start_at_s <= window_end,
                    'freshness_ok': stop.departure_at_s <= order.freshness_deadline_s,
                    'lateness_s': max(0, stop.service_start_at_s - window_end),
                })
    served = [r['order_id'] for r in rows]
    required = [o.order_id for o in snapshot.orders if o.required]
    baseline_map = order_vehicle_map(baseline_plan)
    arm_map = {r['order_id']: r['vehicle_id'] for r in rows}
    changed_orders = sorted(oid for oid in required
                            if baseline_map.get(oid) != arm_map.get(oid))
    ready = {h.order_id: h.ready_at_s for h in plan.warehouse.warehouse_handoffs}
    waits = [max(0, r['departure_at_s'] - ready.get(r['order_id'], 0)) for r in rows]
    baseline_distance = sum(r.distance_m for r in baseline_plan.routing.routes)
    distance = sum(r.distance_m for r in plan.routing.routes)
    duration = sum(r.duration_s for r in plan.routing.routes)
    baseline_duration = sum(r.duration_s for r in baseline_plan.routing.routes)
    lateness = [r['lateness_s'] for r in rows]
    changed_vehicles = ({baseline_map.get(o) for o in changed_orders}
                        | {arm_map.get(o) for o in changed_orders}) - {None}
    return {
        'served_order_count': len(served),
        'unserved_order_ids': sorted(set(required) - set(served)),
        'duplicate_order_ids': sorted({oid for oid in served if served.count(oid) > 1}),
        'on_time_count': sum(r['on_time'] for r in rows),
        'on_time_rate': round(sum(r['on_time'] for r in rows) / len(rows), 4) if rows else None,
        'freshness_ok_count': sum(r['freshness_ok'] for r in rows),
        'late_order_count': sum(1 for r in rows if not r['on_time']),
        'max_lateness_s': max(lateness) if lateness else 0,
        'total_lateness_s': sum(lateness),
        'total_handoff_wait_s': sum(waits),
        'max_handoff_wait_s': max(waits) if waits else 0,
        'total_distance_m': distance, 'distance_delta_m': distance - baseline_distance,
        'total_route_duration_s': duration, 'route_duration_delta_s': duration - baseline_duration,
        'changed_order_count': len(changed_orders), 'changed_order_ids': changed_orders,
        'changed_vehicle_count': len(changed_vehicles),
        'changed_vehicle_ids': sorted(changed_vehicles),
        'wall_ms': wall_ms,
        'deliveries': sorted(rows, key=lambda r: r['order_id']),
    }


def independent_validation(*, plan: CandidatePlan, snapshot: PlanningSnapshot,
                           order_ids: tuple[str, ...]) -> dict:
    """Warehouse-scoped independent transport check plus full cross-domain plan check."""
    orders = {o.order_id: o for o in snapshot.orders}
    vehicles_by_warehouse: dict[str, set[str]] = {}
    for vehicle in snapshot.vehicles:
        vehicles_by_warehouse.setdefault(vehicle.warehouse_id, set()).add(vehicle.vehicle_id)
    groups: dict[str, list[str]] = {}
    for order_id in order_ids:
        groups.setdefault(orders[order_id].warehouse_id, []).append(order_id)

    transport = []
    for warehouse_id, ids in sorted(groups.items()):
        scoped = set(ids)
        vehicles = vehicles_by_warehouse.get(warehouse_id, set())
        request = {
            'snapshot': snapshot.model_dump(mode='python'),
            'order_ids': tuple(ids),
            'warehouse_handoffs': tuple(h.model_dump(mode='python')
                                        for h in plan.warehouse.warehouse_handoffs
                                        if h.order_id in scoped),
            'frozen_routes': (),
        }
        result = {
            'metadata': plan.routing.metadata.model_dump(mode='python'),
            'routes': [r.model_dump(mode='python') for r in plan.routing.routes
                       if r.vehicle_id in vehicles],
            'warehouse_arrivals': [a.model_dump(mode='python') for a in plan.routing.warehouse_arrivals
                                   if a.vehicle_id in vehicles],
            'unserved_orders': [],
        }
        report = validate_transport(request=request, result=result)
        transport.append({'warehouse_id': warehouse_id, 'passed': report.passed,
                          'violations': list(report.violations)})
    plan_violations = validate_plan(
        snapshot=snapshot.model_dump(mode='python'), order_ids=order_ids,
        warehouse=plan.warehouse.model_dump(mode='python'),
        routing=plan.routing.model_dump(mode='python'),
    )
    return {
        'transport': transport,
        'transport_passed': all(item['passed'] for item in transport),
        'plan_violations': [{'rule_id': v['rule_id'], 'object_ids': list(v['object_ids']),
                             'message': v['message']} for v in plan_violations],
        'plan_passed': not plan_violations,
        'validator_scope': 'independent B-02/B-03 rules recomputed from the produced plan',
    }


def arm_record(*, name: str, plan: CandidatePlan, snapshot: PlanningSnapshot,
               order_ids: tuple[str, ...], baseline_plan: CandidatePlan, wall_ms: int,
               error: str | None = None) -> dict:
    record = {'arm': name, 'wall_ms': wall_ms, 'error': error, 'status': 'failed'}
    if plan is None:
        return record
    metrics = plan_metrics(plan=plan, snapshot=snapshot, baseline_plan=baseline_plan, wall_ms=wall_ms)
    validation = independent_validation(plan=plan, snapshot=snapshot, order_ids=order_ids)
    record.update({
        'status': 'partial' if metrics['unserved_order_ids'] else 'complete',
        'candidate_plan': plan.model_dump(mode='json'),
        'metrics': metrics, 'independent_validation': validation,
        'legal': bool(validation['transport_passed'] and validation['plan_passed']),
    })
    return record


def judge(rung: dict) -> dict:
    """Judge one (case, delay) comparison from the three arm records."""
    arms = rung['arms']
    complete = sorted(name for name in ARMS if arms[name]['status'] in ('complete', 'partial'))
    served_all = sorted(name for name in ARMS if arms[name]['status'] == 'complete')
    legal = sorted(name for name in ARMS if arms[name].get('legal'))
    legal_with_service = sorted(name for name in ARMS
                                if arms[name].get('legal') and arms[name]['status'] == 'complete')
    reasons = []
    if len(served_all) != len(ARMS):
        reasons.append('not every arm served all required orders: '
                       + ','.join(f'{n}={arms[n]["status"]}' for n in ARMS))
    status = 'complete_comparison' if not reasons else 'incomplete'
    return {'status': status, 'reasons': reasons, 'produced_plan_arms': complete,
            'fully_served_arms': served_all, 'legal_arms': legal,
            'legal_and_fully_served_arms': legal_with_service,
            'no_reschedule_legal': bool(arms['no_reschedule'].get('legal')),
            'note': 'legal = independent transport and cross-domain validation passed on the post-event snapshot'}


def comparisons(case_records: list[dict]):
    for case in case_records:
        for rung in case['rungs']:
            yield case, rung


def comparison_id(case: dict, rung: dict) -> str:
    return f"{case['case']}@{case['family']}@{rung['delay_s']}"


def build_summary(case_records: list[dict], *, budget_ms: int, simpy_check: dict | None,
                  expected_comparisons: int) -> dict:
    pairs = list(comparisons(case_records))
    complete = [(case, rung) for case, rung in pairs
                if rung['judgement']['status'] == 'complete_comparison']

    def mean_over(rows, arm: str, field: str):
        values = [rung['arms'][arm]['metrics'][field] for _, rung in rows]
        return round(sum(values) / len(values), 4) if values else None

    def aggregates(rows) -> dict:
        if not rows:
            return {}
        return {
            'comparisons': len(rows),
            'mean_effective_delay_s': round(sum(r['effective_delay_s'] for _, r in rows) / len(rows), 4),
            'mean_changed_order_count': {arm: mean_over(rows, arm, 'changed_order_count')
                                         for arm in ('full_reschedule', 'local_reschedule')},
            'mean_distance_delta_m': {arm: mean_over(rows, arm, 'distance_delta_m')
                                      for arm in ('full_reschedule', 'local_reschedule')},
            'mean_total_lateness_s': {arm: mean_over(rows, arm, 'total_lateness_s') for arm in ARMS},
            'mean_total_handoff_wait_s': {arm: mean_over(rows, arm, 'total_handoff_wait_s')
                                          for arm in ARMS},
            'mean_wall_ms': {arm: mean_over(rows, arm, 'wall_ms') for arm in ARMS},
        }

    legal_counts = {arm: sum(1 for _, rung in pairs if rung['arms'][arm].get('legal')) for arm in ARMS}
    first_breaking = {}
    for case in case_records:
        broken = [rung['effective_delay_s'] for rung in case['rungs']
                  if not rung['arms']['no_reschedule'].get('legal')]
        first_breaking[f"{case['case']}@{case['family']}"] = min(broken) if broken else None
    summary = {
        'protocol': PROTOCOL,
        'generated_at_utc': datetime.now(timezone.utc).isoformat(),
        'per_arm_total_budget_ms': budget_ms,
        'delay_ladder_s': list(DELAY_LADDER_S),
        'families': list(FAMILIES), 'window_compression_factor': WINDOW_COMPRESSION_FACTOR,
        'occurred_at_s': OCCURRED_AT_S, 'horizon_s': HORIZON_S,
        'case_count': len({c['case'] for c in case_records}),
        'rungs_per_case': len(DELAY_LADDER_S),
        'comparison_count': len(pairs),
        'complete_comparisons': len(complete),
        'legal_arm_counts': legal_counts,
        'no_reschedule_violation_comparisons': [comparison_id(case, rung) for case, rung in pairs
                                                if not rung['arms']['no_reschedule'].get('legal')],
        'no_reschedule_first_breaking_effective_delay_s': first_breaking,
        'vehicle_rule': VEHICLE_RULE, 'delay_rule': DELAY_RULE,
        'family_rule': FAMILY_RULE, 'rules': RULES,
        'statistical_claim': 'Descriptive only; synthetic scenarios, no inferential significance',
        'simpy_replay_check': simpy_check,
        'cases': case_records,
    }
    if complete and len(complete) == expected_comparisons == len(pairs):
        summary['aggregate_over_complete_comparisons'] = aggregates(complete)
        summary['aggregate_note'] = (
            'Published only because every pre-registered comparison completed; averages over a small '
            'synthetic grid are descriptive, not estimates.')
    else:
        summary['aggregate_over_complete_comparisons'] = None
        summary['aggregate_withheld_reason'] = (
            f'only {len(complete)}/{expected_comparisons} pre-registered comparisons completed')

    # The two families are separate pre-registered designs, so a family publishes its own
    # descriptive means as soon as every comparison inside that family completed. The overall
    # aggregate above stays strict: it needs the whole grid.
    by_family: dict[str, list] = {family: [] for family in FAMILIES}
    for case, rung in pairs:
        by_family.setdefault(case['family'], []).append((case, rung))
    summary['family_completeness'] = {
        family: f"{sum(1 for _, r in rows if r['judgement']['status'] == 'complete_comparison')}/{len(rows)}"
        for family, rows in by_family.items() if rows}
    published, withheld = {}, {}
    for family, rows in by_family.items():
        if not rows:
            continue
        if all(r['judgement']['status'] == 'complete_comparison' for _, r in rows):
            published[family] = aggregates(rows)
        else:
            done = sum(1 for _, r in rows if r['judgement']['status'] == 'complete_comparison')
            withheld[family] = f'only {done}/{len(rows)} comparisons in this family completed'
    summary['aggregate_by_family'] = published or None
    summary['aggregate_by_family_withheld'] = withheld
    return summary


def write_reports(outdir: Path, summary: dict) -> None:
    write_json_line(outdir / 'summary.json', summary)
    fields = ['case', 'family', 'size', 'seed', 'delay_s', 'effective_delay_s', 'comparison_status',
              'arm', 'arm_status', 'legal', 'served_orders', 'unserved_orders', 'on_time_count',
              'late_order_count', 'max_lateness_s', 'total_lateness_s', 'total_handoff_wait_s',
              'changed_order_count', 'distance_delta_m', 'wall_ms', 'transport_passed',
              'plan_violations']
    with (outdir / 'summary.csv').open('w', encoding='utf-8-sig', newline='') as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for case in summary['cases']:
            for rung in case['rungs']:
                for arm in ARMS:
                    record = rung['arms'][arm]
                    metrics = record.get('metrics') or {}
                    validation = record.get('independent_validation') or {}
                    writer.writerow({
                        'case': case['case'], 'family': case['family'],
                        'size': case['size'], 'seed': case['seed'],
                        'delay_s': rung['delay_s'], 'effective_delay_s': rung['effective_delay_s'],
                        'comparison_status': rung['judgement']['status'], 'arm': arm,
                        'arm_status': record['status'], 'legal': record.get('legal'),
                        'served_orders': metrics.get('served_order_count'),
                        'unserved_orders': len(metrics.get('unserved_order_ids') or []),
                        'on_time_count': metrics.get('on_time_count'),
                        'late_order_count': metrics.get('late_order_count'),
                        'max_lateness_s': metrics.get('max_lateness_s'),
                        'total_lateness_s': metrics.get('total_lateness_s'),
                        'total_handoff_wait_s': metrics.get('total_handoff_wait_s'),
                        'changed_order_count': metrics.get('changed_order_count'),
                        'distance_delta_m': metrics.get('distance_delta_m'),
                        'wall_ms': record.get('wall_ms'),
                        'transport_passed': validation.get('transport_passed'),
                        'plan_violations': len(validation.get('plan_violations') or []),
                    })
    lines = [
        '# R19 / B-04 异常重调度三策略对照结果', '',
        f"- 协议：`{summary['protocol']}`；每求解臂预算 {summary['per_arm_total_budget_ms']} ms；"
        f"延误梯度 {summary['delay_ladder_s']} s（事件发生在 {summary['occurred_at_s']} s）。",
        f"- 场景 {summary['case_count']} 组 × 场景族 {len(summary['families'])} × 延误 "
        f"{summary['rungs_per_case']} 档 = {summary['comparison_count']} 组对照；"
        f"完整三臂对照 {summary['complete_comparisons']} 组。",
        f"- 场景族：{summary['family_rule']}",
        f"- 各臂独立校验通过组数：{summary['legal_arm_counts']}。",
        f"- 族内完成度：{summary.get('family_completeness')}。",
        f"- 不重调度出现违约的对照：{summary['no_reschedule_violation_comparisons'] or '无'}。",
        f"- 不重调度首次违约的有效延误(s)：{summary['no_reschedule_first_breaking_effective_delay_s']}。",
        '', '| 场景 | 族 | 订单 | 原始延误(s) | 有效延误(s) | 臂 | 状态 | 合法 | 准时单 | 最晚延误(s) | 交接等待(s) | 改派订单 | 距离差(m) | 耗时(ms) |',
        '|---|---|---:|---:|---:|---|---|---|---:|---:|---:|---:|---:|---:|',
    ]
    for case in summary['cases']:
        for rung in case['rungs']:
            for arm in ARMS:
                record = rung['arms'][arm]
                metrics = record.get('metrics') or {}
                value = lambda x: '—' if x is None else x  # noqa: E731
                lines.append(
                    f"| {case['case']} | {case['family']} | {case['size']} | {rung['delay_s']} | "
                    f"{rung['effective_delay_s']} | {arm} | {record['status']} | "
                    f"{value(record.get('legal'))} | {value(metrics.get('on_time_count'))} | "
                    f"{value(metrics.get('max_lateness_s'))} | {value(metrics.get('total_handoff_wait_s'))} | "
                    f"{value(metrics.get('changed_order_count'))} | "
                    f"{value(metrics.get('distance_delta_m'))} | {value(record.get('wall_ms'))} |")
    aggregate = summary.get('aggregate_over_complete_comparisons')
    lines += ['', '## 汇总口径', '']
    if aggregate:
        lines.append(f"- 全网格描述性均值：{json.dumps(aggregate, ensure_ascii=False)}")
        for family, values in (summary.get('aggregate_by_family') or {}).items():
            lines.append(f"- `{family}` 族均值：{json.dumps(values, ensure_ascii=False)}")
        lines.append(f"- {summary.get('aggregate_note', '')}")
    else:
        lines.append(f"- 全网格均值不发布：{summary.get('aggregate_withheld_reason')}")
        for family, values in (summary.get('aggregate_by_family') or {}).items():
            lines.append(f"- `{family}` 族内全部完成，族均值（描述性）：{json.dumps(values, ensure_ascii=False)}")
        for family, reason in (summary.get('aggregate_by_family_withheld') or {}).items():
            lines.append(f"- `{family}` 族均值不发布：{reason}")
    check = summary.get('simpy_replay_check')
    if check:
        lines.append(f"- SimPy 回放一致性（{check.get('case')}，跑 {check.get('runs')} 次）："
                     f"{check.get('status')}")
    lines += ['', '**限制**：全部为合成场景；样本量不足以做显著性推断；“不重调度”不消耗求解预算，'
              '其代价体现在违约与延误上而不是耗时上；有效延误为 0 表示班次表吸收了该延误；'
              '本结果不替代已验收的 R17/R18 证据。']
    (outdir / 'summary.md').write_text('\n'.join(lines) + '\n', encoding='utf8', newline='\n')


def simpy_replay_check(*, snapshot: PlanningSnapshot, event: DispatchEvent, runs: int = 2) -> dict:
    """Determinism check of the B-05 event-replay path on one pre-registered case."""
    from app.adapters.simulation.simpy_simulator import SimPySimulator

    digests, emitted = [], []
    for _ in range(runs):
        reset_runtime()
        request = SimulationRequest(snapshot=snapshot, events=(event,),
                                    horizon_s=HORIZON_S, random_seed=17)
        result = SimPySimulator().simulate(request)
        normalized = result.final_snapshot.model_dump(mode='json')
        normalized.pop('snapshot_id', None)
        normalized.pop('simulation_time_s', None)
        digests.append(sha256_bytes(json.dumps(normalized, sort_keys=True).encode()))
        emitted.append(len(result.emitted_events))
    return {'case': SIMPY_CHECK_CASE, 'runs': runs, 'final_snapshot_digests': digests,
            'emitted_event_counts': emitted,
            'status': 'identical' if len(set(digests)) == 1 else 'divergent',
            'note': 'B-05 replay of the same event with a fixed seed; digests ignore the volatile '
                    'simulation id and simulation clock'}


def prepare_cases(*, base: PlanningSnapshot, outdir: Path, case_count: int) -> list[dict]:
    """Pre-register the case snapshots on disk before any solver call."""
    stubs = []
    for size, seed in CASE_DESIGNS[:case_count]:
        case = f's{size}_seed{seed}'
        generated = prepare_case(base, size=size, seed=seed)
        for family in FAMILIES:
            snapshot = generated if family == 'base' else stress_variant(generated)
            name = f'{case}__{family}'
            path = outdir / 'scenarios' / f'{name}.json'
            write_json_line(path, snapshot.model_dump(mode='json'))
            stubs.append({'case': case, 'family': family, 'size': size, 'seed': seed,
                          'scenario_file': f'scenarios/{name}.json',
                          'scenario_sha256': sha256_file(path),
                          'scenario_bytes': path.stat().st_size,
                          'order_count': len(snapshot.orders),
                          'vehicle_count': len(snapshot.vehicles)})
    return stubs


def stress_variant(snapshot: PlanningSnapshot) -> PlanningSnapshot:
    """Declared synthetic stress family: tighter service windows plus one spare vehicle per zone."""
    orders = tuple(
        order.model_copy(update={
            'service_window': order.service_window.model_copy(
                update={'end_s': max(1, order.service_window.end_s // WINDOW_COMPRESSION_FACTOR)}),
            'freshness_deadline_s': max(1, order.freshness_deadline_s // WINDOW_COMPRESSION_FACTOR),
        })
        for order in snapshot.orders
    )
    spares = tuple(vehicle.model_copy(update={'vehicle_id': f'{vehicle.vehicle_id}b'})
                   for vehicle in snapshot.vehicles)
    return snapshot.model_copy(update={'orders': orders,
                                       'vehicles': snapshot.vehicles + spares})


def run_case(*, stub: dict, outdir: Path, budget_ms: int) -> dict:
    snapshot, scenario_sha = load_snapshot(outdir / stub['scenario_file'])
    if scenario_sha != stub['scenario_sha256']:
        raise ValueError(f"{stub['case']}: pre-registered snapshot was modified after generation")
    case = stub['case']
    record = dict(stub)
    record['per_arm_total_budget_ms'] = budget_ms

    order_ids = tuple(sorted(o.order_id for o in snapshot.orders))
    reset_runtime()
    runtime.put_snapshot(snapshot)
    started = perf_counter()
    baseline = coordinate(snapshot=snapshot, order_ids=order_ids, budget_ms=budget_ms,
                          max_coordination_rounds=1, coordination_mode='sequential')
    baseline_ms = int((perf_counter() - started) * 1000)
    vehicle_id, vehicle_orders = choose_event_vehicle(baseline)
    departure_s = planned_departure_s(baseline, vehicle_id)
    record.update({
        'baseline': {
            'wall_ms': baseline_ms,
            'candidate_plan': baseline.model_dump(mode='json'),
            'metrics': plan_metrics(plan=baseline, snapshot=snapshot, baseline_plan=baseline,
                                    wall_ms=baseline_ms),
            'independent_validation': independent_validation(plan=baseline, snapshot=snapshot,
                                                             order_ids=order_ids),
        },
        'event_vehicle_id': vehicle_id,
        'event_vehicle_order_count': vehicle_orders,
        'planned_departure_s': departure_s,
        'rungs': [],
    })

    for delay_s in DELAY_LADDER_S:
        event = build_event(case=case, snapshot=snapshot, vehicle_id=vehicle_id, delay_s=delay_s)
        derived = _derive_snapshot_for_event(snapshot, event)
        applied = effective_delay_s(derived=derived, vehicle_id=vehicle_id,
                                    planned_departure=departure_s)
        rung = {'delay_s': delay_s, 'effective_delay_s': applied,
                'event': event.model_dump(mode='json'),
                'derived_snapshot_version': derived.version, 'arms': {}}
        arms = rung['arms']

        started = perf_counter()
        try:
            plan = apply_no_reschedule(baseline_plan=baseline, derived=derived,
                                       vehicle_id=vehicle_id, delay_s=applied)
            arms['no_reschedule'] = arm_record(name='no_reschedule', plan=plan, snapshot=derived,
                                               order_ids=order_ids, baseline_plan=baseline,
                                               wall_ms=int((perf_counter() - started) * 1000))
        except Exception as exc:  # noqa: BLE001 - failures are evidence, never hidden
            arms['no_reschedule'] = arm_record(name='no_reschedule', plan=None, snapshot=derived,
                                               order_ids=order_ids, baseline_plan=baseline,
                                               wall_ms=int((perf_counter() - started) * 1000),
                                               error=f'{type(exc).__name__}: {exc}')

        started = perf_counter()
        try:
            reset_runtime()
            runtime.put_snapshot(derived)
            plan = coordinate(snapshot=derived, order_ids=order_ids, budget_ms=budget_ms,
                              max_coordination_rounds=1, coordination_mode='sequential')
            arms['full_reschedule'] = arm_record(name='full_reschedule', plan=plan, snapshot=derived,
                                                 order_ids=order_ids, baseline_plan=baseline,
                                                 wall_ms=int((perf_counter() - started) * 1000))
        except Exception as exc:  # noqa: BLE001
            arms['full_reschedule'] = arm_record(name='full_reschedule', plan=None, snapshot=derived,
                                                 order_ids=order_ids, baseline_plan=baseline,
                                                 wall_ms=int((perf_counter() - started) * 1000),
                                                 error=f'{type(exc).__name__}: {exc}')

        started = perf_counter()
        try:
            reset_runtime()
            runtime.put_snapshot(snapshot)
            result = handle_event(event=event, previous_plan=baseline, budget_ms=budget_ms)
            arms['local_reschedule'] = arm_record(name='local_reschedule', plan=result.replanned_plan,
                                                  snapshot=derived, order_ids=order_ids,
                                                  baseline_plan=baseline,
                                                  wall_ms=int((perf_counter() - started) * 1000))
            arms['local_reschedule']['b04_impact'] = result.impact.model_dump(mode='json')
            arms['local_reschedule']['b04_diff'] = result.diff.model_dump(mode='json')
            arms['local_reschedule']['b04_validation'] = result.validation.model_dump(mode='json')
        except Exception as exc:  # noqa: BLE001
            arms['local_reschedule'] = arm_record(name='local_reschedule', plan=None, snapshot=derived,
                                                  order_ids=order_ids, baseline_plan=baseline,
                                                  wall_ms=int((perf_counter() - started) * 1000),
                                                  error=f'{type(exc).__name__}: {exc}')

        rung['judgement'] = judge(rung)
        record['rungs'].append(rung)
        write_json_line(outdir / 'raw' / f"{case}__{record['family']}_arms.json", record)
        print(f"  {case}@{record['family']} delay={delay_s}s effective={applied}s "
              f"{rung['judgement']['status']} legal={rung['judgement']['legal_arms']}", flush=True)
    return record


def execute(*, base_file: Path, budget_ms: int, outdir: Path, case_count: int,
            dry_run: bool = False, simpy_check: bool = True) -> dict | None:
    if outdir.exists() and any(outdir.iterdir()):
        raise FileExistsError(f'Output directory is not empty; keep prior evidence and choose a new one: {outdir}')
    outdir.mkdir(parents=True, exist_ok=True)
    (outdir / 'raw').mkdir(exist_ok=True)
    (outdir / 'scenarios').mkdir(exist_ok=True)
    base, base_hash = load_snapshot(base_file)
    manifest = {
        'protocol': PROTOCOL, 'source_scenario_sha256': base_hash,
        'source_scenario_filename': base_file.name,
        'case_designs': [{'case': f's{size}_seed{seed}', 'size': size, 'seed': seed}
                         for size, seed in CASE_DESIGNS[:case_count]],
        'generated_at_utc': datetime.now(timezone.utc).isoformat(),
        'arms': list(ARMS), 'per_arm_total_budget_ms': budget_ms,
        'delay_ladder_s': list(DELAY_LADDER_S), 'families': list(FAMILIES),
        'window_compression_factor': WINDOW_COMPRESSION_FACTOR,
        'occurred_at_s': OCCURRED_AT_S, 'horizon_s': HORIZON_S,
        'vehicle_rule': VEHICLE_RULE, 'delay_rule': DELAY_RULE,
        'family_rule': FAMILY_RULE, 'rules': RULES,
        'generation': 'R18 stratified generator reused unchanged (warehouse x temperature, fixed seed)',
        'scope': SCOPE,
    }
    write_json_line(outdir / 'manifest.json', manifest)
    stubs = prepare_cases(base=base, outdir=outdir, case_count=case_count)
    for stub in stubs:
        stub['base_scenario_sha256'] = base_hash
    manifest['cases'] = [{k: v for k, v in stub.items() if k != 'base_scenario_sha256'}
                         for stub in stubs]
    write_json_line(outdir / 'manifest.json', manifest)
    if dry_run:
        print(f'Generated {len(stubs)} validated synthetic snapshots + manifest (no solver run): {outdir}')
        return None

    expected = len(stubs) * len(DELAY_LADDER_S)
    records = []
    simpy_check_result = None
    for stub in stubs:
        record = run_case(stub=stub, outdir=outdir, budget_ms=budget_ms)
        records.append(record)
        manifest['rung_status'] = {f"{c['case']}@{c['family']}@{r['delay_s']}": r['judgement']['status']
                                   for c in records for r in c['rungs']}
        write_json_line(outdir / 'manifest.json', manifest)
        write_reports(outdir, build_summary(records, budget_ms=budget_ms,
                                            simpy_check=simpy_check_result,
                                            expected_comparisons=expected))
        legal_rungs = sum(1 for r in record['rungs'] if r['judgement']['status'] == 'complete_comparison')
        print(f"{record['case']}@{record['family']}: "
              f"{legal_rungs}/{len(record['rungs'])} complete comparisons", flush=True)
    if simpy_check:
        target = next((r for r in records
                       if r['case'] == SIMPY_CHECK_CASE and r['family'] == 'base'), None)
        if target is not None:
            snapshot, _ = load_snapshot(outdir / target['scenario_file'])
            event = DispatchEvent.model_validate(target['rungs'][0]['event'])
            simpy_check_result = simpy_replay_check(snapshot=snapshot, event=event)
            print(f"simpy replay: {simpy_check_result['status']}", flush=True)
    summary = build_summary(records, budget_ms=budget_ms, simpy_check=simpy_check_result,
                            expected_comparisons=expected)
    write_reports(outdir, summary)
    return summary


def main(argv=None):
    parser = argparse.ArgumentParser(
        description='R19 B-04 three-strategy rescheduling comparison (pre-registered)')
    parser.add_argument('--scenario', type=Path, default=Path('../data/scenarios/two_warehouses_20_orders.json'))
    parser.add_argument('--budget-ms', type=int, default=90000)
    parser.add_argument('--case-count', type=int, default=3, choices=(1, 2, 3))
    parser.add_argument('--output-dir', type=Path)
    parser.add_argument('--dry-run', action='store_true')
    parser.add_argument('--skip-simpy', action='store_true',
                        help='skip the B-05 determinism replay check (documented if used)')
    args = parser.parse_args(argv)
    if args.budget_ms < 1000:
        parser.error('--budget-ms must be >= 1000')
    outdir = args.output_dir or Path('../benchmarks/b04/r19_runs') / datetime.now().strftime('run_%Y%m%d_%H%M%S_%f')
    try:
        summary = execute(base_file=args.scenario, budget_ms=args.budget_ms, outdir=outdir,
                          case_count=args.case_count, dry_run=args.dry_run,
                          simpy_check=not args.skip_simpy)
    except (ValueError, FileExistsError) as exc:
        parser.error(str(exc))
    print(f'Results: {outdir.resolve()}')
    if summary is None:
        return 0
    complete = summary['complete_comparisons'] == summary['comparison_count']
    return 0 if complete else 1


if __name__ == '__main__':
    raise SystemExit(main())
