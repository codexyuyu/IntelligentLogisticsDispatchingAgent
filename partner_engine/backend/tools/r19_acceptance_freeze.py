"""Freeze one R19 run into the stable accepted archive.

Discipline mirrors the R18 freeze: evidence is copied byte-for-byte, every recorded
metric is recomputed from the archived plans and snapshots (never trusted as written),
and a single mismatch aborts the freeze instead of producing a report.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import platform
import sys
from datetime import datetime, timezone
from pathlib import Path

from app.application.handle_event import _derive_snapshot_for_event
from app.contracts.events import DispatchEvent
from app.contracts.planning import CandidatePlan

from tools.r17_joint_ablation import load_snapshot
from tools.r19_reschedule_ablation import (
    ARMS, FAMILIES, PROTOCOL, independent_validation, plan_metrics, sha256_file,
)

ARCHIVE_ROOT_FILES = ('manifest.json', 'summary.json', 'summary.csv', 'summary.md')
# Pin the tools AND the implementation under test: without the solver/handler hashes the
# archive cannot distinguish "before the B-04 frozen-route fix" from "after it".
TOOL_FILES = ('tools/r19_reschedule_ablation.py', 'tools/r19_acceptance_freeze.py',
              'tools/r18_multiscene_ablation.py', 'tools/r17_joint_ablation.py',
              'app/adapters/routing/ortools_solver.py', 'app/application/handle_event.py')


def sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def write_json_line(path: Path, payload) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + '\n', encoding='utf8', newline='\n')


def collect_archive(run_dir: Path) -> list[str]:
    missing = [name for name in ARCHIVE_ROOT_FILES if not (run_dir / name).is_file()]
    if missing:
        raise ValueError(f'run directory is incomplete, missing: {", ".join(missing)}')
    rels = list(ARCHIVE_ROOT_FILES)
    for group in ('scenarios', 'raw'):
        rels += sorted(f'{group}/{path.name}' for path in (run_dir / group).glob('*.json'))
    if not rels:
        raise ValueError(f'no evidence files found under {run_dir}')
    return rels


def recompute(run_dir: Path, manifest: dict, summary: dict) -> dict:
    """Recompute every arm metric and legality flag from the archived plans."""
    problems = []
    comparisons, cases = 0, 0
    for rel in sorted(p.name for p in (run_dir / 'raw').glob('*.json')):
        raw = json.loads((run_dir / 'raw' / rel).read_text(encoding='utf8'))
        case, family = raw['case'], raw['family']
        cases += 1
        snapshot, scenario_sha = load_snapshot(run_dir / raw['scenario_file'])
        if scenario_sha != raw['scenario_sha256']:
            raise ValueError(f'{case}@{family}: archived scenario bytes do not match the declared SHA256')
        order_ids = tuple(sorted(o.order_id for o in snapshot.orders))
        baseline = CandidatePlan.model_validate(raw['baseline']['candidate_plan'])
        baseline_metrics = plan_metrics(plan=baseline, snapshot=snapshot, baseline_plan=baseline,
                                        wall_ms=raw['baseline']['wall_ms'])
        if baseline_metrics != raw['baseline']['metrics']:
            problems.append({'comparison': f'{case}@{family}', 'field': 'baseline.metrics'})
        for rung in raw['rungs']:
            comparisons += 1
            label = f"{case}@{family}@{rung['delay_s']}"
            event = DispatchEvent.model_validate(rung['event'])
            derived = _derive_snapshot_for_event(snapshot, event)
            if derived.version != rung['derived_snapshot_version']:
                problems.append({'comparison': label, 'field': 'derived_snapshot_version'})
            for arm in ARMS:
                record = rung['arms'][arm]
                if record['status'] == 'failed' or 'candidate_plan' not in record:
                    if record['status'] != 'failed' or not record.get('error'):
                        problems.append({'comparison': f'{label}/{arm}',
                                         'field': 'failed arm must carry an error'})
                    continue
                plan = CandidatePlan.model_validate(record['candidate_plan'])
                metrics = plan_metrics(plan=plan, snapshot=derived, baseline_plan=baseline,
                                       wall_ms=record['wall_ms'])
                if metrics != record['metrics']:
                    problems.append({'comparison': f'{label}/{arm}', 'field': 'metrics'})
                validation = independent_validation(plan=plan, snapshot=derived, order_ids=order_ids)
                if validation != record['independent_validation']:
                    problems.append({'comparison': f'{label}/{arm}', 'field': 'independent_validation'})
                if bool(validation['transport_passed'] and validation['plan_passed']) != bool(record['legal']):
                    problems.append({'comparison': f'{label}/{arm}', 'field': 'legal'})
    if problems:
        raise ValueError('recomputation disagrees with the archived records: '
                         + json.dumps(problems, ensure_ascii=False))
    expected_cases = summary['case_count'] * len(summary['families'])
    if cases != expected_cases:
        raise ValueError(f"summary case_count={summary['case_count']} x families="
                         f"{len(summary['families'])} implies {expected_cases} case records "
                         f'but {cases} were archived')
    if summary['comparison_count'] != comparisons:
        raise ValueError(f"summary comparison_count={summary['comparison_count']} but {comparisons} "
                         'comparison records were recomputed')
    if manifest['protocol'] != PROTOCOL or summary['protocol'] != PROTOCOL:
        raise ValueError('protocol mismatch between manifest and summary')
    return {'cases_recomputed': cases, 'comparisons_recomputed': comparisons,
            'mismatches': 0,
            'scope': ('independent recomputation of every recorded arm metric, legality flag and '
                      'derived snapshot version from the archived CandidatePlans and snapshots; '
                      'not a new solver run and not a second constraint proof')}


def build_manifest(run_dir: Path, rels: list[str], run_manifest: dict, summary: dict,
                   audit: dict, archive_name: str) -> dict:
    files = []
    for rel in rels:
        payload = (run_dir / rel).read_bytes()
        files.append({'path': rel, 'bytes': len(payload), 'sha256': sha256_bytes(payload)})
    tool_hashes = {}
    for rel in TOOL_FILES:
        tool = Path(__file__).resolve().parents[1] / rel
        tool_hashes[rel] = sha256_file(tool) if tool.is_file() else None
    return {
        'archive': f'benchmarks/b04/{archive_name}',
        'frozen_at_utc': datetime.now(timezone.utc).isoformat(),
        'protocol': summary['protocol'],
        'source_run': run_dir.name,
        'source_run_path': str(run_dir),
        'source_scenario_sha256': run_manifest['source_scenario_sha256'],
        'per_arm_total_budget_ms': summary['per_arm_total_budget_ms'],
        'delay_ladder_s': summary['delay_ladder_s'],
        'families': summary['families'],
        'case_count': summary['case_count'],
        'comparison_count': summary['comparison_count'],
        'complete_comparisons': summary['complete_comparisons'],
        'legal_arm_counts': summary['legal_arm_counts'],
        'file_count': len(files),
        'total_bytes': sum(item['bytes'] for item in files),
        'files': files,
        'tool_sha256': tool_hashes,
        'reproduction_command': ('cd backend; python -m tools.r19_reschedule_ablation '
                                 f"--case-count 3 --budget-ms {summary['per_arm_total_budget_ms']}"),
        'freeze_command': (f'cd backend; python -m tools.r19_acceptance_freeze --run-dir '
                           f'../benchmarks/b04/r19_runs/{run_dir.name}'),
        'environment': {'python': sys.version.split()[0], 'platform': platform.platform()},
        'verdict': {'cases_recomputed': audit['cases_recomputed'],
                    'comparisons_recomputed': audit['comparisons_recomputed'], 'mismatches': 0},
        'scope': 'synthetic equal-budget strategy comparison; not empirical performance, '
                 'not a significance test, not an R17/R18 replacement',
    }


def write_readme(path: Path, manifest: dict) -> None:
    lines = [
        '# R19 / B-04 三策略对照已验收冻结归档', '',
        f"- 来源运行：`{manifest['source_run']}`（原始运行目录保留在 `r19_runs/` 下，本归档为逐字节副本）。",
        f"- 协议：`{manifest['protocol']}`；场景 {manifest['case_count']} 组 × 族 {manifest['families']} × "
        f"延误 {manifest['delay_ladder_s']} s。",
        f"- 归档 {manifest['file_count']} 个文件、{manifest['total_bytes']} 字节，逐文件 SHA256 见 `r19_accepted_manifest.json`。",
        f"- 独立复算：{manifest['verdict']['comparisons_recomputed']} 组对照的每个指标与合法性均由归档方案重算，"
        f"不一致数 {manifest['verdict']['mismatches']}（见 `r19_recompute_audit.json`）。",
        f"- 各臂合法组数：{manifest['legal_arm_counts']}。",
        '', '## 口径', '',
        '- 合成场景；不构成县域真实收益，未做显著性检验。',
        '- 「不重调度」不消耗求解预算，其代价体现在违约与延误；求解耗时不可直接用来判定优劣。',
        '- 求解器返回的无解是本次预算内的搜索结论，证据中原样保留错误类型。',
        '', '## 复现', '', '```powershell',
        manifest['reproduction_command'], '```', '',
    ]
    path.write_text('\n'.join(lines), encoding='utf8', newline='\n')


def main(argv=None):
    parser = argparse.ArgumentParser(description='Freeze one R19 run into benchmarks/b04/r19_accepted')
    parser.add_argument('--run-dir', type=Path, required=True)
    parser.add_argument('--accepted-dir', type=Path, default=Path('../benchmarks/b04/r19_accepted'))
    args = parser.parse_args(argv)
    run_dir, accepted = args.run_dir, args.accepted_dir
    if not (run_dir / 'summary.json').is_file():
        parser.error(f'{run_dir} is not a completed R19 run directory')
    if accepted.exists() and any(accepted.iterdir()):
        parser.error(f'{accepted} is not empty; keep the existing archive and choose another location')
    rels = collect_archive(run_dir)
    manifest_json = json.loads((run_dir / 'manifest.json').read_text(encoding='utf8'))
    summary = json.loads((run_dir / 'summary.json').read_text(encoding='utf8'))
    audit = recompute(run_dir, manifest_json, summary)
    archive_manifest = build_manifest(run_dir, rels, manifest_json, summary, audit, accepted.name)
    accepted.mkdir(parents=True, exist_ok=True)
    for rel in rels:
        target = accepted / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes((run_dir / rel).read_bytes())
    write_json_line(accepted / 'r19_accepted_manifest.json', archive_manifest)
    write_json_line(accepted / 'r19_recompute_audit.json', audit)
    write_readme(accepted / 'README.md', archive_manifest)
    for entry in archive_manifest['files']:
        if sha256_file(accepted / entry['path']) != entry['sha256']:
            raise SystemExit(f"archived copy corrupted: {entry['path']}")
    print(f"Frozen {archive_manifest['file_count']} files "
          f"({archive_manifest['total_bytes']} bytes) -> {accepted}")
    print(f"recomputed {audit['comparisons_recomputed']} comparisons, mismatches={audit['mismatches']}")
    print(f"legal arm counts: {archive_manifest['legal_arm_counts']}")
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
