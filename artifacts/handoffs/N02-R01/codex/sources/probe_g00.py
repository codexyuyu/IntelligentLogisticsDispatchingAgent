import importlib.util
import json
import sys
from pathlib import Path

sys.dont_write_bytecode=True
root=Path.cwd().resolve()
if root != Path(r'D:\Agent\DeepSeekHarness\IntelligentLogisticsDispatchingAgent').resolve():
    raise SystemExit('wrong working root')
spec=importlib.util.spec_from_file_location('n02_r01_g00_prerequisite',root/'scripts/gates.py')
module=importlib.util.module_from_spec(spec)
sys.modules[spec.name]=module
spec.loader.exec_module(module)
runner=module.GateRunner(root,1,'auto',out_dir=root/'tmp/N02-R01/g00-prerequisite-probe')
checks=runner.check_previous_gates()
payload=dict(command_scope='current official G00 prerequisites only; not G01 acceptance',
    checks=[c.as_dict() for c in checks],schema=runner.gate_record_schema(json.loads((root/'artifacts/gates/G00.json').read_text(encoding='utf-8'))),
    official_records_written=False)
(root/'artifacts/handoffs/N02-R01/codex/g00-prerequisite.json').write_text(json.dumps(payload,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps(payload,ensure_ascii=False,indent=2))
raise SystemExit(0 if all(c.passed for c in checks) else 1)
