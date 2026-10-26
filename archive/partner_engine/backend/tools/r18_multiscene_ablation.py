"""R18 reproducible *new* multi-scenario paired B-03 study, not an R17 rerun.

Pre-register 5 deterministic stratified scenarios, then call the unmodified
R17 equal-total-budget coordinator for sequential and deep on each snapshot.
All failures and raw CandidatePlans are retained, with no cherry-picking.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import random
from datetime import datetime, timezone
from pathlib import Path

from app.contracts.entities import PlanningSnapshot
from tools.r17_joint_ablation import load_snapshot, run_comparison
from tools.r18_evidence_audit import audit_row

PROTOCOL = 'r18-b06-multiscene-paired-1.0'
CASE_DESIGNS = ((12, 17), (16, 42), (20, 66), (20, 88), (20, 101))


def prepare_case(base: PlanningSnapshot, *, size: int, seed: int) -> PlanningSnapshot:
    """Keep all four temperature/warehouse strata represented; modify operational load.

    Never change matrix, warehouses, vehicles, existing orders' IDs or the
    original base file. Subsets and small release/service perturbations form
    distinct *synthetic* stress scenarios, not empirical operational samples.
    """
    rng = random.Random(seed)
    by_stratum: dict[tuple[str, str], list[str]] = {}
    for order in base.orders:
        by_stratum.setdefault((order.warehouse_id, order.temperature_zone), []).append(order.order_id)
    if len(by_stratum) != 4 or size % len(by_stratum):
        raise ValueError('base is not four-stratum or size not divisible by four')
    take = size // len(by_stratum)
    selected: set[str] = set()
    for key in sorted(by_stratum):
        choices = sorted(by_stratum[key]); rng.shuffle(choices)
        if len(choices) < take:
            raise ValueError('too few orders in stratum')
        selected.update(choices[:take])
    payload = base.model_dump(mode='json')
    key = f's{size}_seed{seed}'
    payload['snapshot_id'] = f'r18_{key}'
    payload['orders'] = [o for o in payload['orders'] if o['order_id'] in selected]
    payload['operations'] = [op for op in payload['operations'] if set(op['order_ids']) <= selected]
    active_operations = {op['operation_id'] for op in payload['operations']}
    payload['frozen_operations'] = [op for op in payload['frozen_operations'] if op['operation_id'] in active_operations]
    retained_lots = {o['batch_id'] for o in payload['orders']}
    payload['stock_lots'] = [lot for lot in payload['stock_lots'] if lot['batch_id'] in retained_lots]
    for order in payload['orders']:
        order['service_duration_s'] = max(60, order['service_duration_s'] + rng.choice([-30, 0, 30]))
        order['source']['source_ref'] = f'synthetic:r18-b03:{key}'
    for op in payload['operations']:
        op['release_at_s'] += rng.choice([0, 60, 120, 180])
    return PlanningSnapshot.model_validate(payload)


def inspect_pair(report: dict) -> dict:
    """Calculate reportable values only for complete, validated, full-coverage pairs."""
    base = {'status': 'incomplete', 'error': None, 'sequential_wait_s': None,
            'deep_wait_s': None, 'distance_sequential_m': None, 'distance_deep_m': None,
            'wait_saved_s': None, 'wait_reduction_pct': None,
            'deep_extra_wall_ms': None, 'distance_priority': 'not_comparable'}
    try:
        if report['per_mode_total_budget_ms'] <= 0:
            raise ValueError('invalid budget')
        seq, deep = report['results']
        if seq.get('mode') != 'sequential' or deep.get('mode') != 'deep':
            raise ValueError('wrong arm order')
        a = audit_row(seq, report['order_ids'])
        b = audit_row(deep, report['order_ids'])
    except (ValueError, KeyError, TypeError, IndexError) as exc:
        base['error'] = str(exc)
        return base
    base.update(status='complete_validated_pair', sequential_wait_s=a['handoff_wait_s'],
                deep_wait_s=b['handoff_wait_s'], distance_sequential_m=a['distance_m'],
                distance_deep_m=b['distance_m'], deep_extra_wall_ms=b['wall_ms'] - a['wall_ms'])
    if b['distance_m'] != a['distance_m']:
        base['distance_priority'] = 'deep_shorter' if b['distance_m'] < a['distance_m'] else 'deep_longer'
        base['error'] = 'Distances differ: waiting improvement percentage withheld because objective prioritizes distance'
        return base
    base['distance_priority'] = 'equal_distance'
    base['wait_saved_s'] = a['handoff_wait_s'] - b['handoff_wait_s']
    base['wait_reduction_pct'] = round(100 * base['wait_saved_s'] / a['handoff_wait_s'], 2) if a['handoff_wait_s'] else None
    return base


def build_summary(case_records: list[dict], budget_ms: int) -> dict:
    comparable = [x for x in case_records if x['analysis']['status'] == 'complete_validated_pair'
                  and x['analysis']['distance_priority'] == 'equal_distance']
    improvements = sum(x['analysis']['wait_saved_s'] > 0 for x in comparable)
    regressions = sum(x['analysis']['wait_saved_s'] < 0 for x in comparable)
    ties = sum(x['analysis']['wait_saved_s'] == 0 for x in comparable)
    return {'protocol': PROTOCOL, 'generated_at_utc': datetime.now(timezone.utc).isoformat(),
            'per_mode_total_budget_ms': budget_ms, 'case_count': len(case_records),
            'valid_equal_distance_pairs': len(comparable),
            'improved_count': improvements, 'regressed_count': regressions, 'unchanged_count': ties,
            'average_wait_reduction_pct': round(sum(x['analysis']['wait_reduction_pct'] for x in comparable
                  if x['analysis']['wait_reduction_pct'] is not None) / len(comparable), 2)
                  if len(comparable) >= 3 and all(x['analysis']['wait_reduction_pct'] is not None for x in comparable) else None,
            'statistical_claim': 'Descriptive only; synthetic samples, no inferential significance',
            'cases': case_records}


def write_json_line(path: Path, payload) -> None:
    """Write JSON with an explicit LF ending; Windows text mode would emit CRLF and
    change the published SHA256 of reproducible evidence."""
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + '\n',
                    encoding='utf8', newline='\n')


def write_reports(outdir: Path, summary: dict):
    write_json_line(outdir / 'summary.json', summary)
    with (outdir / 'summary.csv').open('w', encoding='utf-8-sig', newline='') as f:
        fields = ['case', 'size', 'seed', 'scenario_sha256', 'status', 'distance_priority',
                  'distance_sequential_m', 'distance_deep_m', 'sequential_wait_s',
                  'deep_wait_s', 'wait_saved_s', 'wait_reduction_pct', 'deep_extra_wall_ms', 'error']
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        for case in summary['cases']:
            row = {k:case.get(k) for k in fields}
            row.update({k:v for k,v in case['analysis'].items() if k in fields})
            writer.writerow(row)
    notes = [
        '# R18 / B-06 多场景等预算成对实验结果', '',
        f"- 测试场景：{summary['case_count']}；每模式预算：{summary['per_mode_total_budget_ms']}ms。",
        f"- 同距离、全量服务、校验通过的可比较对：{summary['valid_equal_distance_pairs']}。",
        f"- 等距离条件下等待改善/持平/变差：{summary['improved_count']}/{summary['unchanged_count']}/{summary['regressed_count']}。",
        f"- 改善率算术平均：{str(summary['average_wait_reduction_pct'])+'%' if summary['average_wait_reduction_pct'] is not None else '不报告（不足3组同距离有效对照或原始等待为0）'}。",
        '', '| 场景 | 订单 | 判定 | 顺序等待(s) | 深度等待(s) | 改善率 |',
        '|---|---:|---|---:|---:|---:|'
    ]
    for c in summary['cases']:
        a=c['analysis']
        val=lambda x: '—' if x is None else str(x)
        notes.append(f"| {c['case']} | {c['size']} | {a['status']} / {a['distance_priority']} | {val(a['sequential_wait_s'])} | {val(a['deep_wait_s'])} | {val(a['wait_reduction_pct'])} |")
    notes.extend(['', '**口径与限制**：每个场景的两种模式读取相同快照 SHA256、相同总求解预算；同一 R17 核心协调器，完整原始 CandidatePlan 和失败均留存。仅当两者订单全覆盖、校验通过且运输距离相同时才报告等待改善率。所有场景为合成压力测试，不代表县域真实货损或成本收益。'])
    (outdir / 'summary.md').write_text('\n'.join(notes) + '\n', encoding='utf8', newline='\n')


def execute(*, base_file: Path, budget_ms: int, outdir: Path, case_count: int, dry_run=False):
    if outdir.exists() and any(outdir.iterdir()):
        raise FileExistsError(f'Output directory is not empty; keep prior evidence and choose a new directory: {outdir}')
    base, base_hash = load_snapshot(base_file)
    outdir.mkdir(parents=True, exist_ok=True)
    scenarios = outdir / 'scenarios'
    raw = outdir / 'raw'
    scenarios.mkdir();raw.mkdir()
    cases = []
    for size, seed in CASE_DESIGNS[:case_count]:
        name = f's{size}_seed{seed}'
        snapshot = prepare_case(base, size=size, seed=seed)
        scenario_path = scenarios / f'{name}.json'
        write_json_line(scenario_path, snapshot.model_dump(mode='json'))
        sha = hashlib.sha256(scenario_path.read_bytes()).hexdigest()
        cases.append({'case': name, 'size': size, 'seed': seed, 'scenario_sha256': sha,
                      'scenario_file': str(scenario_path.relative_to(outdir)), 'mode_budget_ms': budget_ms,
                      'status': 'not_started'})
    manifest = {'protocol': PROTOCOL, 'source_scenario_sha256': base_hash,
                'source_scenario_filename': base_file.name, 'per_mode_total_budget_ms': budget_ms,
                'generation': 'stratified by warehouse x temperature, independent random seed, order subset + loading release + service duration',
                'cases': cases, 'mode_order': ['sequential', 'deep'],
                'scope': 'synthetic scenario paired evaluation; not R17 accepted evidence replacement'}
    write_json_line(outdir / 'manifest.json', manifest)
    if dry_run:
        print(f'Generated {len(cases)} validated synthetic snapshots + manifest (no solver run): {outdir}')
        return None
    records = []
    for c in cases:
        case = dict(c)
        scenario, sha = load_snapshot(outdir / c['scenario_file'])
        if sha != c['scenario_sha256']:
            raise ValueError('post-generation snapshot was modified')
        ids = tuple(o.order_id for o in scenario.orders)
        try:
            result = run_comparison(snapshot=scenario, snapshot_sha256=sha, budget_ms=budget_ms, order_ids=ids)
            write_json_line(raw / f"{c['case']}_paired.json", result)
            case['analysis'] = inspect_pair(result)
        except Exception as exc:
            case['analysis'] = {'status': 'incomplete', 'error': f'{type(exc).__name__}: {exc}',
                                'distance_priority': 'not_comparable', 'distance_sequential_m': None,
                                'distance_deep_m': None, 'sequential_wait_s': None, 'deep_wait_s': None,
                                'wait_saved_s': None, 'wait_reduction_pct': None, 'deep_extra_wall_ms': None}
            write_json_line(raw / f"{c['case']}_runner_error.json", case['analysis'])
        case['status'] = case['analysis']['status']
        c['status'] = case['status']
        write_json_line(outdir / 'manifest.json', manifest)
        records.append(case)
        # checkpoint after EVERY scenario, even if it fails
        write_reports(outdir, build_summary(records, budget_ms))
        print(f"{case['case']}: {case['status']} / {case['analysis']['distance_priority']}", flush=True)
    return build_summary(records, budget_ms)


def main(argv=None):
    parser = argparse.ArgumentParser(description='R18 multi-scenario paired evidence; distinct from accepted R17 A/B')
    parser.add_argument('--scenario', type=Path, default=Path('../data/scenarios/two_warehouses_20_orders.json'))
    parser.add_argument('--budget-ms', type=int, default=90000)
    parser.add_argument('--case-count', type=int, default=5, choices=(3, 4, 5))
    parser.add_argument('--output-dir', type=Path)
    parser.add_argument('--dry-run', action='store_true', help='generate/check scenarios only, no solver')
    args = parser.parse_args(argv)
    if args.budget_ms < 1000:
        parser.error('--budget-ms must be >= 1000')
    outdir = args.output_dir or Path('../benchmarks/b03/r18_runs') / datetime.now().strftime('run_%Y%m%d_%H%M%S_%f')
    try:
        result = execute(base_file=args.scenario, budget_ms=args.budget_ms,
                         outdir=outdir, case_count=args.case_count, dry_run=args.dry_run)
    except (ValueError, FileExistsError) as exc:
        parser.error(str(exc))
    print(f'Results: {outdir.resolve()}')
    return 0 if result is None or all(c['analysis']['status'] == 'complete_validated_pair' for c in result['cases']) else 1


if __name__ == '__main__':
    raise SystemExit(main())
