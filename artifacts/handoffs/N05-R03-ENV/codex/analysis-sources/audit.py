from __future__ import annotations
import hashlib
import importlib.util
from pathlib import Path
import shutil
import subprocess
import sys
from common import ROOT,TEMP,OUT,ENV,sha,j,dump,now,gate_module

PREVIOUS=ROOT/'artifacts/handoffs/N05-R02-IMPACT/codex'
assert sha(ROOT/'artifacts/dispatch/2026-10-04/orchestration/codex/N05-R03-ENV.md')=='aff4cfab45d0cf7c656ee4063419844a9389871eefda8819b35551ba2d5bcc85'
seal=j(PREVIOUS/'seal.json');assert sha(PREVIOUS/'seal.json')=='abac462cd99f1979ae4a10b32b0b7e13306d8aa7b70e51682880ab809c546ac8'
assert seal['status']=='BLOCKED' and seal['file_count']==len(seal['files'])==44
for row in seal['files']:assert sha(ROOT/row['path'])==row['sha256'] and (ROOT/row['path']).stat().st_size==row['bytes'],row['path']
g=gate_module();runner=g.GateRunner(ROOT,1,'auto');rows=runner.relevant_manifest_rows()
revision='content-sha256:'+hashlib.sha256('\n'.join(f'{p}\0{d}' for p,d,_ in rows).encode()).hexdigest()
dirty='content-sha256:'+hashlib.sha256('\n'.join(f'{p}\0{s}\0{d}' for p,d,s in rows).encode()).hexdigest()
assert revision==runner.compute_revision()=='content-sha256:477a883d2a29deb5cb60f8269c8712693d9e7aedeb3a620ba4953a630289158c'
assert dirty==runner.dirty_tree_hash()=='content-sha256:eaea942624f00e5da16e89a3e744d3a2c1c659fcf9eeda0a23787116681d636f'
assert len(rows)==82 and not (ROOT/'.git').exists();runner.revision=revision
oldgate=j(ROOT/'artifacts/gates/G01.json');review=j(ROOT/'artifacts/gates/G01-codex-review.json');old=j(PREVIOUS/'initial-audit.json');priorfinal=j(PREVIOUS/'final-audit.json')
assert sha(ROOT/'artifacts/gates/G01.json')=='9f30bb45307721ecdb6d85259bac18230002d91d6dc5eabc61f55fd41337e35c'
assert sha(ROOT/'artifacts/gates/G01-codex-review.json')=='e64827a62caa4c497304c66d85df154ac6047e571b3c5947b97a2d7c93925efc'
assert oldgate['status']=='failed' and oldgate['failed_checks']==['P01-01-cmd1']
assert oldgate['commands'][0]['test_counts']=={'passed':55,'failed':1} and oldgate['commands'][2]['exit_code']==0
assert review['status']=='approved' and review['code_revision']==revision and review['dirty_tree_hash']==dirty
assert len(oldgate['input_artifact_hashes'])==40 and len(review['verified_input_hashes'])==184
for p,d in {**oldgate['input_artifact_hashes'],**review['verified_input_hashes'],**priorfinal['official_raw_log_hashes']}.items():assert sha(ROOT/p)==d,p
assert all(c.passed for c in runner.check_previous_gates()+runner.check_phase_handoffs())
g00=j(ROOT/'artifacts/gates/G00.json');assert not runner.previous_gate_record_problems('G00',g00)
assert sha(ROOT/'artifacts/gates/G00.json')==old['G00_sha256']
prechecks=[]
for task in runner.phase_tasks():
    p=f"artifacts/handoffs/{task['id']}/zcode/precheck.json";pre=j(ROOT/p)
    assert not runner.recorded_input_problems(task['id'],pre['verified_input_hashes'],require=runner.required_precheck_inputs(task))
    for c in pre['commands']:assert sha(ROOT/c['log_path'])==c['log_sha256']
    prechecks.append({'task':task['id'],'sha256':sha(ROOT/p),'input_count':len(pre['verified_input_hashes']),'command_count':len(pre['commands'])})
assert sum(p['input_count'] for p in prechecks)==123 and sum(p['command_count'] for p in prechecks)==29
probe=j(PREVIOUS/'independent-import-probe.json');assert probe['passed'] and probe['case_count']==len(probe['cases'])==6
assert all(c['exit_code']==0 and c['observed']['third_party_roots']==[] for c in probe['cases'])
assert revision==probe['current_code_revision']
for row in old['layer_modules']:assert sha(ROOT/row['path'])==row['sha256'],row['path']
spec=importlib.util.spec_from_file_location('n05_r03_architecture',ROOT/'scripts/check_architecture.py');a=importlib.util.module_from_spec(spec);sys.modules[spec.name]=a;spec.loader.exec_module(a)
assert sorted(p.relative_to(ROOT).as_posix() for _,p in a.iter_modules(ROOT))==sorted(row['path'] for row in old['layer_modules'])
oldtemp=Path(r'C:\Users\30382\AppData\Local\Temp\IntelligentLogisticsDispatchingAgent-n05-r02-impact')
for name in ('uv-cache','npm-cache'):
    dest=TEMP/name;assert not dest.exists(),'new cache destination must be unused: '+str(dest)
    shutil.copytree(oldtemp/name,dest)
start=now();argv=['node',str(TEMP/'cache-verify.cjs')]
result=subprocess.run(argv,cwd=ROOT,env=ENV,text=True,capture_output=True,encoding='utf-8',timeout=60)
raw=TEMP/'cache-verify.log';raw.write_text('# argv: '+str(argv)+'\n# started_at: '+start+'\n## stdout\n'+result.stdout+'\n## stderr\n'+result.stderr+f'\n## exit_code: {result.returncode}\n',encoding='utf-8')
assert result.returncode==0,result.stderr
import json
cache=json.loads(result.stdout);assert cache['passed'] and cache['network_requests']==cache['cache_writes']==0
for case in cache['cases']:assert [p['bytes'] for p in case['packages']]==[8749,899597,3123044]
dest=OUT/'environment'/raw.name;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(raw,dest)
dump(OUT/'environment/cache-verify.json',{'argv':argv,'cwd':str(ROOT),'exit_code':0,'started_at':start,'finished_at':now(),'log_path':dest.relative_to(ROOT).as_posix(),'log_sha256':sha(dest),'result':cache})
archive=OUT/'archive'/now().replace(':','').replace('+','_');assert not archive.exists()
oldpaths=[ROOT/'artifacts/gates/G01.json',ROOT/'artifacts/gates/G01-codex-review.json',*sorted((ROOT/'artifacts/gates/G01-logs').glob('*.log'))];assert len(oldpaths)==14
archived=[]
for p in oldpaths:
    rel=p.relative_to(ROOT).as_posix();dst=archive/rel;dst.parent.mkdir(parents=True,exist_ok=True);digest=sha(p);shutil.copyfile(p,dst)
    assert sha(p)==sha(dst)==digest
    archived.append({'original_path':rel,'archive_path':dst.relative_to(ROOT).as_posix(),'bytes':p.stat().st_size,'sha256':digest})
dump(OUT/'archive-manifest.json',{'created_at':now(),'file_count':14,'byte_identical':True,'files':archived})
for name in ('common.py','audit.py','cache-verify.cjs'):
    dst=OUT/'analysis-sources'/name;dst.parent.mkdir(exist_ok=True);shutil.copyfile(TEMP/name,dst);assert sha(TEMP/name)==sha(dst)
initial={'task_id':'N05-R03-ENV','passed':True,'actual_utc':now(),'code_revision':revision,'dirty_tree_hash':dirty,'candidate_file_count':82,
         'candidate_rows':[{'path':p,'sha256':d,'bytes':s} for p,d,s in rows],'G00_sha256':old['G00_sha256'],'review_sha256':sha(ROOT/'artifacts/gates/G01-codex-review.json'),
         'review_reused_unchanged':True,'reused_independent_import_probe':{'path':(PREVIOUS/'independent-import-probe.json').relative_to(ROOT).as_posix(),'sha256':sha(PREVIOUS/'independent-import-probe.json'),'case_count':6,'rerun':False},
         'previous_seal_sha256':sha(PREVIOUS/'seal.json'),'previous_sealed_count':44,'prechecks':prechecks,'layer_modules':old['layer_modules'],
         'cache_verification':cache,'old_failed_G01_sha256':sha(ROOT/'artifacts/gates/G01.json'),'archive_count':14,'old_failure_preserved':True}
dump(OUT/'initial-audit.json',initial)
print({'passed':True,'revision':revision,'files':82,'review_inputs':184,'review_reused':True,'precheck_inputs':123,'precheck_command_logs':29,'three_tarballs_present':True,'cache_verify_network_requests':0,'cache_verify_writes':0,'old_seal_files_unchanged':44,'archived_old_official_files':14})
