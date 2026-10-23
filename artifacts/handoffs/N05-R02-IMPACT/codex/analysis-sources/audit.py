from __future__ import annotations
import ast
import datetime as dt
import hashlib
import importlib.util
from pathlib import Path
import shutil
import sys
from common import ROOT,TEMP,OUT,CACHE,sha,j,dump,now,gate_module

g=gate_module();runner=g.GateRunner(ROOT,1,'auto');rows=runner.relevant_manifest_rows()
revision='content-sha256:'+hashlib.sha256('\n'.join(f'{p}\0{d}' for p,d,_ in rows).encode()).hexdigest()
dirty='content-sha256:'+hashlib.sha256('\n'.join(f'{p}\0{s}\0{d}' for p,d,s in rows).encode()).hexdigest()
assert revision==runner.compute_revision()=='content-sha256:477a883d2a29deb5cb60f8269c8712693d9e7aedeb3a620ba4953a630289158c'
assert dirty==runner.dirty_tree_hash()=='content-sha256:eaea942624f00e5da16e89a3e744d3a2c1c659fcf9eeda0a23787116681d636f'
assert len(rows)==82 and not (ROOT/'.git').exists();runner.revision=revision
old=j(ROOT/'artifacts/handoffs/N05-R01/codex/initial-audit.json');before={r['path']:r['sha256'] for r in old['candidate_rows']};current={p:d for p,d,_ in rows}
changed=sorted(p for p in before if current[p]!=before[p]);assert set(before)==set(current)
assert changed==['packages/domain/src/logistics_domain/states.py','tests/integration/test_p02_01_primitives_and_states.py','tests/unit/test_p02_01_primitives_and_states.py']
verified={};reasons={};checks=[]
def bind(p,digest=None,reason='Phase01 required evidence'):
    assert p not in ('artifacts/gates/G01.json','artifacts/gates/G01-codex-review.json') and not Path(p).is_absolute() and '..' not in Path(p).parts,p
    actual=sha(ROOT/p);assert digest is None or actual==digest,'input drift: '+p
    verified[p]=actual;reasons.setdefault(p,[])
    if reason not in reasons[p]:reasons[p].append(reason)
def stamped(stamp):
    v=dt.datetime.fromisoformat(stamp.replace('Z','+00:00'));assert v.tzinfo is not None and v<=dt.datetime.now(dt.timezone.utc),stamp
g00=j(ROOT/'artifacts/gates/G00.json');bind('artifacts/gates/G00.json','c5e57a6d250ff83f9ceed524f6219a3b1cb9474697a3354b5f102fe24c3bb7e4','frozen prerequisite G00')
assert not runner.previous_gate_record_problems('G00',g00)
for p,d in g00['input_artifact_hashes'].items():bind(p,d,'G00 frozen input dependency')
for c in g00['commands']:bind(c['log_path'],c['log_hash'],'actual G00 prerequisite command log')
expected_pre={'P01-01':'f044a885c622d17d320cb5cd9f6ce247d6f6434d9163f16cf63e377acb56790e',
              'P01-02':'4474dfeb0169a8e5c7ac8ceddcf09e9b44ad0d45f368243766542bd48b3ecae4',
              'P01-03':'d9ee646eb4989bc5e1833538aaa9d7de5842250418404c6230f8b81a67b1bfaa'}
for task in runner.phase_tasks():
    tid=task['id'];prepath=f'artifacts/handoffs/{tid}/zcode/precheck.json';pre=j(ROOT/prepath)
    bind(prepath,expected_pre[tid],tid+' required independent precheck')
    assert pre['task_id']==tid and pre['phase_gate']=='G01' and pre['status']=='Z_PRECHECK_PASSED' and pre['reviewer']
    assert not runner.recorded_input_problems(tid,pre['verified_input_hashes'],require=runner.required_precheck_inputs(task))
    assert 'artifacts/gates/G01.json' not in pre['verified_input_hashes'] and 'artifacts/gates/G01-codex-review.json' not in pre['verified_input_hashes']
    for p,d in pre['verified_input_hashes'].items():bind(p,d,tid+' precheck transitive binding (P02 evidence/seal are sealed provenance only)')
    if tid=='P01-01':
        assert pre['code_revision']==revision and pre['dirty_tree_hash']==dirty and len(pre['verified_input_hashes'])==54
        assert pre['round']=='p02-f01-impact-m01';stamped(pre['reviewed_at'])
    for c in pre['commands']:
        bind(c['log_path'],c['log_sha256'],tid+' actual/reused precheck raw log')
        raw=(ROOT/c['log_path']).read_text(encoding='utf-8');parsed=g.parse_pytest_counts(raw)
        if c.get('test_counts'):assert all(parsed.get(k,0)==v for k,v in c['test_counts'].items()),c['log_path']
    dshpath=f'artifacts/handoffs/{tid}/dsh/evidence.json';dsh=j(ROOT/dshpath);bind(dshpath,reason=tid+' implementation evidence')
    assert dsh['task_id']==tid and dsh['phase_gate']=='G01' and dsh['status']=='READY_FOR_ZCODE' and dsh['role']=='dsh'
    entries=dsh['artifacts'].values() if isinstance(dsh['artifacts'],dict) else dsh['artifacts']
    for row in [*entries,*dsh.get('deliverable_files',[])]:
        bind(row['path'],row['sha256'],tid+' actual delivered artifact')
        if 'bytes' in row:assert (ROOT/row['path']).stat().st_size==row['bytes'],row['path']
    for p,row in dsh['command_logs'].items():bind(p,row['sha256'],tid+' implementation raw log; historical scope retained')
    bind(dsh['dependency_evidence']['G00']['path'],dsh['dependency_evidence']['G00']['sha256'],tid+' G00 binding')
    for p in [*task['files'],task['unit_test'],task['integration_test'],task['prompt'],task['task_doc'],task['report'],f'docs/handoffs/{tid}/dsh.md',f'docs/handoffs/{tid}/zcode.md']:
        bind(p,reason=tid+' delivered implementation/test/config or frozen task/handoff')
    checks.append({'task':tid,'precheck_sha256':expected_pre[tid],'input_count':len(pre['verified_input_hashes']),'command_count':len(pre['commands'])})
assert sum(c['input_count'] for c in checks)==123 and sum(c['command_count'] for c in checks)==29
assert all(c.passed for c in runner.check_previous_gates()+runner.check_zcode_precheck())
assert runner.check_legacy_demo_untouched().passed

# Actual layer scanner input inventory, including every later-phase source it reads.
spec=importlib.util.spec_from_file_location('n05_r02_architecture',ROOT/'scripts/check_architecture.py')
a=importlib.util.module_from_spec(spec);sys.modules[spec.name]=a;spec.loader.exec_module(a)
layer_modules=[];domain_imports=[]
for layer,path in a.iter_modules(ROOT):
    p=path.relative_to(ROOT).as_posix();bind(p,reason='actual full-layer scanner input; domain marker import dependency where applicable')
    layer_modules.append({'layer':layer,'path':p,'sha256':sha(path)})
    if layer=='domain':
        for node in ast.walk(ast.parse(path.read_text(encoding='utf-8'))):
            names=[v.name.split('.',1)[0] for v in node.names] if isinstance(node,ast.Import) else ([node.module.split('.',1)[0]] if isinstance(node,ast.ImportFrom) and not node.level else [])
            for name in names:
                assert name in sys.stdlib_module_names or name=='logistics_domain',(p,name)
                domain_imports.append({'path':p,'line':node.lineno,'root':name})
assert len(layer_modules)==10 and sum(r['layer']=='domain' for r in layer_modules)==4
for p in ('AGENTS.md','AI-CODING-PLAN.md','docs/plan/GATE_EXECUTION_CONTRACT.md','docs/workflow/HANDOFF_CONTRACT.md',
          'docs/agent-toolchain/00-common.md','docs/agent-toolchain/08-codex-final-review.md','docs/agent-toolchain/15-autonomous-orchestration.md',
          'docs/architecture/ARCHITECTURE_OVERVIEW.md','docs/architecture/IMPLEMENTATION_CONVENTIONS.md'):
    bind(p,reason='actual execution/independence/input-scope or import-layer rule')
assert sha(ROOT/'docs/agent-toolchain/15-autonomous-orchestration.md')=='055ffe685e22dc2beb1165abeb44f6260aaa1d9a6d71e512bec07c771ac69e34'

oldreview=j(ROOT/'artifacts/gates/G01-codex-review.json');oldgate=j(ROOT/'artifacts/gates/G01.json')
assert sha(ROOT/'artifacts/gates/G01.json')=='a7eed6aee3f0e21b39e440aee6a7d4f2f5f74b5d1407eb4011eac7215a3b18c4'
assert sha(ROOT/'artifacts/gates/G01-codex-review.json')=='c41888a77a22d146502dd5f91de85f12f036c4cbd70fbf3de00d45789630a275'
assert runner.stale_input_hashes(oldgate['input_artifact_hashes'])==[]
drift=runner.stale_input_hashes(oldreview['verified_input_hashes'])

# Old independent controlled probes only exercise unchanged gate/checker logic.
prior=j(ROOT/'artifacts/handoffs/N05/codex/independent-probes.json');assert prior['passed'] and prior['count']==52 and all(r['passed'] for r in prior['results'])
for p in ('scripts/gates.py','scripts/check_architecture.py','tmp/N05/probes.py','tmp/N05/capture.py',
          'artifacts/handoffs/N05/codex/independent-probes.json','artifacts/handoffs/N05/codex/commands/independent-probes.log',
          'artifacts/handoffs/N05/codex/commands/clean-env-sync-r02.log','artifacts/handoffs/N05/codex/commands/clean-env-outside-imports-r02.log'):
    bind(p,oldreview['verified_input_hashes'][p],'unchanged controlled 52 rework probes / frozen clean-install proof reused, not rerun')

# Archive before either official record can be replaced. Historical report is
# marker authorization provenance; no active source is replaced by an archive.
archive=OUT/'archive'/dt.datetime.now(dt.timezone.utc).strftime('%Y-%m-%dT%H%M%SZ');assert not archive.exists()
oldpaths=[ROOT/'artifacts/gates/G01.json',ROOT/'artifacts/gates/G01-codex-review.json',*sorted((ROOT/'artifacts/gates/G01-logs').glob('*.log'))]
assert len(oldpaths)==14
history_source=ROOT/'artifacts/handoffs/P02-01/dsh/archive/f01-before/docs__implementation__reports__P02-01.md'
assert sha(history_source)==oldreview['verified_input_hashes']['docs/implementation/reports/P02-01.md']
oldpaths += [history_source,ROOT/'docs/prompts/02-domain/P02-01-primitives-and-states.md',
             ROOT/'artifacts/dispatch/2026-10-04/orchestration/codex/N05-R02-IMPACT.md',
             ROOT/'artifacts/dispatch/2026-10-04/orchestration/codex/P02-F01-recovery-routing.md',
             ROOT/'artifacts/dispatch/2026-10-04/orchestration/zcode/P01-01-IMPACT-F01-M01-scope-resolution.md']
archived=[]
for p in oldpaths:
    rel=p.relative_to(ROOT).as_posix();dest=archive/rel;dest.parent.mkdir(parents=True,exist_ok=True);digest=sha(p);shutil.copyfile(p,dest)
    assert sha(p)==sha(dest)==digest
    row={'original_path':rel,'archive_path':dest.relative_to(ROOT).as_posix(),'sha256':digest,'bytes':p.stat().st_size};archived.append(row)
    bind(row['archive_path'],digest,'immutable history; previous official bytes / marker authorization / specific dispatched scope')
assert 'packages/domain/src/logistics_domain/__init__.py' in history_source.read_text(encoding='utf-8')
assert '包marker只有确需导出本任务类型时可修改' in (ROOT/'docs/prompts/02-domain/P02-01-primitives-and-states.md').read_text(encoding='utf-8')
dump(OUT/'archive-manifest.json',{'created_at':now(),'file_count':len(archived),'old_official_file_count':14,'byte_identical':True,'files':archived})
bind((OUT/'archive-manifest.json').relative_to(ROOT).as_posix(),reason='byte-exact archive identity list')

# Record every old direct input disposition instead of silently refreshing 262 hashes.
decisions=[]
for p,d in oldreview['verified_input_hashes'].items():
    if p in verified:action='retain';reason='; '.join(reasons[p])
    elif p.startswith('tests/') and 'test_p02_01_' in p:action='remove';reason='P02 business tests not executed/adopted as Phase01 correctness proof; remain in true global auto candidate'
    elif p.startswith('docs/implementation/') and 'P02-01' in p or p=='docs/handoffs/P02-01/dsh.md':action='remove';reason='current P02 business documentation/handoff not Phase01 proof; old marker authorization report bound only as immutable history'
    elif p.startswith('artifacts/handoffs/P02-01/'):action='remove';reason='P02 business log/outputs not adopted; sealed evidence/seal separately retained only through mandatory precheck provenance'
    elif p.startswith('artifacts/dispatch/') or p.startswith('tmp/') or p.startswith('docs/handoffs/N05') or p.startswith('artifacts/handoffs/N05'):
        action='remove';reason='nonessential previous process/audit/output history; exact used controlled probe and clean-install evidence retained separately'
    else:action='remove';reason='not adopted for this Phase01 conclusion; actual required dependency present in current closure or archived historical reference'
    decisions.append({'path':p,'old_sha256':d,'action':action,'reason':reason})
for p in verified:
    if p not in oldreview['verified_input_hashes']:decisions.append({'path':p,'action':'add','reason':'; '.join(reasons[p])})
for p in ('tests/unit/test_p02_01_primitives_and_states.py','tests/integration/test_p02_01_primitives_and_states.py',
          'docs/implementation/P02-01.md','docs/implementation/reports/P02-01.md','docs/handoffs/P02-01/dsh.md'):
    assert p not in verified,'business input accidentally retained: '+p
for row in layer_modules:assert row['path'] in verified
for p,d in verified.items():assert sha(ROOT/p)==d,'post-preparation drift: '+p
if not CACHE.exists():shutil.copytree(Path(r'C:\Users\30382\AppData\Local\Temp\N05-independent\2026-10-04-main\uv-cache'),CACHE)
result={'task_id':'N05-R02-IMPACT','passed':True,'actual_utc':now(),'code_revision':revision,'dirty_tree_hash':dirty,'candidate_file_count':82,
        'candidate_rows':[{'path':p,'sha256':d,'bytes':s} for p,d,s in rows],'changed_since_R01':changed,
        'old_G01_direct_input_drift':[],'old_review_drift':drift,'prechecks':checks,'G00_sha256':sha(ROOT/'artifacts/gates/G00.json'),
        'layer_modules':layer_modules,'domain_imports':domain_imports,'verified_input_hashes':dict(sorted(verified.items())),
        'input_decisions':decisions,'retained_P02_seal_scope':'transitive sealed provenance in required P01-01 precheck; no business conclusion; later dependency attachment must append without rewriting it',
        'P02_business_acceptance':False,'cache_seed':'read-only copy of previous exclusive N05 cache into this card system TEMP; global configuration untouched'}
dump(OUT/'initial-audit.json',result)
print({'passed':True,'revision':revision,'dirty':dirty,'files':82,'precheck_inputs':123,'precheck_commands':29,
       'old_review_drift_count':len(drift),'current_review_closure_inputs':len(verified),'layer_modules':10,'archived_files':len(archived)})
