"""Unit tests use archived evidence and explicit fake failures; NO claimed new solves."""
import collections
import hashlib
import json
from pathlib import Path

import pytest

from app.contracts.entities import PlanningSnapshot
from tools import r18_evidence_audit as audit
from tools import r18_multiscene_ablation as multi

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / 'data/scenarios/two_warehouses_20_orders.json'
ARCHIVED = ROOT / 'benchmarks/b03/r17_accepted/r17_accepted_original.json'


def archived():
    return json.loads(ARCHIVED.read_text(encoding='utf8'))


def test_archive_r17_matches_snapshot_hash_and_independently_recalculates_metrics():
    evidence = archived()
    report = audit.audit_evidence(evidence, scenario_bytes=SOURCE.read_bytes())
    assert report['scenario_sha256'] == hashlib.sha256(SOURCE.read_bytes()).hexdigest()
    assert report['handoff_wait_saved_s'] == 2100
    assert report['handoff_wait_reduction_pct'] == 46.67
    assert report['additional_deep_wall_ms'] == 11672
    assert [r['handoff_wait_s'] for r in report['modes']] == [4500, 2400]
    assert [r['distance_m'] for r in report['modes']] == [56000, 56000]
    assert [r['order_count'] for r in report['modes']] == [20, 20]


def test_archive_tampering_with_wait_or_order_fails_closed():
    evidence = archived()
    evidence['results'][1]['candidate_plan']['warehouse']['warehouse_handoffs'][0]['ready_at_s'] += 15
    with pytest.raises(ValueError, match='coordination metrics'):
        audit.audit_evidence(evidence)
    evidence = archived()
    evidence['results'][0]['candidate_plan']['routing']['routes'][0]['stops'][1]['order_ids'].append('ord_002')
    with pytest.raises(ValueError, match='duplicate delivery'):
        audit.audit_evidence(evidence)


def test_archive_rejects_wrong_sha_and_failed_validation():
    with pytest.raises(ValueError, match='SHA256'):
        audit.audit_evidence(archived(), scenario_bytes=b'not the real file')
    evidence = archived()
    evidence['results'][1]['validation']['status'] = 'failed'
    with pytest.raises(ValueError, match='not passed'):
        audit.audit_evidence(evidence)


@pytest.mark.parametrize('size,seed', multi.CASE_DESIGNS)
def test_deterministic_synthetic_cases_keep_integrity_and_all_strata(size, seed):
    original = PlanningSnapshot.model_validate_json(SOURCE.read_text(encoding='utf8'))
    before_sha = hashlib.sha256(SOURCE.read_bytes()).hexdigest()
    one = multi.prepare_case(original, size=size, seed=seed)
    two = multi.prepare_case(original, size=size, seed=seed)
    assert one == two
    assert len(one.orders) == size
    assert len(one.operations) == size
    assert len(one.stock_lots) == size
    assert len(one.vehicles) == 4 and len(one.warehouses) == 2
    assert one.matrix == original.matrix
    assert collections.Counter((o.warehouse_id, o.temperature_zone) for o in one.orders) == {
        ('wh_1', 'chilled'): size // 4, ('wh_1', 'frozen'): size // 4,
        ('wh_2', 'chilled'): size // 4, ('wh_2', 'frozen'): size // 4,
    }
    assert {op.order_ids[0] for op in one.operations} == {o.order_id for o in one.orders}
    assert hashlib.sha256(SOURCE.read_bytes()).hexdigest() == before_sha


def test_pair_inspection_archived_success_no_unsupported_distance_savings():
    pair = multi.inspect_pair(archived())
    assert pair['status'] == 'complete_validated_pair'
    assert pair['distance_priority'] == 'equal_distance'
    assert pair['wait_saved_s'] == 2100
    assert pair['wait_reduction_pct'] == 46.67
    assert pair['deep_extra_wall_ms'] == 11672


def test_distance_difference_suppresses_wait_percentage():
    evidence = archived()
    evidence['results'][1]['candidate_plan']['routing']['routes'][0]['distance_m'] += 100
    evidence['results'][1]['candidate_plan']['coordination']['selected_distance_m'] += 100
    evidence['results'][1]['coordination']['selected_distance_m'] += 100
    evidence['results'][1]['distance_m'] += 100
    pair = multi.inspect_pair(evidence)
    assert pair['status'] == 'complete_validated_pair'
    assert pair['distance_priority'] == 'deep_longer'
    assert pair['wait_reduction_pct'] is None


def test_failed_validation_or_missing_order_prevents_comparable_pair():
    evidence = archived()
    evidence['results'][1]['status'] = 'failed'
    out = multi.inspect_pair(evidence)
    assert out['status'] == 'incomplete'
    assert out['wait_reduction_pct'] is None


def test_full_dry_run_and_collision_guard(tmp_path):
    folder = tmp_path / 'preview'
    assert multi.execute(base_file=SOURCE, budget_ms=90000, outdir=folder, case_count=5, dry_run=True) is None
    manifest = json.loads((folder/'manifest.json').read_text(encoding='utf8'))
    assert len(manifest['cases']) == 5
    assert len({c['scenario_sha256'] for c in manifest['cases']}) == 5
    assert all(c['status'] == 'not_started' for c in manifest['cases'])
    assert not (folder/'summary.json').exists()
    with pytest.raises(FileExistsError):
        multi.execute(base_file=SOURCE, budget_ms=90000, outdir=folder, case_count=5, dry_run=True)


def test_failure_is_checkpointed_and_does_not_get_averaged(monkeypatch, tmp_path):
    def no_real_solver(**kwargs):
        return {'order_ids': list(kwargs['order_ids']), 'per_mode_total_budget_ms': kwargs['budget_ms'],
                'results': [
                    {'mode': 'sequential', 'status': 'failed', 'error_type': 'RuntimeError', 'error': 'fixture_no_solver'},
                    {'mode': 'deep', 'status': 'failed', 'error_type': 'RuntimeError', 'error': 'fixture_no_solver'},
                ]}
    monkeypatch.setattr(multi, 'run_comparison', no_real_solver)
    folder = tmp_path/'failed'
    result = multi.execute(base_file=SOURCE, budget_ms=90000, outdir=folder, case_count=3)
    assert result['case_count'] == 3
    assert result['valid_equal_distance_pairs'] == 0
    assert result['average_wait_reduction_pct'] is None
    assert len(list((folder/'raw').glob('*.json'))) == 3
    assert (folder/'summary.csv').exists()
    assert '不报告' in (folder/'summary.md').read_text(encoding='utf8')


def test_partial_valid_pairs_not_presented_as_statistical_mean():
    passed = multi.inspect_pair(archived())
    failed = {'status': 'incomplete', 'distance_priority': 'not_comparable', 'wait_reduction_pct': None}
    rows = [{'case':'x','analysis':passed}, {'case':'y','analysis':passed}, {'case':'z','analysis':failed}]
    report = multi.build_summary(rows, 90000)
    assert report['valid_equal_distance_pairs'] == 2
    assert report['average_wait_reduction_pct'] is None
