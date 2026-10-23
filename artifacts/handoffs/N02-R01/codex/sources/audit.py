"""N02-R01 independent byte audit; no business or official gate mutation."""
import ast
import difflib
import hashlib
import importlib.util
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.dont_write_bytecode = True
ROOT = Path.cwd().resolve()
EXPECTED = Path(r'D:\Agent\DeepSeekHarness\IntelligentLogisticsDispatchingAgent').resolve()
if ROOT != EXPECTED:
    raise SystemExit('wrong working root')
OUT = ROOT / 'artifacts/handoffs/N02-R01/codex'
OUT.mkdir(parents=True, exist_ok=True)

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def read(path):
    return json.loads((ROOT / path).read_text(encoding='utf-8-sig'))

def write(name, value):
    (OUT / name).write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')

def load_runner():
    spec = importlib.util.spec_from_file_location('n02_r01_runner', ROOT / 'scripts/gates.py')
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module.GateRunner(ROOT, 1, 'auto', out_dir=ROOT / 'tmp/N02-R01/g00-probe')

# Independently traverse and apply the exact, inspected current runner policy.
ROOTS = ('apps', 'packages', 'scripts', 'tests', 'tools', 'contracts', 'data', 'deploy', '.github',
         'docs/architecture', 'docs/api', 'docs/algorithms')
FILES = ('pyproject.toml', 'uv.lock', 'package.json', 'package-lock.json', '.python-version',
         '.node-version', 'OWNERSHIP.json', 'PROJECT_MASTER_PLAN.md', 'TASK_GRAPH.md',
         'docs/plan/TASK_MANIFEST.json', 'docs/plan/PHASE_GATES.md',
         'docs/plan/GATE_EXECUTION_CONTRACT.md', 'docs/plan/TEST_FIXTURES.md')
EXCLUDED = {'.venv', 'node_modules', '__pycache__', '.git', '.mimosa', '.ruff_cache', '.pytest_cache', '.mypy_cache'}
PREFIXES = ('artifacts/', 'tmp/', 'tools/bin/', 'demo/', 'demos/', 'platform/', 'backend/', 'frontend/', 'benchmarks/')
SUFFIXES = ('.pyc', '.pyo', '.log', '.zip', '.png', '.jpg', '.pdf')

def walk(base):
    for current, dirs, files in os.walk(base):
        dirs[:] = [d for d in dirs if d not in EXCLUDED]
        for name in files:
            yield Path(current) / name

candidate = {}
for base in ROOTS:
    for p in walk(ROOT / base):
        rel = p.relative_to(ROOT).as_posix()
        if not rel.startswith(PREFIXES) and not rel.endswith(SUFFIXES):
            candidate[rel] = p
for rel in FILES:
    if (ROOT / rel).is_file():
        candidate[rel] = ROOT / rel
rows = [dict(path=p, sha256=sha(candidate[p]), bytes=candidate[p].stat().st_size) for p in sorted(candidate)]
revision = 'content-sha256:' + hashlib.sha256('\n'.join(r['path']+'\0'+r['sha256'] for r in rows).encode()).hexdigest()
dirty = 'content-sha256:' + hashlib.sha256('\n'.join(r['path']+'\0'+str(r['bytes'])+'\0'+r['sha256'] for r in rows).encode()).hexdigest()
claimed = read('artifacts/handoffs/N01-R01/codex/candidate-files.json')
runner = load_runner()
evidence = read('artifacts/handoffs/N01-R01/codex/evidence.json')
problems = []
if rows != claimed['files']:
    problems.append('candidate list differs')
if revision != claimed['code_revision'] or revision != runner.compute_revision() or dirty != claimed['dirty_tree_hash'] or dirty != runner.dirty_tree_hash():
    problems.append('candidate formula differs')
write('candidate-audit.json', dict(root=str(ROOT), git_present=(ROOT/'.git').exists(), code_revision=revision,
      dirty_tree_hash=dirty, file_count=len(rows), runner_agrees=revision==runner.compute_revision(), files=rows))

scope = read('artifacts/handoffs/N01-R01/codex/scope-before.json')
governance = read('artifacts/handoffs/N01-R01/codex/governance-files.json')
changes = []
patch = []
before_problems = []
for rel in sorted(scope['whitelist']):
    old = ROOT/'tmp/N01-R01/before'/rel
    now = ROOT/rel
    expected = scope['before'][rel]
    old_hash = sha(old) if old.is_file() else None
    new_hash = sha(now) if now.is_file() else None
    if old_hash != expected:
        before_problems.append(rel)
    if old_hash != new_hash:
        changes.append(dict(path=rel, before_sha256=old_hash, after_sha256=new_hash,
                            before_bytes=old.stat().st_size if old.is_file() else 0,
                            after_bytes=now.stat().st_size if now.is_file() else 0))
        patch.extend(difflib.unified_diff(old.read_text(encoding='utf-8-sig').splitlines(keepends=True) if old.is_file() else [],
                     now.read_text(encoding='utf-8-sig').splitlines(keepends=True) if now.is_file() else [],
                     fromfile='before/'+rel, tofile='after/'+rel))
patch_text = ''.join(patch)
(OUT/'governance-diff.patch').write_text(patch_text, encoding='utf-8')
patch_matches = patch_text == (ROOT/'artifacts/handoffs/N01-R01/codex/governance-diff.patch').read_text(encoding='utf-8')
if before_problems or changes != governance['files'] or not patch_matches:
    problems.append('governance byte/diff mismatch')
write('governance-audit.json', dict(whitelist_count=len(scope['whitelist']), changed_count=len(changes),
      original_byte_errors=before_problems, exact_diff_matches=patch_matches, files=changes))

protected = [{'path':p, 'expected_sha256':h, 'actual_sha256':sha(ROOT/p) if (ROOT/p).is_file() else None}
             for p,h in scope['protected'].items()]
protected_errors = [r['path'] for r in protected if r['expected_sha256'] != r['actual_sha256']]
if protected_errors:
    problems.append('protected bytes changed')
write('protected-audit.json', dict(count=len(protected), unchanged=len(protected)-len(protected_errors),
      mismatches=protected_errors, files=protected))

checks = []
for row in evidence['outputs']+[evidence['handoff']]:
    p = ROOT/row['path']
    actual = sha(p) if p.is_file() else None
    checks.append(dict(path=row['path'], expected_sha256=row['sha256'], actual_sha256=actual,
                       matches=actual==row['sha256'] and ('bytes' not in row or p.stat().st_size==row['bytes'])))
for row in evidence['commands']:
    p = ROOT/row['log_path']
    checks.append(dict(path=row['log_path'], expected_sha256=row['log_hash'], actual_sha256=sha(p),
                       matches=sha(p)==row['log_hash'], declared_exit_code=row['exit_code'], argv=row['argv']))
for rel,h in evidence['verified_input_hashes'].items():
    checks.append(dict(path=rel, expected_sha256=h, actual_sha256=sha(ROOT/rel), matches=sha(ROOT/rel)==h))
if not all(r['matches'] for r in checks):
    problems.append('handoff output/log/input hashes differ')
write('n01-evidence-audit.json', dict(check_count=len(checks), passed=sum(r['matches'] for r in checks), checks=checks))

freeze = read('docs/architecture/CONTRACT_FREEZE.json')
freeze_rows = [dict(path=r['path'], recorded=r['sha256'], actual=sha(ROOT/r['path'])) for r in freeze['artifacts']]
baseline = read('docs/architecture/BASELINE_INVENTORY.json')
baseline_rows = [dict(path=r['source_path'], recorded=r['sha256'], actual=sha(ROOT/r['source_path'])) for r in baseline['entries']]
registered = {r['path'] for r in baseline_rows}
ordinary = {p.relative_to(ROOT).as_posix() for p in walk(ROOT/'demo')}
unregistered = sorted(ordinary-registered)
if any(r['recorded'] != r['actual'] for r in baseline_rows) or unregistered:
    problems.append('registered legacy baseline mismatch or uncovered ordinary files')
write('baseline-audit.json', dict(count=len(baseline_rows), passed=sum(r['recorded']==r['actual'] for r in baseline_rows),
      unregistered_ordinary_files=unregistered, derived_trees='NOT_RUN; excluded by frozen coverage policy', files=baseline_rows))
g00 = read('artifacts/gates/G00.json')
inputs = [dict(path=p, recorded=h, actual=sha(ROOT/p)) for p,h in g00['input_artifact_hashes'].items()]
previous = [c.as_dict() for c in runner.check_previous_gates()]
write('old-freeze-g00-audit.json', dict(freeze=freeze_rows, freeze_drift=[r['path'] for r in freeze_rows if r['recorded']!=r['actual']],
      g00_inputs=inputs, g00_input_drift=[r['path'] for r in inputs if r['recorded']!=r['actual']],
      g00_log_hashes=[dict(path=c['log_path'], recorded=c['log_hash'], actual=sha(ROOT/c['log_path'])) for c in g00['commands']],
      dependency_evidence=g00['dependency_evidence_hashes'], runner_checks=previous))

def record_ast(path):
    tree=ast.parse(path.read_text(encoding='utf-8-sig'))
    return ast.dump(next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='record_g00'), include_attributes=False)
record_unchanged = record_ast(ROOT/'tools/ai_coding_plan/validate_plan.py')==record_ast(ROOT/'tmp/N01-R01/before/tools/ai_coding_plan/validate_plan.py')
if not record_unchanged:
    problems.append('record_g00 AST differs')

# Capture the non-derived project tree before this review's authorized changes.
snapshot = {}
for p in walk(ROOT):
    rel = p.relative_to(ROOT).as_posix()
    if rel.startswith(('tmp/', 'artifacts/handoffs/N02-R01/', 'docs/handoffs/N02-R01/')):
        continue
    snapshot[rel] = sha(p)
write('review-scope-before.json', dict(files=snapshot, excluded_derived_parts=sorted(EXCLUDED),
      allowed_exact=['docs/architecture/CONTRACT_FREEZE.json','docs/architecture/CONTRACT_FREEZE.md',
                     'artifacts/gates/G00.json','artifacts/gates/G00-checks.log'],
      allowed_new_prefixes=['docs/handoffs/N02-R01/','artifacts/handoffs/N02-R01/','tmp/N02-R01/']))
summary = dict(task_id='N02-R01', audited_at=datetime.now(timezone.utc).isoformat(),root=str(ROOT),git_present=(ROOT/'.git').exists(),
      code_revision=revision,dirty_tree_hash=dirty,candidate_files=len(rows),governance_changes=len(changes),
      whitelist_files=len(scope['whitelist']),protected_files=len(protected),evidence_hash_checks=len(checks),
      legacy_registered_files=len(baseline_rows),record_g00_AST_unchanged=record_unchanged,
      freeze_drift_count=sum(r['recorded']!=r['actual'] for r in freeze_rows),
      g00_input_drift_count=sum(r['recorded']!=r['actual'] for r in inputs),errors=problems)
write('audit-summary.json', summary)
print(json.dumps(summary,ensure_ascii=False,indent=2))
raise SystemExit(1 if problems else 0)
