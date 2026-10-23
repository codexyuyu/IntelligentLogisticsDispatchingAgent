"""Read source bytes and preserve this bounded repair's evidence; never sign a gate."""
import ast
import difflib
import hashlib
import importlib.util
import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.dont_write_bytecode = True
root = Path.cwd().resolve()
assert root == Path(r'D:\Agent\DeepSeekHarness\IntelligentLogisticsDispatchingAgent').resolve()
out = root / 'artifacts/handoffs/N01-R02/codex'
scope = json.loads((root / 'tmp/N01-R02/scope-before.json').read_text(encoding='utf-8'))
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
digest = lambda b: hashlib.sha256(b).hexdigest()
def write_json(name, data):
    p = out / name
    assert not p.exists(), f'preserve {p}'
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')

copies = []
def preserve(source, target):
    a, b = root / source, out / target
    assert not b.exists(), f'preserve {b}'
    b.parent.mkdir(parents=True, exist_ok=True)
    b.write_bytes(a.read_bytes())
    assert sha(a) == sha(b)
    copies.append(dict(source=source, target=b.relative_to(root).as_posix(), sha256=sha(a), bytes=a.stat().st_size))

changes, diff = [], []
for rel in scope['whitelist']:
    old, new = root / 'tmp/N01-R02/before' / rel, root / rel
    assert sha(old) == scope['before'][rel]
    assert sha(old) != sha(new), rel
    changes.append(dict(path=rel, before_sha256=sha(old), after_sha256=sha(new), before_bytes=old.stat().st_size, after_bytes=new.stat().st_size))
    diff.extend(difflib.unified_diff(old.read_bytes().decode('utf-8').splitlines(keepends=True), new.read_bytes().decode('utf-8').splitlines(keepends=True), fromfile='before/' + rel, tofile='after/' + rel))
    preserve('tmp/N01-R02/before/' + rel, 'before/' + rel)
patch = ''.join(diff).encode('utf-8')
assert not (out / 'governance-diff.patch').exists()
(out / 'governance-diff.patch').write_bytes(patch)

protected_errors = []
for rel, expected in scope['protected'].items():
    p = root / rel
    if not p.is_file() or sha(p) != expected:
        protected_errors.append(rel)
seen = set()
for current, dirs, files in os.walk(root):
    dirs[:] = [d for d in dirs if d not in scope['excluded_derived_parts'] and not (Path(current) / d).relative_to(root).as_posix().startswith(tuple(p.rstrip('/') for p in scope['own_output_prefixes']))]
    for name in files:
        rel = (Path(current) / name).relative_to(root).as_posix()
        if not rel.startswith(tuple(scope['own_output_prefixes'])):
            seen.add(rel)
unexpected = sorted(seen - set(scope['protected']) - set(scope['whitelist']))
missing = sorted(set(scope['protected']) - seen)
assert not protected_errors and not unexpected and not missing, (protected_errors, unexpected, missing)
assert not (root / '.git').exists()

old_json = json.loads((root / 'tmp/N01-R02/before/contracts/changes/N01-R01-contract-decisions.json').read_text(encoding='utf-8'))
new_json = json.loads((root / 'contracts/changes/N01-R01-contract-decisions.json').read_text(encoding='utf-8'))
old_types = {row['name']: row for row in old_json['types']}
new_types = {row['name']: row for row in new_json['types']}
assert set(old_types) == set(new_types) and len(new_types) == 196
payload_names = set(new_types['EventPayload']['variants'].values())
allowed_type_changes = {'EntityKind', 'EntityRef'} | payload_names
actual_type_changes = {name for name in new_types if old_types[name] != new_types[name]}
assert actual_type_changes == allowed_type_changes
for name in payload_names:
    a, b = old_types[name].copy(), new_types[name].copy()
    assert b['rules'] == a['rules'] + ['event.entity_ref_mapping']
    del a['rules']; del b['rules']
    assert a == b, name
old_modules = old_json['module_dependencies']
new_modules = new_json['module_dependencies']
primitive = 'packages/domain/src/logistics_domain/primitives.py'
states = 'packages/domain/src/logistics_domain/states.py'
assert old_modules[primitive] == [] and new_modules[primitive] == [states]
assert {k:v for k,v in old_modules.items() if k != primitive} == {k:v for k,v in new_modules.items() if k != primitive}
members = new_types['EntityKind']['members']
targets = new_json['entity_ref_targets']
rules = new_json['event_entity_ref_mapping']
assert len(members) == len(set(members.values())) == len(targets) == 45
assert set(members.values()) == set(targets)
assert new_types['EntityRef']['fields'] == dict(kind='EntityKind', id='UUID', revision='NonNegativeInt?')
assert len(rules) == 10 and set(rules) == set(new_types['EventPayload']['variants'])
catalogue = (root / 'docs/architecture/DOMAIN_CATALOG.md').read_text(encoding='utf-8')
main_entities = re.findall(r'^\| ([A-Za-z][A-Za-z0-9]*) / ', catalogue, re.M)
aux_entities = re.findall(r'`([A-Za-z][A-Za-z0-9]*)\(', catalogue.split('## 必需辅助实体（不替代上表）',1)[1].split('## 数据库约束与索引',1)[0])
assert len(main_entities) == 32 and len(aux_entities) == 11
assert set(main_entities + aux_entities) == {v['type'] for v in targets.values() if v['category'] == 'entity'}
for doc in ('docs/architecture/DATA_CONTRACTS.md', 'docs/architecture/TYPE_DEFINITION_OWNERSHIP.md'):
    line = next(line for line in (root / doc).read_text(encoding='utf-8').splitlines() if line.startswith('| EntityKind |'))
    assert dict(re.findall(r'([A-Z][A-Z0-9_]*)=([a-z][a-z0-9_]*)', line)) == members
    ref = next(line for line in (root / doc).read_text(encoding='utf-8').splitlines() if line.startswith('| EntityRef |'))
    assert 'kind:EntityKind; id:UUID; revision:NonNegativeInt?' in ref

def ast_facts(p):
    source = p.read_bytes().decode('utf-8')
    tree = ast.parse(source)
    tests = {cls.name + '.' + n.name: ast.dump(n, include_attributes=False) for cls in tree.body if isinstance(cls, ast.ClassDef) for n in cls.body if isinstance(n, ast.FunctionDef) and n.name.startswith('test_')}
    record = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == 'record_g00')
    raw = ''.join(source.splitlines(keepends=True)[record.lineno - 1:record.end_lineno]).encode('utf-8')
    return tests, ast.dump(record, include_attributes=False), raw
old_ast = ast_facts(root / 'tmp/N01-R02/before/tools/ai_coding_plan/validate_plan.py')
new_ast = ast_facts(root / 'tools/ai_coding_plan/validate_plan.py')
assert len(old_ast[0]) == 43 and len(new_ast[0]) == 73
assert all(new_ast[0].get(name) == value for name, value in old_ast[0].items())
assert old_ast[1:] == new_ast[1:]

module_spec = importlib.util.spec_from_file_location('n01_r02_final_gate_runner', root / 'scripts/gates.py')
module = importlib.util.module_from_spec(module_spec)
sys.modules[module_spec.name] = module
module_spec.loader.exec_module(module)
runner = module.GateRunner(root, 1, 'auto', out_dir=root / 'tmp/N01-R02/gate-probe')
rows = [dict(path=p, sha256=h, bytes=s) for p,h,s in runner.relevant_manifest_rows()]
# Independent whole-tree traversal of the declared inclusion policy.
independent = []
root_names = set(module.REVISION_INCLUDE_ROOTS)
directories = module.REVISION_INCLUDE_CONTRACT_ROOTS
explicit = set(module.REVISION_INCLUDE_FILES) | set(module.REVISION_INCLUDE_PLAN_FILES)
for current, dirs, files in os.walk(root):
    dirs[:] = [d for d in dirs if d not in module.REVISION_EXCLUDE_PARTS and not (Path(current) / d).relative_to(root).as_posix().startswith(tuple(p.rstrip('/') for p in module.REVISION_EXCLUDE_PREFIXES))]
    for name in files:
        p = Path(current) / name
        rel = p.relative_to(root).as_posix()
        included = rel.split('/')[0] in root_names or any(rel.startswith(d + '/') for d in directories) or rel in explicit
        if included and not rel.startswith(module.REVISION_EXCLUDE_PREFIXES) and not rel.endswith(module.REVISION_EXCLUDE_SUFFIXES):
            independent.append(dict(path=rel, sha256=sha(p), bytes=p.stat().st_size))
independent.sort(key=lambda row: row['path'])
assert independent == rows and len(rows) == 77
revision = 'content-sha256:' + digest('\n'.join(r['path'] + '\0' + r['sha256'] for r in rows).encode('utf-8'))
dirty = 'content-sha256:' + digest('\n'.join(r['path'] + '\0' + str(r['bytes']) + '\0' + r['sha256'] for r in rows).encode('utf-8'))
assert revision == runner.compute_revision() and dirty == runner.dirty_tree_hash()
before_candidate = json.loads((out / 'candidate-before.json').read_text(encoding='utf-8'))
assert {r['path'] for r in rows} == {r['path'] for r in before_candidate['files']}
candidate_changes = [r['path'] for r in rows if r['sha256'] != next(a['sha256'] for a in before_candidate['files'] if a['path'] == r['path'])]
assert sorted(candidate_changes) == sorted(scope['whitelist'])

verified_commands = []
for rel in ('tmp/N01-R02/validator/plan-validation-02-command.json', 'artifacts/handoffs/N01-R02/codex/examples/contract-check-final01-command.json'):
    cmd = json.loads((root / rel).read_text(encoding='utf-8'))
    expected = cmd.get('log_hash', cmd.get('log_sha256'))
    assert sha(root / cmd['log_path']) == expected
    assert cmd['cwd'] == str(root) and type(cmd['exit_code']) is int and cmd['exit_code'] == 0
    for p,h in cmd.get('inputs_sha256', cmd.get('verified_input_hashes')).items():
        assert sha(root / p) == h, p
    verified_commands.append(dict(descriptor=rel, descriptor_sha256=sha(root / rel), log_path=cmd['log_path'], log_sha256=expected, exit_code=cmd['exit_code'], all_current_inputs_match=True))

g00 = json.loads((root / 'artifacts/gates/G00.json').read_text(encoding='utf-8'))
g00_problems = runner.previous_gate_record_problems('G00', g00)
freeze = json.loads((root / 'docs/architecture/CONTRACT_FREEZE.json').read_text(encoding='utf-8'))
freeze_drift = [row['path'] for row in freeze['artifacts'] if not (root / row['path']).is_file() or sha(root / row['path']) != row['sha256']]
assert g00_problems and len(freeze_drift) == 4
assert len([p for p in g00_problems if 'drifted after the gate was recorded' in p]) == 5

for p in sorted((root / 'tmp/N01-R02/validator').glob('*')):
    if p.is_file():
        preserve(p.relative_to(root).as_posix(), 'validator/' + p.name)
for name in ('verify_design_examples.py', 'event_reference_examples.py', 'capture_examples.py', 'prepare_copy.py'):
    preserve('tmp/N01-R02/examples/' + name, 'reproduction/examples/' + name)
preserve('tmp/N01-R02/audit_final.py', 'reproduction/audit_final.py')
preserve('tmp/N01-R02/capture.py', 'reproduction/capture.py')
write_json('preserved-copies.json', dict(status='PASS', copies=copies))
write_json('governance-diff.json', dict(changed_count=len(changes), changes=changes, added_existing_source_paths=[], deleted_existing_source_paths=[], patch_sha256=digest(patch), semantic=dict(defined_type_count=196, added_types=[], modified_types=sorted(actual_type_changes), payload_fields_and_variants_unchanged=True, other_types_unchanged=True, module_edges_added=[dict(source=primitive, target=states)], task_order_and_manifest_unchanged=True)))
write_json('candidate-after.json', dict(code_revision=revision, dirty_tree_hash=dirty, file_count=len(rows), formula=dict(code_revision='content-sha256:sha256(UTF8(newline.join(path + NUL + sha256(bytes))))', dirty_tree_hash='content-sha256:sha256(UTF8(newline.join(path + NUL + decimal_byte_size + NUL + sha256(bytes))))'), independent_file_walk_matches=True, changed_candidate_paths=candidate_changes, files=rows))
write_json('protected-file-audit.json', dict(status='PASS', checked_at=datetime.now(timezone.utc).isoformat(), registered_count=len(scope['protected']), unchanged_count=len(scope['protected']), changed_or_missing=protected_errors, unexpected_outside_scope=unexpected, missing_paths=missing, baseline_path='artifacts/handoffs/N01-R02/codex/scope-before.json', baseline_sha256=sha(out / 'scope-before.json'), excluded_derived_parts=scope['excluded_derived_parts'], whitelist=scope['whitelist'], own_output_prefixes=scope['own_output_prefixes'], official_records_and_old_handoffs_and_logs_unchanged=True))
write_json('legacy-freeze-g00-state.json', dict(read_only=True, official_g00_sha256=sha(root / 'artifacts/gates/G00.json'), official_g00_status=g00['status'], current_g00_valid=False, runner_prerequisite_problems=g00_problems, old_freeze_artifact_count=len(freeze['artifacts']), old_freeze_drift=freeze_drift, freeze_json_sha256=sha(root / 'docs/architecture/CONTRACT_FREEZE.json'), freeze_md_sha256=sha(root / 'docs/architecture/CONTRACT_FREEZE.md'), gate_recording_not_run=True, N03_may_start=False))
summary = dict(status='PASS', task='N01-R02', code_revision=revision, dirty_tree_hash=dirty, candidate_file_count=len(rows), changed_existing_file_count=5, protected_file_count=len(scope['protected']), enum_members=45, catalogue_entities=32, catalogue_auxiliary_entities=11, pure_targets=['TravelMatrix', 'RegionRef'], event_mappings=10, type_count=196, original_test_methods_unchanged=43, current_test_methods=73, record_g00_ast_and_bytes_unchanged=True, record_g00_bytes_sha256=digest(new_ast[2]), final_commands=verified_commands, G00_valid=False, N03_may_start=False, writes_only_own_evidence=True)
write_json('audit-summary.json', summary)
print(json.dumps(summary, ensure_ascii=False))
