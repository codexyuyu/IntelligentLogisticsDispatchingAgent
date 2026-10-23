"""Capture a real fresh design run and its raw output without replacing earlier runs."""
import hashlib
import json
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path.cwd().resolve()
if ROOT != Path(r'D:\Agent\DeepSeekHarness\IntelligentLogisticsDispatchingAgent'):
    raise SystemExit('Wrong workspace root; no writes authorized')
label = sys.argv[1] if len(sys.argv) == 2 else ''
if not re.fullmatch(r'[a-z0-9-]+', label):
    raise SystemExit('One fresh lowercase run label required')
OUT = ROOT / 'artifacts/handoffs/N01-R02/codex/examples'
OUT.mkdir(parents=True, exist_ok=True)
log_path = OUT / ('contract-check-' + label + '.log')
record_path = OUT / ('contract-check-' + label + '-command.json')
result_path = OUT / ('contract-validation-' + label + '.json')
example_path = OUT / ('contract-examples-' + label + '.json')
if any(p.exists() for p in (log_path, record_path, result_path, example_path)):
    raise SystemExit('Fresh label required; do not overwrite previous run evidence')
argv = [sys.executable, 'tmp/N01-R02/examples/verify_design_examples.py', label]
inputs = ['contracts/changes/N01-R01-contract-decisions.json', 'docs/plan/TASK_MANIFEST.json', 'tmp/N01-R02/scope-before.json', 'tmp/N01-R01/verify_contracts.py', 'tmp/N01-R02/examples/verify_design_examples.py', 'tmp/N01-R02/examples/event_reference_examples.py', 'tools/ai_coding_plan/validate_plan.py', 'tools/ai_coding_plan/render_plan.py']
hashes = {p: hashlib.sha256((ROOT / p).read_bytes()).hexdigest() for p in inputs}
started = datetime.now(timezone.utc).isoformat()
process = subprocess.run(argv, cwd=ROOT, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
finished = datetime.now(timezone.utc).isoformat()
log_path.write_bytes(process.stdout)
record = dict(argv=argv, cwd=str(ROOT), started_at=started, finished_at=finished, exit_code=process.returncode, log_path=log_path.relative_to(ROOT).as_posix(), log_hash=hashlib.sha256(process.stdout).hexdigest(), verified_input_hashes=hashes, result_path=result_path.relative_to(ROOT).as_posix(), examples_path=example_path.relative_to(ROOT).as_posix(), limitation='Executable design checks only; no Gate signature or business engine acceptance.')
record_path.write_text(json.dumps(record, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
if result_path.is_file():
    result = json.loads(result_path.read_text(encoding='utf-8'))
    print(json.dumps({k: result[k] for k in ['status', 'checks', 'passed', 'failed', 'inherited_check_count', 'event_reference_check_count', 'event_case_counts']}, ensure_ascii=False))
else:
    print(process.stdout.decode('utf-8', errors='replace')[-4000:])
print(json.dumps(record, ensure_ascii=False))
sys.exit(process.returncode)
