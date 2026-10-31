"""Isolated, no-database acceptance check for Wenchang breakdown rescue.

Run from the project root in the backend's existing Python environment:
    python scripts/check_fault_rescue_solver.py

This command does NOT connect to PostgreSQL, access DeepSeek, or write data.
Requires ortools and the local backend source (editable install or PYTHONPATH).
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'apps' / 'backend' / 'src'))

from logistics_backend.application.fault_rescue_showcase import (  # noqa: E402
    VEHICLES, solve_breakdown_showcase,
)


def main() -> int:
    try:
        result = solve_breakdown_showcase(3000)
    except ImportError as exc:
        print(f'缺少 OR-Tools 等 Python 依赖：{exc}', file=sys.stderr)
        return 2
    print(json.dumps({
        'status': result['status'],
        'reason': result.get('reason'),
        'diagnostic': result.get('solver_diagnostic'),
        'candidate_valid': result.get('candidate_valid'),
        'rescue_assignments': result.get('rescue_assignments'),
        'recovered_orders': result.get('recovered_orders'),
        'metrics': result.get('metrics'),
    }, ensure_ascii=False, indent=2))
    if result['status'] != 'solved' or not result['candidate_valid']:
        print('验收失败：OR-Tools 没有返回通过独立校验的候选。', file=sys.stderr)
        return 1
    assert result['metrics']['candidate']['delivered_orders'] == 8
    assert result['metrics']['no_rescue']['delivered_orders'] == 6
    assert result['recovered_orders'] == 2
    assert set(result['rescue_assignments']) == {'demo-o4', 'demo-o5'}
    assert all(v in (VEHICLES[0], VEHICLES[2]) for v in result['rescue_assignments'].values())
    print('验收通过：真实 OR-Tools 求解 + 2 单接管 + 独立时序/载重/交接校验。')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
