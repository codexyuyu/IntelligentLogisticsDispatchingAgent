"""Independent N02-R01 F01/F04 shape/discriminator examples, no services."""
import copy
import json
import re
import sys
from datetime import datetime
from pathlib import Path
from uuid import UUID

sys.dont_write_bytecode=True
root=Path.cwd().resolve()
assert root==Path(r'D:\Agent\DeepSeekHarness\IntelligentLogisticsDispatchingAgent').resolve()
spec=json.loads((root/'contracts/changes/N01-R01-contract-decisions.json').read_text(encoding='utf-8'))
rows={r['name']:r for r in spec['types']}
examples=json.loads((root/'artifacts/handoffs/N01-R01/codex/contract-examples-final03.json').read_text(encoding='utf-8'))

def parse(name,value):
    if name.endswith('?'):
        if value is None:
            return
        return parse(name[:-1],value)
    if name.startswith('='):
        assert type(value)is str and value==name[1:]
        return
    if name=='UUID':
        assert isinstance(value,str) and str(UUID(value))==value
        return
    if name=='UTC':
        assert isinstance(value,str) and re.fullmatch(r'\d{4}-\d\d-\d\dT\d\d:\d\d:\d\dZ',value)
        datetime.fromisoformat(value.replace('Z','+00:00'))
        return
    if name=='Sha256':
        assert isinstance(value,str) and re.fullmatch('[0-9a-f]{64}',value)
        return
    if name=='PositiveInt':
        assert type(value)is int and 1<=value<2**63
        return
    row=rows[name]
    if row['kind']=='mapped':
        return parse(row['base'],value)
    if row['kind']=='enum':
        assert type(value)is str and value in row['members'].values()
        return
    if row['kind']=='union':
        assert isinstance(value,dict) and value.get(row['discriminator']) in row['variants']
        return parse(row['variants'][value[row['discriminator']]],value)
    assert row['kind']=='record' and isinstance(value,dict) and set(value)==set(row['fields'])
    for field,typ in row['fields'].items():
        parse(typ,value[field])

def command(value):
    parse('JobRequest',value)
    assert value['kind']==value['payload']['family']==value['payload']['request_ref']['family']

checks=[]
def check(label,fn,expected):
    try:
        fn()
        ok=expected
    except (AssertionError,ValueError,TypeError,KeyError):
        ok=not expected
    checks.append(dict(name=label,passed=ok))
    assert ok,label

for cmd,metadata in examples['job_commands']:
    check('accept '+cmd['kind'],lambda c=cmd:command(c),True)
    check('metadata '+cmd['kind'],lambda m=metadata:parse('RequestMetadata',m),True)
    check('actor '+cmd['kind'],lambda:parse('ActorContext',examples['actor']),True)
    b=copy.deepcopy(cmd)
    b['payload']['request_ref']['family']='metric' if b['kind']!='metric' else 'simulation'
    check('ref mismatch '+cmd['kind'],lambda c=b:command(c),False)
    b=copy.deepcopy(cmd);b['actor']=examples['actor']
    check('body actor '+cmd['kind'],lambda c=b:command(c),False)
    b=copy.deepcopy(cmd);b['payload']['request_ref']['version']=True
    check('bool version '+cmd['kind'],lambda c=b:command(c),False)
    b=copy.deepcopy(cmd);b['payload']['request_ref']['hash']='A'*64
    check('uppercase hash '+cmd['kind'],lambda c=b:command(c),False)
base=copy.deepcopy(examples['job_commands'][0][0])
for mode in ['transport','warehouse','joint']:
    b=copy.deepcopy(base);b['payload']['mode']=mode
    check('mode '+mode,lambda c=b:command(c),True)
for label,path,value in [('unknown kind',['kind'],'routing'),('old schema',['schema_version'],'1.0.0'),('unknown mode',['payload','mode'],'routing')]:
    b=copy.deepcopy(base);target=b
    for key in path[:-1]:
        target=target[key]
    target[path[-1]]=value
    check(label,lambda c=b:command(c),False)
for cmd,_ in examples['job_commands'][1:]:
    b=copy.deepcopy(cmd);b['payload']['mode']='transport'
    check('nonoptimization mode '+cmd['kind'],lambda c=b:command(c),False)
summary=dict(independent_job_shape_checks=len(checks),passed=sum(r['passed'] for r in checks),results=checks,
    limitations='Design data shape/discriminants only; no real capability parser, JobService, worker, HTTP or DB executed.')
(root/'artifacts/handoffs/N02-R01/codex/job-shape-probe.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps(summary,ensure_ascii=False))
