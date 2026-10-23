from __future__ import annotations
import datetime as dt
import hashlib
import json
from pathlib import Path
from common import ROOT,OUT,sha,j,dump,now,gate_module,capture

# Check-only is an extra post-sign freshness/immutability check, never the signer.
paths=[ROOT/'artifacts/gates/G00.json',ROOT/'artifacts/gates/G00-checks.log',ROOT/'artifacts/gates/G01.json',ROOT/'artifacts/gates/G01-codex-review.json',*sorted((ROOT/'artifacts/gates/G01-logs').glob('*.log'))]
assert len(paths)==16
def snapshot():return {p.relative_to(ROOT).as_posix():sha(p) for p in paths}
before=snapshot();c=capture('post-sign-check-only',['uv','run','python','scripts/gates.py','--phase','01','--revision','auto','--check-only']);after=snapshot()
dump(OUT/'check-only-byte-audit.json',{'exit_code':c.returncode,'file_count':16,'before':before,'after':after,'all_bytes_unchanged':before==after})
assert c.returncode==0 and before==after,'post-sign freshness or byte immutability failure'
g=gate_module();runner=g.GateRunner(ROOT,1,'auto');rows=runner.relevant_manifest_rows();revision=runner.compute_revision();runner.revision=revision
gate=j(ROOT/'artifacts/gates/G01.json');review=j(ROOT/'artifacts/gates/G01-codex-review.json');audit=j(OUT/'initial-audit.json');problems=[]
def require(ok,label):
    if not ok:problems.append(label)
def stamped(value):
    stamp=dt.datetime.fromisoformat(value.replace('Z','+00:00'));require(stamp.tzinfo is not None and stamp<=dt.datetime.now(dt.timezone.utc),'invalid/future UTC '+value)
require(gate['schema_version']=='1.0.0' and gate['gate_id']=='G01' and gate['phase']==1,'wrong Gate identity')
require(gate['status']=='passed' and gate['failed_checks']==[],'official Gate failed')
require(review['status']=='approved' and review['review_context']['independent'],'review not independent approval')
require(revision==gate['code_revision']==review['code_revision']==audit['code_revision'],'candidate revision drift')
require(runner.dirty_tree_hash()==gate['dirty_tree_hash']==review['dirty_tree_hash']==audit['dirty_tree_hash'],'dirty drift')
require(len(rows)==82,'candidate count drift')
for p,d in gate['input_artifact_hashes'].items():require((ROOT/p).is_file() and sha(ROOT/p)==d,'Gate input drift '+p)
for p,d in review['verified_input_hashes'].items():require((ROOT/p).is_file() and sha(ROOT/p)==d,'review input drift '+p)
require(len(gate['input_artifact_hashes'])==40 and len(review['verified_input_hashes'])==184,'wrong input count')
for p in ('artifacts/gates/G01.json','artifacts/gates/G01-codex-review.json','tests/unit/test_p02_01_primitives_and_states.py','tests/integration/test_p02_01_primitives_and_states.py','docs/implementation/P02-01.md','docs/implementation/reports/P02-01.md','docs/handoffs/P02-01/dsh.md'):
    require(p not in review['verified_input_hashes'],'wrong current input retained '+p)
require(not any(p.startswith('artifacts/handoffs/P02-01/dsh/logs/') for p in review['verified_input_hashes']),'P02 business log used as current Phase01 proof')
for row in audit['layer_modules']:require(row['path'] in review['verified_input_hashes'] and sha(ROOT/row['path'])==row['sha256'],'real layer source missing/drift '+row['path'])
require(gate['dependency_evidence_hashes']==review['dependency_evidence_hashes']=={'G00':audit['G00_sha256']},'dependency mismatch')
require(sha(ROOT/'artifacts/gates/G00.json')==audit['G00_sha256'],'G00 drift')
for check in runner.check_previous_gates()+runner.check_phase_handoffs():require(check.passed,check.id+': '+check.detail)
require(runner.check_legacy_demo_untouched().passed,'legacy baseline drift')
for a in gate['acceptance_artifacts']:require(sha(ROOT/a['path'])==a['sha256'],'assertion artifact drift '+a['path'])
expected=[g.normalize_argv(g.split_command(c)) for t in runner.phase_tasks() for c in t['commands']]
require(len(expected)==len(gate['commands'])==7,'wrong required command count');counts=[]
for index,(record,required) in enumerate(zip(gate['commands'],expected)):
    problems.extend(runner.recorded_command_problems(index,record))
    actual=[Path(record['argv'][0]).stem.lower(),*record['argv'][1:]];wanted=[Path(required[0]).stem.lower(),*required[1:]]
    require(actual==wanted and Path(record['cwd']).resolve()==ROOT,'required argv/cwd mismatch '+record['check_id'])
    raw=(ROOT/record['log_path']).read_text(encoding='utf-8');parsed=g.parse_pytest_counts(raw)
    require(record['exit_code']==0 and '## exit_code: 0' in raw,'actual command failure '+record['check_id'])
    if g.looks_like_pytest(record['argv']):
        require(parsed==record['test_counts'] and parsed.get('passed',0)>0 and not any(parsed.get(k,0) for k in ('failed','errors','skipped','xfailed','xpassed')),'invalid actual test counts '+record['check_id'])
        counts.append(parsed['passed'])
require(counts==[56,96,74],'wrong task test coverage')
ids={a.id for a in g.PHASE_ASSERTIONS[1]}
require(len(ids)==5 and {a['id'] for a in gate['acceptance_assertions']}==ids and all(a['passed'] for a in gate['acceptance_assertions']),'assertion coverage failure')
require(len(gate['record_checks'])==14 and all(c['passed'] for c in gate['record_checks']),'record check failure')
require(len(gate['commands'])+len(gate['acceptance_assertions'])+len(gate['record_checks'])==26,'wrong total check count')
start=dt.datetime.fromisoformat(gate['started_at']);end=dt.datetime.fromisoformat(gate['finished_at'])
for t in (gate['started_at'],gate['finished_at'],review['reviewed_at']):stamped(t)
require(dt.datetime.fromisoformat(review['reviewed_at'])<=start<end,'review/Gate timeline failure')
logs={};raws={}
for p in sorted((ROOT/'artifacts/gates/G01-logs').glob('*.log')):
    rel=p.relative_to(ROOT).as_posix();logs[rel]=sha(p);raw=p.read_text(encoding='utf-8');raws[p.name]=raw
    stamp=next(line.removeprefix('# started_at: ') for line in raw.splitlines() if line.startswith('# started_at: '))
    require(start<=dt.datetime.fromisoformat(stamp)<=end,'stale official raw log '+rel)
    expected_exit=1 if p.name=='runner-fails-closed-probe.log' else 0
    require(f'## exit_code: {expected_exit}' in raw,'actual native exit failure '+rel)
require(len(logs)==12,'wrong official raw log count')
layer=json.loads(raws['layer-boundaries-json.log'].split('## stdout\n',1)[1].split('## stderr',1)[0])
require(layer['passed'] and layer['violations']==[] and layer['modules_scanned']==10 and layer['modules_per_layer']['domain']==4,'real full-layer/purity failure')
probe=j(ROOT/'artifacts/handoffs/N05-R02-IMPACT/codex/independent-import-probe.json');require(probe['passed'] and len(probe['cases'])==probe['case_count']==6,'independent import probe failure')
for case in probe['cases']:require(case['exit_code']==0 and case['observed']['third_party_roots']==[] and len(case['observed']['six_packages'])==6,'independent isolated case failure')
archive=j(OUT/'archive-manifest.json');require(archive['file_count']==len(archive['files'])==14,'incomplete archive')
for row in archive['files']:require(sha(ROOT/row['archive_path'])==row['sha256'] and (ROOT/row['archive_path']).stat().st_size==row['bytes'],'archived byte drift '+row['archive_path'])
run=j(OUT/'commands/official-g01-command.json');require(run['exit_code']==0 and sha(ROOT/run['log_path'])==run['log_sha256'],'actual official process/raw log failure')
rows2=runner.relevant_manifest_rows()
independent='content-sha256:'+hashlib.sha256('\n'.join(f'{p}\0{d}' for p,d,_ in rows2).encode()).hexdigest()
independent_dirty='content-sha256:'+hashlib.sha256('\n'.join(f'{p}\0{s}\0{d}' for p,d,s in rows2).encode()).hexdigest()
require(independent==revision and independent_dirty==audit['dirty_tree_hash'],'end auto candidate drift')
prior=j(ROOT/'artifacts/handoffs/N05-R02-IMPACT/codex/seal.json')
for row in prior['files']:require(sha(ROOT/row['path'])==row['sha256'],'prior44 sealed evidence drift '+row['path'])
require(sha(ROOT/'artifacts/gates/G01-codex-review.json')==audit['review_sha256'],'reused review bytes changed')
result={'task_id':'N05-R03-ENV','status':'PASSED' if not problems else 'FAILED','official_G01_valid':not problems,'audited_at':now(),
        'code_revision':revision,'dirty_tree_hash':independent_dirty,'candidate_file_count':82,'G01_sha256':sha(ROOT/'artifacts/gates/G01.json'),
        'review_sha256':sha(ROOT/'artifacts/gates/G01-codex-review.json'),'G00_sha256':audit['G00_sha256'],'official_input_count':40,'review_input_count':184,
        'official_task_tests':counts,'official_phase01_test_total':sum(counts),'official_command_count':7,'assertion_count':5,'record_check_count':14,'total_check_count':26,
        'reused_independent_import_processes':6,'retained_layer_sources':audit['layer_modules'],'precheck_inputs':123,'precheck_command_logs':29,
        'official_raw_log_hashes':logs,'official_run_command':run,'old_official_archived_count':14,'archive_file_count':14,
        'post_sign_check_only_exit_code':0,'post_sign_official_files_unchanged':16,'problems':problems,'P02_business_acceptance':False,'G02_signed':False}
dump(OUT/'final-audit.json',result)
print(json.dumps({k:v for k,v in result.items() if k not in ('official_raw_log_hashes','retained_layer_sources')},ensure_ascii=False))
raise SystemExit(1 if problems else 0)
