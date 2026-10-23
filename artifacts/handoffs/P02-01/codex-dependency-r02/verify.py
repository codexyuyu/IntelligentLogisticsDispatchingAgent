"""Read-only dependency audit; output is this task's new evidence, not DSH evidence."""
import datetime
import hashlib
import importlib.util
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[4]
OUT = Path(__file__).resolve().parent
inputs = {}
problems = []
counts = {}
historical_failed_commands = []

def digest(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()

def read(relative):
    p = ROOT / relative
    inputs[relative] = digest(p)
    return json.loads(p.read_text(encoding='utf-8'))

def verify(relative, expected):
    actual = digest(ROOT / relative)
    inputs[relative] = actual
    if actual != expected:
        problems.append(relative)

for task, number in [('N05-R02-IMPACT', 44), ('N05-R03-ENV', 36)]:
    seal = read(f'artifacts/handoffs/{task}/codex/seal.json')
    assert len(seal['files']) == number
    for f in seal['files']:
        verify(f['path'], f['sha256'])
        if (ROOT / f['path']).stat().st_size != f['bytes']:
            problems.append(f['path'] + ': size')
    counts[task + '_sealed_files'] = number

for gate in ['G00', 'G01']:
    record = read(f'artifacts/gates/{gate}.json')
    assert record['status'] == 'passed'
    for path, sha in record['input_artifact_hashes'].items():
        verify(path, sha)
    for command in record['commands']:
        assert command['exit_code'] == 0
        verify(command['log_path'], command.get('log_sha256', command.get('log_hash')))
    counts[gate + '_inputs'] = len(record['input_artifact_hashes'])

review = read('artifacts/gates/G01-codex-review.json')
assert review['status'] == 'approved'
for path, sha in review['verified_input_hashes'].items():
    verify(path, sha)
counts['G01_review_inputs'] = len(review['verified_input_hashes'])
audit = read('artifacts/handoffs/N05-R03-ENV/codex/final-audit.json')
for path, sha in audit['official_raw_log_hashes'].items():
    verify(path, sha)
counts['G01_logs'] = len(audit['official_raw_log_hashes'])

for task in ['P01-01', 'P01-02', 'P01-03']:
    precheck = read(f'artifacts/handoffs/{task}/zcode/precheck.json')
    assert precheck['status'] == 'Z_PRECHECK_PASSED'
    for path, sha in precheck['verified_input_hashes'].items():
        verify(path, sha)
    for command in precheck['commands']:
        verify(command['log_path'], command.get('log_sha256', command.get('log_hash')))
        if command['exit_code'] != 0:
            historical_failed_commands.append({'task': task, 'command': command})
    counts[task + '_precheck_inputs'] = len(precheck['verified_input_hashes'])
    counts[task + '_precheck_commands'] = len(precheck['commands'])

evidence = read('artifacts/handoffs/P02-01/dsh/evidence.json')
seal = read('artifacts/handoffs/P02-01/dsh/seal.json')
for key in ['artifacts', 'commands_executed']:
    for row in evidence.get(key, []):
        path = row.get('path') or row.get('log_path')
        sha = row.get('sha256') or row.get('log_sha256') or row.get('log_hash')
        if path and sha:
            verify(path, sha)
verify(seal['evidence']['path'], seal['evidence']['sha256'])
for path, details in seal['handoffs'].items():
    verify(path, details['sha256'])
counts['DSH_F01_bound_products_and_logs'] = 14

spec = importlib.util.spec_from_file_location('dependency_gate_audit', ROOT / 'scripts/gates.py')
module = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = module
spec.loader.exec_module(module)
runner = module.GateRunner(ROOT, 1, 'auto')
computed = runner.compute_revision()
assert computed == audit['code_revision'], (computed, audit['code_revision'])
assert not problems, problems
result = {'task_id': 'P02-01-DEP-R02', 'status': 'VERIFIED_DEPENDENCY_ONLY',
          'author': 'Codex root', 'implementation_author': 'DSH-A original session',
          'generated_at_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
          'root': str(ROOT), 'code_revision': computed, 'counts': counts,
          'verified_input_hashes': inputs, 'hash_problems': problems,
          'current_G01': inputs['artifacts/gates/G01.json'],
          'current_G01_review': inputs['artifacts/gates/G01-codex-review.json'],
          'original_DSH_evidence': inputs['artifacts/handoffs/P02-01/dsh/evidence.json'],
          'original_DSH_seal': inputs['artifacts/handoffs/P02-01/dsh/seal.json'],
          'P02_business_acceptance': False, 'business_tests_rerun': False,
          'reuse_limit': 'DSH F01 52 tests retain original evidence; G01 226 tests cover Phase01 only; historical 272 is not current-candidate regression',
          'historical_failed_commands': historical_failed_commands,
          'next_executor': 'Original independent ZCode P02-01 F01 recheck'}
(OUT / 'evidence.json').write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
print(json.dumps({k: v for k, v in result.items() if k != 'verified_input_hashes'}, ensure_ascii=False))
