from __future__ import annotations
import itertools
import json
import subprocess
from common import ROOT,TEMP,OUT,ENV,sha,j,dump,now

audit=j(OUT/'initial-audit.json');assert audit['passed']
cwd=TEMP/'outside-cwd';cwd.mkdir(exist_ok=True)
cases=[];python=ROOT/'.venv/Scripts/python.exe'
for order in itertools.permutations(('errors','primitives','states')):
    code="""import sys,json,pathlib,importlib
before=set(sys.modules)
ORDER=ORDER_VALUE
for name in ORDER:exec('from logistics_domain import '+name)
import logistics_domain as package
exports={}
for name in ('errors','primitives','states'):
    obj=getattr(package,name)
    assert obj is importlib.import_module('logistics_domain.'+name) and name in package.__all__
    exports[name]=str(pathlib.Path(obj.__file__).resolve())
LOUD={}
for name in ('entities','ids','units','ports'):
    try:getattr(package,name)
    except NotImplementedError as e:
        assert name in str(e) and 'not implemented yet' in str(e);LOUD[name]='NotImplementedError'
    else:raise AssertionError('undelivered entry succeeded: '+name)
try:getattr(package,'n05_r02_unknown')
except AttributeError:unknown='AttributeError'
else:raise AssertionError('unknown entry succeeded')
six={}
for name in ('logistics_domain','logistics_contracts','logistics_optimization','logistics_simulation','logistics_agents','logistics_evaluation'):
    obj=importlib.import_module(name);path=pathlib.Path(obj.__file__).resolve()
    assert path.is_relative_to(pathlib.Path(ROOT_VALUE)/'packages') and path.name=='__init__.py'
    six[name]=str(path)
third=sorted({n.split('.',1)[0] for n in set(sys.modules)-before}-set(sys.stdlib_module_names)-set(six))
assert not third,third
assert sys.flags.isolated==1 and sys.dont_write_bytecode
print(json.dumps({'order':ORDER,'exports':exports,'loud':LOUD,'unknown':unknown,'six_packages':six,'third_party_roots':third,'isolated':sys.flags.isolated,'cwd':str(pathlib.Path.cwd())}))
""".replace('ORDER_VALUE',repr(list(order))).replace('ROOT_VALUE',repr(str(ROOT)))
    argv=[str(python),'-I','-B','-c',code];start=now()
    c=subprocess.run(argv,cwd=cwd,env=ENV,text=True,capture_output=True,encoding='utf-8',timeout=60)
    print(json.dumps({'argv':argv,'cwd':str(cwd),'exit_code':c.returncode,'started_at':start,'finished_at':now(),'stdout':c.stdout,'stderr':c.stderr},ensure_ascii=False))
    assert c.returncode==0,c.stderr
    observed=json.loads(c.stdout);assert observed['loud']==dict.fromkeys(('entities','ids','units','ports'),'NotImplementedError')
    cases.append({'argv':argv,'cwd':str(cwd),'exit_code':0,'started_at':start,'finished_at':now(),'observed':observed})
for row in audit['layer_modules']:assert sha(ROOT/row['path'])==row['sha256'],row['path']
result={'task_id':'N05-R02-IMPACT','passed':True,'actual_utc':now(),'case_count':6,'cases':cases,'current_code_revision':audit['code_revision'],
        'scope':'six package import provenance, all domain export permutations, domain purity, pending/unknown entry failures only; no Reservation/P02 business acceptance',
        'clean_install_reused_not_rerun':'unchanged package metadata and locked artifacts, original N05 clean installation proof; this process uses the existing installed workspace environment'}
dump(OUT/'independent-import-probe.json',result)
print(json.dumps({'passed':True,'fresh_processes':6,'six_packages_each':6,'third_party_roots':[],'pending_failures_each':4,'unknown_error':'AttributeError','business_acceptance':False}))
