import hashlib
import json
from pathlib import Path

root=Path.cwd().resolve()
if root != Path(r'D:\Agent\DeepSeekHarness\IntelligentLogisticsDispatchingAgent').resolve():
    raise SystemExit('wrong working root')
source=root/'tmp/N01-R01/verify_contracts.py'
text=source.read_text(encoding='utf-8')
replacements=[("OUT=ROOT/'artifacts/handoffs/N01-R01/codex'", "OUT=ROOT/'artifacts/handoffs/N02-R01/codex'"),
              ("dir=ROOT/'tmp/N01-R01'", "dir=ROOT/'tmp/N02-R01'")]
for before,after in replacements:
    if text.count(before)!=1:
        raise SystemExit('unexpected replay source')
    text=text.replace(before,after)
target=root/'tmp/N02-R01/replay_contract_examples.py'
target.write_text(text,encoding='utf-8')
out=root/'artifacts/handoffs/N02-R01/codex/replay-source-binding.json'
out.write_text(json.dumps(dict(source=source.relative_to(root).as_posix(),source_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),
               adapted_source=target.relative_to(root).as_posix(),adapted_sha256=hashlib.sha256(target.read_bytes()).hexdigest(),
               only_changes=replacements,classification='replayed implementer design examples; independent semantic audit separate'),indent=2)+'\n',encoding='utf-8')
print('Prepared isolated output replay; only output/scratch destinations changed.')
