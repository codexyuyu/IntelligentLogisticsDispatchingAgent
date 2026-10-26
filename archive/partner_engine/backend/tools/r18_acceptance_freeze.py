"""Freeze one R18 multi-scene run into the stable accepted archive.

Discipline:
  * Evidence is copied byte-for-byte; the source run directory is never modified.
  * Every pair is recomputed from the raw CandidatePlan JSON with the same
    independent audit used by the runner, then compared against the run's own
    summary.json. A mismatch aborts the freeze instead of writing a report.
  * The frozen manifest records the SHA256 of every archived byte, the source
    run id, the reproduction command and the tool hashes, so a later reviewer
    can tell "archived bytes" from "what the tool would produce today".
"""
from __future__ import annotations

import argparse
import hashlib
import json
import platform
import sys
from datetime import datetime, timezone
from pathlib import Path

from tools.r18_evidence_audit import audit_row
from tools.r18_multiscene_ablation import PROTOCOL, inspect_pair

TOOL_FILES = ('tools/r18_multiscene_ablation.py', 'tools/r18_evidence_audit.py',
              'tools/r17_joint_ablation.py', 'tools/r18_acceptance_freeze.py')
ARCHIVE_ROOT_FILES = ('manifest.json', 'summary.json', 'summary.csv', 'summary.md')
R17_CROSS_CHECK_CASE = 's20_seed66'


def sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def sha256_file(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def collect_archive(run_dir: Path) -> list[str]:
    """Relative posix paths of the files that belong in the accepted archive."""
    rels = [name for name in ARCHIVE_ROOT_FILES if (run_dir / name).is_file()]
    for group in ('scenarios', 'raw'):
        rels += sorted(f'{group}/{p.name}' for p in (run_dir / group).glob('*.json'))
    missing = [n for n in ARCHIVE_ROOT_FILES if not (run_dir / n).is_file()]
    if missing:
        raise ValueError(f'run directory is incomplete, missing: {", ".join(missing)}')
    return rels


def recompute(run_dir: Path, run_manifest: dict, run_summary: dict) -> dict:
    """Independently recompute every pair; raise on any disagreement."""
    declared = {c['case']: c for c in run_manifest['cases']}
    summarized = {c['case']: c for c in run_summary['cases']}
    if set(declared) != set(summarized) or len(declared) != run_summary['case_count']:
        raise ValueError('manifest/summary case sets disagree')
    records, problems = [], []
    for name in sorted(declared):
        case = declared[name]
        scenario_path = run_dir / Path(case['scenario_file'])
        actual_sha = sha256_file(scenario_path)
        if actual_sha != case['scenario_sha256']:
            raise ValueError(f'{name}: archived scenario bytes do not match the declared SHA256')
        raw_path = run_dir / 'raw' / f'{name}_paired.json'
        if not raw_path.is_file():
            raise ValueError(f'{name}: raw paired evidence is missing, refusing to freeze a partial run')
        report = json.loads(raw_path.read_text(encoding='utf8'))
        if report['scenario_sha256'] != actual_sha:
            raise ValueError(f'{name}: raw evidence was produced from a different snapshot')
        recomputed = inspect_pair(report)
        expected = summarized[name]['analysis']
        if recomputed != expected:
            problems.append({'case': name, 'field': 'analysis', 'summary': expected, 'recomputed': recomputed})
        if report['per_mode_total_budget_ms'] != run_summary['per_mode_total_budget_ms']:
            problems.append({'case': name, 'field': 'budget_ms',
                             'summary': run_summary['per_mode_total_budget_ms'],
                             'recomputed': report['per_mode_total_budget_ms']})
        recomputed_ids = tuple(report['order_ids'])
        for row in report['results']:
            audit_row(row, recomputed_ids)
        records.append({
            'case': name, 'size': case['size'], 'seed': case['seed'],
            'scenario_sha256': actual_sha, 'scenario_bytes': scenario_path.stat().st_size,
            'raw_evidence': f'raw/{name}_paired.json',
            'raw_sha256': sha256_file(raw_path),
            'status': recomputed['status'],
            'distance_priority': recomputed['distance_priority'],
            'distance_sequential_m': recomputed['distance_sequential_m'],
            'distance_deep_m': recomputed['distance_deep_m'],
            'sequential_wait_s': recomputed['sequential_wait_s'],
            'deep_wait_s': recomputed['deep_wait_s'],
            'wait_saved_s': recomputed['wait_saved_s'],
            'wait_reduction_pct': recomputed['wait_reduction_pct'],
            'deep_extra_wall_ms': recomputed['deep_extra_wall_ms'],
        })
    if problems:
        raise ValueError('recomputation disagrees with summary.json: '
                         + json.dumps(problems, ensure_ascii=False))
    comparable = [r for r in records if r['status'] == 'complete_validated_pair'
                  and r['distance_priority'] == 'equal_distance']
    derived = {
        'valid_equal_distance_pairs': len(comparable),
        'improved_count': sum(r['wait_saved_s'] > 0 for r in comparable),
        'regressed_count': sum(r['wait_saved_s'] < 0 for r in comparable),
        'unchanged_count': sum(r['wait_saved_s'] == 0 for r in comparable),
        'average_wait_reduction_pct': (round(sum(r['wait_reduction_pct'] for r in comparable)
                                             / len(comparable), 2)
                                       if len(comparable) >= 3
                                       and all(r['wait_reduction_pct'] is not None for r in comparable) else None),
    }
    for key, value in derived.items():
        if run_summary[key] != value:
            raise ValueError(f'summary.json {key}={run_summary[key]!r} but recomputation gives {value!r}')
    return {'cases': records, 'derived': derived}


def cross_check_r17(r17_evidence: Path | None, records: list[dict]) -> dict:
    """Compare the s20_seed66 arm against the accepted R17 A/B record, factually."""
    if r17_evidence is None or not r17_evidence.is_file():
        return {'status': 'not_checked', 'reason': 'R17 accepted evidence not available'}
    evidence = json.loads(r17_evidence.read_text(encoding='utf8'))
    rows = {r['mode']: audit_row(r, evidence['order_ids']) for r in evidence['results']}
    reference = next((r for r in records if r['case'] == R17_CROSS_CHECK_CASE), None)
    if reference is None:
        return {'status': 'not_checked', 'reason': f'{R17_CROSS_CHECK_CASE} not part of this run'}
    observed = {'sequential_wait_s': rows['sequential']['handoff_wait_s'],
                'deep_wait_s': rows['deep']['handoff_wait_s'],
                'distance_m': rows['sequential']['distance_m']}
    matched = (observed['sequential_wait_s'] == reference['sequential_wait_s']
               and observed['deep_wait_s'] == reference['deep_wait_s']
               and observed['distance_m'] == reference['distance_sequential_m'])
    return {'status': 'match' if matched else 'differ', 'case': R17_CROSS_CHECK_CASE,
            'reference_file': r17_evidence.name, 'reference': observed,
            'observed': {'sequential_wait_s': reference['sequential_wait_s'],
                         'deep_wait_s': reference['deep_wait_s'],
                         'distance_m': reference['distance_sequential_m']},
            'note': 'Coincidence check on shared operational load only; the R18 s20 snapshots are '
                    'separately perturbed synthetic files and do not replace the R17 evidence.'}


def build_manifest(run_dir: Path, rels: list[str], run_manifest: dict, run_summary: dict,
                   audit: dict) -> dict:
    files = []
    for rel in rels:
        payload = (run_dir / rel).read_bytes()
        files.append({'path': rel, 'bytes': len(payload), 'sha256': sha256_bytes(payload)})
    tool_hashes = {}
    for rel in TOOL_FILES:
        tool = Path(__file__).resolve().parents[1] / rel
        tool_hashes[rel] = sha256_file(tool) if tool.is_file() else None
    return {
        'archive': 'benchmarks/b03/r18_accepted',
        'frozen_at_utc': datetime.now(timezone.utc).isoformat(),
        'protocol': run_summary['protocol'],
        'source_run': run_dir.name,
        'source_run_path': str(run_dir),
        'source_scenario_sha256': run_manifest['source_scenario_sha256'],
        'source_scenario_filename': run_manifest['source_scenario_filename'],
        'per_mode_total_budget_ms': run_summary['per_mode_total_budget_ms'],
        'case_count': run_summary['case_count'],
        'file_count': len(files),
        'total_bytes': sum(f['bytes'] for f in files),
        'files': files,
        'tool_sha256': tool_hashes,
        'reproduction_command': ('cd backend; python -m tools.r18_multiscene_ablation '
                                 f"--case-count {run_summary['case_count']} "
                                 f"--budget-ms {run_summary['per_mode_total_budget_ms']}"),
        'freeze_command': (f'cd backend; python -m tools.r18_acceptance_freeze --run-dir '
                           f'../benchmarks/b03/r18_runs/{run_dir.name}'),
        'line_endings': 'archived bytes preserve the CRLF produced by the 2026-10-14 runner; '
                        'the LF defect is fixed in this revision, so a re-run of the tool writes LF',
        'environment': {'python': sys.version.split()[0], 'platform': platform.platform()},
        'verdict': {'recomputed_cases': len(audit['cases']), 'mismatches': 0},
        'scope': 'synthetic equal-budget paired evidence; not empirical county-level savings, '
                 'not an R17 replacement, no significance test',
    }


def write_json(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + '\n', encoding='utf8', newline='\n')


def write_readme(path: Path, manifest: dict) -> None:
    lines = [
        '# R18 / B-06 已验收冻结归档', '',
        f"- 来源运行：`{manifest['source_run']}`（原始运行目录保留在同一 `r18_runs/` 下，本归档为逐字节副本）。",
        f"- 协议：`{manifest['protocol']}`；每模式总预算 {manifest['per_mode_total_budget_ms']} ms；场景数 {manifest['case_count']}。",
        f"- 归档 {manifest['file_count']} 个文件、{manifest['total_bytes']} 字节，逐文件 SHA256 见 `r18_accepted_manifest.json`。",
        f"- 复算核对：{manifest['verdict']['recomputed_cases']} 组逐单重算与运行 summary 完全一致（见 `r18_multiscene_audit.json`）。",
        '', '## 口径', '',
        '- 等待指标为逐订单「备货完成 → 车辆离仓」累计值，不是车辆排队时间；改善率仅在两组运输距离相同时披露。',
        '- 全部为合成压力场景；不构成县域真实收益、成本或距离改善，也未做显著性检验。',
        '- 归档字节保持运行当时的 CRLF 换行原样；换行缺陷已在本次收尾修复，故重新运行会产出 LF。',
        '', '## 复现', '', '```powershell',
        manifest['reproduction_command'], '```', '',
    ]
    path.write_text('\n'.join(lines), encoding='utf8', newline='\n')


def main(argv=None):
    parser = argparse.ArgumentParser(description='Freeze one R18 run into benchmarks/b03/r18_accepted')
    parser.add_argument('--run-dir', type=Path, required=True)
    parser.add_argument('--accepted-dir', type=Path, default=Path('../benchmarks/b03/r18_accepted'))
    parser.add_argument('--r17-evidence', type=Path,
                        default=Path('../benchmarks/b03/r17_accepted/r17_accepted_original.json'))
    args = parser.parse_args(argv)
    run_dir: Path = args.run_dir
    accepted: Path = args.accepted_dir
    if not (run_dir / 'summary.json').is_file():
        parser.error(f'{run_dir} is not a completed R18 run directory')
    if accepted.exists() and any(accepted.iterdir()):
        parser.error(f'{accepted} is not empty; keep the existing archive and choose another location')
    rels = collect_archive(run_dir)
    run_manifest = json.loads((run_dir / 'manifest.json').read_text(encoding='utf8'))
    run_summary = json.loads((run_dir / 'summary.json').read_text(encoding='utf8'))
    if run_summary['protocol'] != PROTOCOL:
        parser.error(f"unexpected protocol {run_summary['protocol']!r}")
    audit = recompute(run_dir, run_manifest, run_summary)
    audit['r17_cross_check'] = cross_check_r17(args.r17_evidence, audit['cases'])
    audit['scope'] = ('independent per-order recomputation from archived raw CandidatePlans plus '
                      'summary cross-check; not a new solver run and not a second constraint validation')
    manifest = build_manifest(run_dir, rels, run_manifest, run_summary, audit)
    accepted.mkdir(parents=True, exist_ok=True)
    for rel in rels:
        target = accepted / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes((run_dir / rel).read_bytes())
    write_json(accepted / 'r18_accepted_manifest.json', manifest)
    write_json(accepted / 'r18_multiscene_audit.json', audit)
    write_readme(accepted / 'README.md', manifest)
    for entry in manifest['files']:
        if sha256_file(accepted / entry['path']) != entry['sha256']:
            raise SystemExit(f"archived copy corrupted: {entry['path']}")
    print(f"Frozen {manifest['file_count']} files ({manifest['total_bytes']} bytes) -> {accepted}")
    print('recomputed cases: ' + ', '.join(f"{c['case']}={c['status']}/{c['distance_priority']}"
                                           for c in audit['cases']))
    print(f"R17 cross-check: {audit['r17_cross_check']['status']}")
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
