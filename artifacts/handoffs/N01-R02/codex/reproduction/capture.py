import hashlib
import json
import os
import platform
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

root=Path.cwd().resolve()
assert root==Path(r'D:\Agent\DeepSeekHarness\IntelligentLogisticsDispatchingAgent').resolve()
label=sys.argv[1];argv=sys.argv[2:]
out=root/'artifacts/handoffs/N01-R02/codex';out.mkdir(parents=True,exist_ok=True)
log=out/(label+'.log');descriptor=out/(label+'-command.json')
assert not log.exists() and not descriptor.exists(),'preserve previous command evidence'
started=datetime.now(timezone.utc).isoformat()
environment=dict(os.environ,PYTHONDONTWRITEBYTECODE='1',PYTHONIOENCODING='utf-8')
process=subprocess.run(argv,cwd=root,env=environment,stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
log.write_bytes(process.stdout)
command=dict(argv=argv,cwd=str(root),started_at=started,finished_at=datetime.now(timezone.utc).isoformat(),exit_code=process.returncode,
    log_path=log.relative_to(root).as_posix(),log_hash=hashlib.sha256(process.stdout).hexdigest(),log_bytes=len(process.stdout),
    environment=dict(python=platform.python_version(),os=platform.system()))
descriptor.write_text(json.dumps(command,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps(command,ensure_ascii=False))
print(process.stdout.decode('utf-8',errors='replace')[-1400:])
raise SystemExit(process.returncode)
