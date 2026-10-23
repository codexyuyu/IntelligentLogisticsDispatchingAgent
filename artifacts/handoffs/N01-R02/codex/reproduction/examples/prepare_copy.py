"""Prepare this round's isolated replay; never execute or overwrite old evidence."""
import ast
import difflib
import hashlib
import json
from pathlib import Path

ROOT = Path.cwd().resolve()
EXPECTED_ROOT = Path(r'D:\Agent\DeepSeekHarness\IntelligentLogisticsDispatchingAgent')
if ROOT != EXPECTED_ROOT:
    raise SystemExit('Wrong workspace root; no writes authorized')
HERE = ROOT / 'tmp/N01-R02/examples'
OUT = ROOT / 'artifacts/handoffs/N01-R02/codex/examples'
SOURCE = ROOT / 'tmp/N01-R01/verify_contracts.py'
TARGET = HERE / 'verify_design_examples.py'
source = SOURCE.read_text(encoding='utf-8')
text = source

def replace_once(before, after):
    global text
    if text.count(before) != 1:
        raise ValueError('Unexpected inherited source fragment: ' + before[:120])
    text = text.replace(before, after, 1)

replace_once('ROOT=Path.cwd().resolve()', "sys.dont_write_bytecode=True\nROOT=Path.cwd().resolve()\nif ROOT != Path(r'D:\\Agent\\DeepSeekHarness\\IntelligentLogisticsDispatchingAgent'):\n    raise SystemExit('Wrong workspace root; no writes authorized')")
replace_once("OUT=ROOT/'artifacts/handoffs/N01-R01/codex'", "OUT=ROOT/'artifacts/handoffs/N01-R02/codex/examples'\nOUT.mkdir(parents=True,exist_ok=True)")
replace_once("scope=json.loads((ROOT/'tmp/N01-R01/scope-before.json').read_text(encoding='utf-8'))", "scope=json.loads((ROOT/'tmp/N01-R02/scope-before.json').read_text(encoding='utf-8'))")
replace_once("        if value['kind'] not in {'vehicle','order','cargo','dock','worker','equipment','warehouse','zone','location','transport_task','warehouse_task'}:raise ValueError('unknown entity kind in example')", "        parse('EntityKind',value['kind']) # Sole source: this round's normative enum.")
replace_once("[t['id'] for t in json.loads((ROOT/'tmp/N01-R01/before/docs/plan/TASK_MANIFEST.json').read_text(encoding='utf-8'))['tasks']]", "scope['manifest_task_ids']")
replace_once("dir=ROOT/'tmp/N01-R01'", "dir=ROOT/'tmp/N01-R02/examples'")
replace_once("check('3418 protected files preserve original bytes',lambda:not protected_changes)", "check(str(len(scope['protected']))+' this-round protected files preserve original bytes',lambda:not protected_changes)")
marker = "summary=dict(status='PASS' if all(r['passed'] for r in results) else 'FAIL'"
replace_once(marker, "inherited_check_count=len(results)\nfrom event_reference_examples import run_examples\nevent_examples=run_examples(check,parse,spec,digest,patch,epoch)\n" + marker)
replace_once("'resolve examples check reference metadata and failure ordering only; no real capability parser/worker was run.'", "'resolve examples check reference metadata and failure ordering only; no real capability parser/worker was run.', 'Inherited parse-only adapters still do not enforce CalendarDTO overlap, RegionRef nonempty nodes, OnArc temporal order, or complete Scenario FK/calendar binding integrity; N02-R01 limitations are retained.', 'New event-reference predicates validate the normative mapping against a fixed design fact snapshot; they are not domain classes, ingest services, DB/solver/SimPy acceptance, or live revalidation of old audit references.', 'Inherited entity adapters verify named field structure and selected primitive constraints; CargoType/Skill/Qualification and full inherited entity state machines remain outside this bounded design harness.'")
replace_once("(OUT/('contract-validation'+suffix+'.json')).write_text", "summary.update(round='N01-R02',inherited_check_count=inherited_check_count,event_reference_check_count=len(results)-inherited_check_count,event_case_counts=event_examples['case_counts'],source_inputs={p:sha(ROOT/p) for p in ['contracts/changes/N01-R01-contract-decisions.json','docs/plan/TASK_MANIFEST.json','tmp/N01-R02/scope-before.json','tmp/N01-R01/verify_contracts.py','tmp/N01-R02/examples/verify_design_examples.py','tmp/N01-R02/examples/event_reference_examples.py','tools/ai_coding_plan/validate_plan.py','tools/ai_coding_plan/render_plan.py']})\n(OUT/('contract-validation'+suffix+'.json')).write_text")
replace_once("resource=dict(kind='equipment',value=equipment))", "resource=dict(kind='equipment',value=equipment),event_references=event_examples)")

# Validate syntax before writing the bounded copy. The old source is never imported.
ast.parse(text)
HERE.mkdir(parents=True, exist_ok=True)
OUT.mkdir(parents=True, exist_ok=True)
TARGET.write_text(text, encoding='utf-8')
diff = ''.join(difflib.unified_diff(source.splitlines(True), text.splitlines(True), fromfile='tmp/N01-R01/verify_contracts.py', tofile='tmp/N01-R02/examples/verify_design_examples.py'))
(OUT / 'inherited-harness-copy.diff').write_text(diff, encoding='utf-8')
(OUT / 'inherited-harness-source.json').write_text(json.dumps({'source': SOURCE.relative_to(ROOT).as_posix(), 'source_sha256': hashlib.sha256(SOURCE.read_bytes()).hexdigest(), 'new_source': TARGET.relative_to(ROOT).as_posix(), 'new_source_sha256': hashlib.sha256(TARGET.read_bytes()).hexdigest(), 'scope': 'Bounded copy of prior design examples; unchanged old source/evidence; all fresh outputs in N01-R02 examples.'}, indent=2) + '\n', encoding='utf-8')
print(json.dumps({'prepared': TARGET.relative_to(ROOT).as_posix(), 'old_source_sha256': hashlib.sha256(SOURCE.read_bytes()).hexdigest(), 'new_source_sha256': hashlib.sha256(TARGET.read_bytes()).hexdigest()}))
