"""Capture exact merged subprocess bytes and actual return code for N02-R01."""
import hashlib
import json
import os
import platform
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

root=Path.cwd().resolve()
if root != Path(r'D:\Agent\DeepSeekHarness\IntelligentLogisticsDispatchingAgent').resolve():
    raise SystemExit('wrong working root')
label=sys.argv[1]
argv=sys.argv[2:]
out=root/'artifacts/handoffs/N02-R01/codex'
out.mkdir(parents=True,exist_ok=True)
started=datetime.now(timezone.utc).isoformat()
env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1',PYTHONIOENCODING='utf-8')
proc=subprocess.run(argv,cwd=root,env=env,stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
log=out/(label+'.log')
log.write_bytes(proc.stdout)
record=dict(argv=argv,cwd=str(root),started_at=started,finished_at=datetime.now(timezone.utc).isoformat(),
            exit_code=proc.returncode,log_path=log.relative_to(root).as_posix(),
            log_hash=hashlib.sha256(proc.stdout).hexdigest(),log_bytes=len(proc.stdout),
            environment=dict(python=platform.python_version(),os=platform.system()))
(out/(label+'-command.json')).write_text(json.dumps(record,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps(record,ensure_ascii=False))
print(proc.stdout.decode('utf-8',errors='replace')[-1800:])
raise SystemExit(proc.returncode)
