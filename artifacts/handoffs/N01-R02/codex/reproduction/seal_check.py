"""Read-only final evidence/candidate/protection validation after delivery writes."""
import hashlib
import importlib.util
import json
import os
import sys
from pathlib import Path

sys.dont_write_bytecode = True
root = Path.cwd().resolve()
assert root == Path(r'D:\Agent\DeepSeekHarness\IntelligentLogisticsDispatchingAgent').resolve()
out = root/'artifacts/handoffs/N01-R02/codex'
load = lambda p: json.loads((root/p).read_text(encoding='utf-8'))
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
evidence = load('artifacts/handoffs/N01-R02/codex/evidence.json')
scope = load('tmp/N01-R02/scope-before.json')
assert evidence['output_count'] == len(evidence['output_manifest'])
for row in evidence['output_manifest']:
    p=root/row['path']
    assert p.is_file() and sha(p)==row['sha256'] and p.stat().st_size==row['bytes'],row['path']
for rel,h in evidence['input_artifact_hashes'].items():
    assert sha(root/rel)==h,rel
for rel,h in scope['protected'].items():
    assert (root/rel).is_file() and sha(root/rel)==h,rel
seen=set()
for current,dirs,files in os.walk(root):
    dirs[:]=[d for d in dirs if d not in scope['excluded_derived_parts'] and not (Path(current)/d).relative_to(root).as_posix().startswith(tuple(p.rstrip('/') for p in scope['own_output_prefixes']))]
    for name in files:
        rel=(Path(current)/name).relative_to(root).as_posix()
        if not rel.startswith(tuple(scope['own_output_prefixes'])):seen.add(rel)
assert not seen-set(scope['protected'])-set(scope['whitelist'])
for command in evidence['commands']:
    assert sha(root/command['descriptor'])==command['descriptor_sha256']
    assert sha(root/command['original_log_path'])==sha(root/command['durable_log_path'])==command['log_sha256']
for row in load('artifacts/handoffs/N01-R02/codex/preserved-copies.json')['copies']:
    assert sha(root/row['source'])==sha(root/row['target'])==row['sha256']
spec=importlib.util.spec_from_file_location('n01_r02_seal_gate_runner',root/'scripts/gates.py')
module=importlib.util.module_from_spec(spec);sys.modules[spec.name]=module;spec.loader.exec_module(module)
runner=module.GateRunner(root,1,'auto',out_dir=root/'tmp/N01-R02/gate-probe')
assert runner.compute_revision()==evidence['code_revision'] and runner.dirty_tree_hash()==evidence['dirty_tree_hash']
g00=load('artifacts/gates/G00.json')
problems=runner.previous_gate_record_problems('G00',g00)
assert problems==load('artifacts/handoffs/N01-R02/codex/legacy-freeze-g00-state.json')['runner_prerequisite_problems']
spec=importlib.util.spec_from_file_location('n01_r02_seal_plan_checker',root/'tools/ai_coding_plan/validate_plan.py')
checker=importlib.util.module_from_spec(spec);sys.modules[spec.name]=checker;spec.loader.exec_module(checker)
link_errors=checker.local_links(root/'docs/handoffs/N01-R02/codex.md',root)+checker.local_links(out/'enum-and-event-tables.md',root)
assert not link_errors,link_errors
assert evidence['status']=='READY_FOR_INDEPENDENT_REVIEW' and not evidence['G00_valid'] and not evidence['N03_may_start']
print(json.dumps(dict(status='PASS', check='read-only post-delivery seal', output_count=evidence['output_count'], output_and_input_and_command_hashes_match=True, preserved_copies_match=True, protected_file_count=len(scope['protected']), protected_files_unchanged=True, candidate_unchanged=True, code_revision=evidence['code_revision'], evidence_sha256=sha(out/'evidence.json'), handoff_sha256=sha(root/'docs/handoffs/N01-R02/codex.md'), local_links_valid=True, G00_valid=False, N03_may_start=False, stop_writing=True),ensure_ascii=False))
