"""Independent reproduction of the remaining N02-F02 normative closure gap."""
import hashlib
import json
import re
import sys
from pathlib import Path

sys.dont_write_bytecode=True
root=Path.cwd().resolve()
if root != Path(r'D:\Agent\DeepSeekHarness\IntelligentLogisticsDispatchingAgent').resolve():
    raise SystemExit('wrong working root')
sys.path.insert(0,str(root/'tools/ai_coding_plan'))
import validate_plan
design=json.loads((root/'contracts/changes/N01-R01-contract-decisions.json').read_text(encoding='utf-8'))
manifest=json.loads((root/'docs/plan/TASK_MANIFEST.json').read_text(encoding='utf-8'))
types={r['name']:r for r in design['types']}
data=(root/'docs/architecture/DATA_CONTRACTS.md').read_text(encoding='utf-8')
source=root/'tmp/N01-R01/verify_contracts.py'
ns={'__name__':'independent_readonly_examples'}
# Definitions only; before the first check call, scratch generation, or output writes.
prefix=source.read_text(encoding='utf-8').splitlines()[:226]
exec(compile('\n'.join(prefix),str(source),'exec'),ns)
examples=json.loads((root/'artifacts/handoffs/N01-R01/codex/contract-examples-final03.json').read_text(encoding='utf-8'))
results=[]
def probe(label,fn,expected_accepted):
    try:
        value=fn()
        row=dict(probe=label,accepted=True,result=value)
    except Exception as exc:
        row=dict(probe=label,accepted=False,exception=str(exc))
    row['expected_accepted']=expected_accepted
    row['matches_expected']=row['accepted']==expected_accepted
    results.append(row)
    print(json.dumps(row,ensure_ascii=False))
patch=ns['patch'];parse=ns['parse'];scenario=ns['scenario'];digest=ns['digest']
probe('saved empty ScenarioBundle',lambda:scenario(examples['scenario']),True)
probe('ScenarioRef dataset version mismatch',lambda:scenario(patch(examples['scenario'],['ref','dataset_version'],2)),False)
probe('ScenarioInput expected_plan injection',lambda:scenario(patch(examples['scenario'],['input','expected_plan'],{})),False)
probe('calendar overlap negative',lambda:ns['calendar'](patch(examples['calendar'],['intervals',0,'end_s'],11)),False)
probe('CalendarDTO mapped overlap; harness limitation',lambda:parse('CalendarDTO',dict(patch(examples['calendar'],['intervals',0,'end_s'],11),schema_version='2.0.0')),False)
probe('RegionRef empty nodes; harness limitation',lambda:parse('RegionRef',dict(region_id=examples['actor']['scope_id'],node_ids=[])),False)
probe('OnArcLocation reversed timestamps; harness limitation',lambda:parse('OnArcLocation',dict(kind='on_arc',from_node_id=examples['actor']['actor_id'],to_node_id=examples['actor']['scope_id'],departed_at_s=10,expected_arrival_s=5,progress_numerator=1,progress_denominator=2)),False)
bundle=patch(examples['scenario'],['input','snapshot','resources','equipment'],[examples['resource']['value']])
bundle['spec']['size']['equipment']=1
bundle['input']['snapshot']['hash']=digest({k:v for k,v in bundle['input']['snapshot'].items() if k!='hash'})
bundle['ref']['content_hash']=ns['scenario_hash'](bundle)
probe('Scenario dangling warehouse/missing calendar binding; harness limitation',lambda:scenario(bundle),False)
entity_ref=dict(kind='vehicle',id=examples['actor']['actor_id'],revision=0)
probe('harness hardcoded vehicle EntityRef',lambda:parse('EntityRef',entity_ref),True)
probe('harness rejects driver EntityRef despite Driver master entity',lambda:parse('EntityRef',dict(entity_ref,kind='driver')),False)

uses=[]
for row in design['types']:
    if 'EntityRef' in row.get('fields',{}).values():
        uses.append(dict(name=row['name'],fields=row['fields'],task=row['task'],path=row['path']))
occurrences=[]
for base in ['docs/architecture','docs/api','contracts','tools/ai_coding_plan','apps','packages','tests']:
    for p in sorted((root/base).rglob('*')):
        if not p.is_file() or any(part in {'.venv','node_modules','__pycache__'} for part in p.parts):
            continue
        if p.suffix not in {'.md','.json','.py','.ts'}:
            continue
        for number,line in enumerate(p.read_text(encoding='utf-8-sig',errors='replace').splitlines(),1):
            if 'EntityKind' in line:
                occurrences.append(dict(path=p.relative_to(root).as_posix(),line=number,text=line))
source_lines=[dict(line=i,text=line) for i,line in enumerate(data.splitlines(),1) if 'EntityKind' in line]
payloads=types['EventPayload']['variants']
paths={name:types[name]['fields'] for name in payloads.values()}
normative=dict(finding='N02-R01-F02-C01',parent_finding='N02-F02',
    description='EntityKind source names it but does not define its complete members or exact serialized values',
    entity_kind=types['EntityKind'],entity_ref=types['EntityRef'],scenario_spec=types['ScenarioSpec'],
    event_payload=types['EventPayload'],payload_fields=paths,source_lines=source_lines,
    current_checker_errors=validate_plan.validate_contract_decisions(design,manifest),
    entity_kind_members_present=bool(types['EntityKind'].get('members')),
    entity_ref_existing_leaf=types['EntityRef']['kind']=='existing',
    occurrences=occurrences,harness_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),
    scope='normative design closure only; no business runtime or vulnerability finding',
    harness_limitations=[r for r in results if not r['matches_expected']])
out=root/'artifacts/handoffs/N02-R01/codex/closure-probe.json'
out.write_text(json.dumps(dict(normative=normative,probes=results),ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps(dict(normative_gap_reproduced=not normative['entity_kind_members_present'],
      checker_errors=normative['current_checker_errors'],definition_occurrences=len(occurrences),
      harness_semantic_limits=len(normative['harness_limitations']),runtime_acceptance='NOT_RUN'),ensure_ascii=False))
# Zero means the audit reproduction ran, not that G00 passed.
raise SystemExit(0)
