import copy
import importlib.util
import json
import re
import sys
from functools import cache
from pathlib import Path

sys.dont_write_bytecode=True
root=Path.cwd().resolve()
assert root==Path(r'D:\Agent\DeepSeekHarness\IntelligentLogisticsDispatchingAgent').resolve()
spec=json.loads((root/'contracts/changes/N01-R01-contract-decisions.json').read_text(encoding='utf-8'))
manifest=json.loads((root/'docs/plan/TASK_MANIFEST.json').read_text(encoding='utf-8'))
loader=importlib.util.spec_from_file_location('independent_design_validator',root/'tools/ai_coding_plan/validate_plan.py')
module=importlib.util.module_from_spec(loader)
loader.loader.exec_module(module)
errors=module.validate_contract_decisions(spec,manifest)
assert not errors
nodes={r['id']:r for r in manifest['tasks']+manifest['gates']}
tasks={r['id']:r for r in manifest['tasks']}
assert len(nodes)==149
@cache
def ancestors(tid):
    result=set()
    for dep in nodes[tid]['deps']:
        assert dep in nodes
        result.add(dep)
        result.update(ancestors(dep))
    return result

for tid,row in nodes.items():
    ancestors(tid)
    assert {k for k,n in nodes.items() if tid in n['deps']}==set(row.get('blocks',[]))
for gate in manifest['gates']:
    assert set(gate['deps'])=={t['id'] for t in manifest['tasks'] if t['phase']==gate['phase']}
for task in manifest['tasks']:
    if task['phase']>0:
        assert 'G'+str(task['phase']-1).zfill(2) in ancestors(task['id'])
definitions={r['name']:r for r in spec['types']}
def refs(row):
    return set(re.findall(r'\b[A-Za-z][A-Za-z0-9_]*\b',' '.join(row.get('fields',{}).values())))&definitions.keys() | set(row.get('variants',{}).values()) | ({row['base']} if 'base' in row else set())
reachable=set()
def visit(name):
    if name in reachable:
        return
    reachable.add(name)
    for ref in refs(definitions[name]):
        visit(ref)
visit('JobRequest')
job_types=[dict(name=n,task=definitions[n]['task'],path=definitions[n]['path']) for n in sorted(reachable)]
assert len(job_types)==11
for r in job_types:
    assert r['path'] in tasks[r['task']]['allowed_files']
assert 'P02-04' in ancestors('P05-03')
mutations=[]
for label in ['duplicate','future','wrong_mapping','outside_whitelist','domain_to_contracts']:
    bad=copy.deepcopy(spec)
    row=next(r for r in bad['types'] if r['name']=='RequestRef')
    if label=='duplicate':
        bad['types'].append(copy.deepcopy(row))
    if label=='future':
        row['task']='P32-01'
    if label=='wrong_mapping':
        bad['job_kind_mapping']['metric']='SimulationJobPayload'
    if label=='outside_whitelist':
        row['path']='packages/domain/src/logistics_domain/unlisted.py'
    if label=='domain_to_contracts':
        bad['module_dependencies'][row['path']].append('packages/contracts/src/logistics_contracts/runtime.py')
    result=module.validate_contract_decisions(bad,manifest)
    assert result,label
    mutations.append(dict(mutation=label,rejected=True,errors=result))
required_headers=['Files created','Files modified','Tests added','Commands executed','Test results','Known limitations','Remaining risks']
p00=[]
for task in manifest['tasks']:
    if task['phase']!=0:
        continue
    body=(root/task['report']).read_text(encoding='utf-8')
    missing=[p for p in task['allowed_files'] if not (root/p).is_file()]
    missing_headers=[h for h in required_headers if h not in body]
    assert not missing and not missing_headers
    p00.append(dict(task=task['id'],allowed_files=task['allowed_files'],missing=missing,missing_report_headers=missing_headers,
                    reports='historical implementation reports only; not current independent acceptance'))
trace=(root/'docs/plan/REQUIREMENTS_TRACEABILITY.md').read_text(encoding='utf-8')
trace_rows=[line for line in trace.splitlines() if re.match(r'\| R\d\d \|',line)]
assert len(trace_rows)==18
for line in trace_rows:
    assert re.search(r'P\d\d-\d\d',line)
    assert all(n in nodes for n in re.findall(r'P\d\d-\d\d|G\d\d',line))
summary=dict(design_errors=errors,registered_types=len(spec['types']),tasks=len(tasks),gates=len(manifest['gates']),
    plan_version=manifest['plan_version'],DAG='acyclic; reverse edges, gate dependencies and phase barriers match',
    requirement_groups=len(trace_rows),phase00_delivery_files=sum(len(r['allowed_files']) for r in p00),phase00=p00,
    JobRequest_declared_reachable_types=job_types,JobRequest_module_count=len({r['path'] for r in job_types}),
    early_runtime_consumers=[dict(task=tid,early_runtime_available='P02-04' in ancestors(tid)) for tid in ['P05-01','P05-02','P05-03','P16-01']],
    single_fault_mutations=mutations,limitation='existing leaves are not expanded by the registered design graph; semantic closure requires source review')
(root/'artifacts/handoffs/N02-R01/codex/design-graph-probe.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps(summary,ensure_ascii=False))
