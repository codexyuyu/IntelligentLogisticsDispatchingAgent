from __future__ import annotations
import datetime as dt
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

ROOT=Path(r'D:\Agent\DeepSeekHarness\IntelligentLogisticsDispatchingAgent')
TEMP=Path(__file__).resolve().parent
assert TEMP==Path(r'C:\Users\30382\AppData\Local\Temp\IntelligentLogisticsDispatchingAgent-n05-r02-impact')
OUT=ROOT/'artifacts/handoffs/N05-R02-IMPACT/codex'
CACHE=TEMP/'uv-cache'
ENV=dict(os.environ)
ENV.update(PYTHONIOENCODING='utf-8',PYTHONNOUSERSITE='1',PYTHONDONTWRITEBYTECODE='1',UV_CACHE_DIR=str(CACHE),npm_config_cache=str(TEMP/'npm-cache'))
for key in ('npm_config_offline','npm_config_cache_mode','npm_config_allow_scripts','NPM_CONFIG_OFFLINE'):ENV.pop(key,None)
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def j(p):return json.loads(p.read_text(encoding='utf-8'))
def dump(p,v):
    p.parent.mkdir(parents=True,exist_ok=True)
    p.write_text(json.dumps(v,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
def now():return dt.datetime.now(dt.timezone.utc).isoformat()
def gate_module():
    spec=importlib.util.spec_from_file_location('n05_r02_gates',ROOT/'scripts/gates.py')
    g=importlib.util.module_from_spec(spec);sys.modules[spec.name]=g;spec.loader.exec_module(g);return g
def capture(check_id,argv,cwd=ROOT,timeout=1800):
    args=list(argv);args[0]=shutil.which(args[0]) or args[0];env=dict(ENV)
    pytestroot=TEMP/('pytest-'+check_id);pytestroot.mkdir(parents=True,exist_ok=True);env['PYTEST_DEBUG_TEMPROOT']=str(pytestroot)
    raw=TEMP/(check_id+'.log');assert not raw.exists(),'refuse overwrite: '+str(raw)
    started=now()
    with raw.open('w',encoding='utf-8',newline='\n') as h:
        h.write(f'# argv: {json.dumps(args,ensure_ascii=False)}\n# cwd: {cwd}\n# started_at: {started}\n# system_temp: {TEMP}\n\n');h.flush()
        result=subprocess.run(args,cwd=cwd,env=env,capture_output=True,text=True,encoding='utf-8',errors='replace',timeout=timeout)
        h.write('## stdout\n'+result.stdout+'\n## stderr\n'+result.stderr+f'\n## exit_code: {result.returncode}\n')
    finished=now();dest=OUT/'commands'/raw.name;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(raw,dest)
    record={'check_id':check_id,'argv':args,'cwd':str(cwd),'exit_code':result.returncode,'started_at':started,'finished_at':finished,'log_path':dest.relative_to(ROOT).as_posix(),'log_sha256':sha(dest)}
    dump(dest.with_name(check_id+'-command.json'),record)
    print(json.dumps(record,ensure_ascii=False));print(result.stdout[-2500:]);print(result.stderr[-1000:]);return result
if __name__=='__main__':raise SystemExit(capture(sys.argv[1],sys.argv[2:]).returncode)
