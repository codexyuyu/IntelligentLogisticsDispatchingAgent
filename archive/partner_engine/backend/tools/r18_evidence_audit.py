"""Independent arithmetic/provenance audit of an existing R17 paired evidence JSON.

Uses only Python stdlib, never runs a solver or silently rewrites the original.
This is not a second full CP-SAT/Routing constraint validation.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path


def audit_row(row: dict, order_ids: list[str]) -> dict:
    if row.get('status') != 'succeeded':
        raise ValueError(f"{row.get('mode')}: run failed")
    validation = row.get('validation') or {}
    if validation.get('status') != 'passed' or validation.get('violations'):
        raise ValueError(f"{row.get('mode')}: original validator not passed")
    plan = row['candidate_plan']
    if plan['validation'] != validation:
        raise ValueError(f"{row.get('mode')}: validator record mismatch")
    if plan['coordination'] != row['coordination']:
        raise ValueError(f"{row.get('mode')}: coordination record mismatch")
    routes = plan['routing']['routes']
    handoffs = plan['warehouse']['warehouse_handoffs']
    ready = {}
    for h in handoffs:
        oid = h['order_id']
        if oid in ready:
            raise ValueError(f"duplicate handoff: {oid}")
        ready[oid] = h['ready_at_s']
    departed = {}
    for route in routes:
        starts = [s for s in route['stops'] if s['stop_kind'] == 'depot_start']
        if len(starts) != 1:
            raise ValueError('each route needs one depot_start')
        start = starts[0]['departure_at_s']
        for stop in route['stops']:
            if stop['stop_kind'] != 'delivery':
                continue
            for oid in stop['order_ids']:
                if oid in departed:
                    raise ValueError(f'duplicate delivery: {oid}')
                departed[oid] = start
    if set(departed) != set(order_ids) or set(ready) != set(order_ids):
        raise ValueError('order coverage / handoff mismatch')
    if row.get('unserved_orders') or plan['routing']['unserved_orders']:
        raise ValueError('unserved orders present')
    waiting = sum(departed[oid] - ready[oid] for oid in order_ids)
    if any(departed[oid] < ready[oid] for oid in order_ids):
        raise ValueError('departure before ready_at')
    distance = sum(r['distance_m'] for r in routes)
    if distance != row['distance_m']:
        raise ValueError('distance mismatch')
    coordination = row['coordination']
    if coordination['selected_distance_m'] != distance or coordination['selected_handoff_wait_s'] != waiting:
        raise ValueError('coordination metrics do not match candidate')
    if coordination['mode'] != row['mode']:
        raise ValueError('mode mismatch')
    if coordination['selected_round'] not in [r['round_number'] for r in coordination['rounds'] if r['accepted']]:
        raise ValueError('selected round not an accepted round')
    return {'mode': row['mode'], 'status': 'verified_arithmetic_and_provenance',
            'order_count': len(departed), 'distance_m': distance,
            'handoff_wait_s': waiting, 'wall_ms': row['wall_ms'],
            'selected_round': coordination['selected_round'],
            'attempted_rounds': coordination['attempted_rounds'], 'validation_record': 'passed'}


def audit_evidence(evidence: dict, *, scenario_bytes: bytes | None = None) -> dict:
    ids = evidence['order_ids']
    if len(ids) != len(set(ids)) or len(ids) != evidence['order_count']:
        raise ValueError('invalid order_ids')
    if evidence['per_mode_total_budget_ms'] <= 0:
        raise ValueError('invalid budget')
    if scenario_bytes is not None and hashlib.sha256(scenario_bytes).hexdigest() != evidence['scenario_sha256']:
        raise ValueError('scenario SHA256 mismatch')
    rows = evidence['results']
    if len(rows) != 2 or [r.get('mode') for r in rows] != ['sequential', 'deep']:
        raise ValueError('expected sequential and deep arms')
    checked = [audit_row(r, ids) for r in rows]
    a, b = checked
    saved = a['handoff_wait_s'] - b['handoff_wait_s']
    return {
        'source_benchmark_version': evidence['benchmark_version'],
        'scenario_sha256': evidence['scenario_sha256'],
        'input_snapshot_verified_by_sha256': scenario_bytes is not None,
        'per_arm_budget_ms': evidence['per_mode_total_budget_ms'],
        'modes': checked, 'handoff_wait_saved_s': saved,
        'handoff_wait_reduction_pct': round(100 * saved / a['handoff_wait_s'], 2) if a['handoff_wait_s'] else None,
        'additional_deep_wall_ms': b['wall_ms'] - a['wall_ms'],
        'scope': 'candidate-plan arithmetic and evidence consistency only; no rerun and no full independent constraint validation',
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description='Audit R17 accepted evidence without rerunning OR-Tools')
    parser.add_argument('--input', type=Path, required=True)
    parser.add_argument('--scenario', type=Path)
    parser.add_argument('--output', type=Path)
    args = parser.parse_args(argv)
    report = audit_evidence(json.loads(args.input.read_text(encoding='utf8')),
                            scenario_bytes=args.scenario.read_bytes() if args.scenario else None)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        # newline='\n' keeps the report byte-identical across platforms; the default
        # text-mode translation wrote CRLF on Windows and broke hash verification.
        args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n',
                               encoding='utf8', newline='\n')
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
