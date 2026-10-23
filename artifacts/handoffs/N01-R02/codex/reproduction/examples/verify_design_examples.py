"""Executable design examples, not domain/HTTP/DB acceptance or fake services."""
import copy, hashlib, importlib.util, json, re, subprocess, sys, tempfile
from datetime import datetime, timezone, timedelta
from pathlib import Path
from uuid import UUID
sys.dont_write_bytecode=True
ROOT=Path.cwd().resolve()
if ROOT != Path(r'D:\Agent\DeepSeekHarness\IntelligentLogisticsDispatchingAgent'):
    raise SystemExit('Wrong workspace root; no writes authorized')
OUT=ROOT/'artifacts/handoffs/N01-R02/codex/examples'
OUT.mkdir(parents=True,exist_ok=True)
suffix='-'+sys.argv[1] if len(sys.argv)>1 else ''
sys.path.insert(0,str(ROOT/'tools/ai_coding_plan'))
import validate_plan, render_plan
spec=json.loads((ROOT/'contracts/changes/N01-R01-contract-decisions.json').read_text(encoding='utf-8'))
types={r['name']:r for r in spec['types']}
manifest=json.loads((ROOT/'docs/plan/TASK_MANIFEST.json').read_text(encoding='utf-8'))
scope=json.loads((ROOT/'tmp/N01-R02/scope-before.json').read_text(encoding='utf-8'))
results=[]
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def check(name,fn,expected=True):
    try: value=fn(); ok=bool(value)==expected; detail=str(value)
    except (ValueError,KeyError,TypeError,AssertionError) as exc:ok=not expected;detail=str(exc)
    row=dict(name=name,passed=ok,detail=detail)
    results.append(row);print(json.dumps(row,ensure_ascii=False))
def canonical(value):return json.dumps(value,ensure_ascii=False,sort_keys=True,separators=(',',':'),allow_nan=False).encode('utf-8')
def digest(value):return hashlib.sha256(canonical(value)).hexdigest()
def strict_json(raw):
    def pairs(rows):
        out={}
        for key,val in rows:
            if key in out:raise ValueError('duplicate JSON key '+key)
            out[key]=val
        return out
    return json.loads(raw,object_pairs_hook=pairs,parse_constant=lambda s:(_ for _ in ()).throw(ValueError(s)))
def utc(value):
    if not isinstance(value,str) or not re.fullmatch(r'\d{4}-\d\d-\d\dT\d\d:\d\d:\d\dZ',value):raise ValueError('UTC seconds Z required')
    return datetime.fromisoformat(value.replace('Z','+00:00'))
def exact(value,fields):
    if not isinstance(value,dict) or set(value)!=set(fields):raise ValueError('missing or extra fields: '+str(set(value) ^ set(fields)))
def parse(name,value):
    if name.endswith('?'):
        if value is None:return
        return parse(name[:-1],value)
    if name.endswith('[]'):
        if not isinstance(value,list):raise ValueError('typed tuple JSON array required')
        for item in value:parse(name[:-2],item)
        return
    if name.startswith('='):
        literal=name[1:]
        if value!=literal and not (literal.isdigit() and type(value)is int and value==int(literal)):raise ValueError('literal mismatch')
        return
    if name=='UUID':
        if not isinstance(value,str) or str(UUID(value))!=value:raise ValueError('canonical UUID required')
        return
    if name=='UTC':utc(value);return
    if name in ['int','PositiveInt','NonNegativeInt','Seed','Horizon']:
        if type(value)is not int or not -2**63<=value<2**63:raise ValueError('int64 required')
        if name in ['PositiveInt','Horizon'] and value<1:raise ValueError('positive integer required')
        if name in ['NonNegativeInt','Seed'] and value<0:raise ValueError('nonnegative integer required')
        if name=='Horizon' and value>604800:raise ValueError('horizon limit')
        return
    if name=='Sha256':
        if not isinstance(value,str) or not re.fullmatch('[0-9a-f]{64}',value):raise ValueError('64 lowercase hex required')
        return
    if name=='VersionText':
        if not isinstance(value,str) or not re.fullmatch(r'(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)',value):raise ValueError('exact semantic version required')
        return
    if name in ['str','SafeText']:
        if not isinstance(value,str) or (name=='SafeText' and not 1<=len(value)<=256):raise ValueError('bounded safe string required')
        return
    if name=='bool':
        if type(value)is not bool:raise ValueError('bool required')
        return
    row=types[name]
    if row['kind']=='enum':
        if value not in row['members'].values():raise ValueError('unknown enum '+name)
    elif row['kind']=='mapped':
        extra=row.get('extra_fields',{})
        if extra:
            for field,expression in extra.items():parse(expression,value[field])
            parse(row['base'],{k:v for k,v in value.items() if k not in extra})
        else:parse(row['base'],value)
    elif row['kind']=='union':
        if not isinstance(value,dict) or value.get(row['discriminator']) not in row['variants']:raise ValueError('unknown discriminant')
        parse(row['variants'][value[row['discriminator']]],value)
    elif row['kind']=='record':
        exact(value,row['fields'])
        for key,kind in row['fields'].items():parse(kind,value[key])
    else:parse_inherited(name,value)
def parse_inherited(name,value):
    # Existing source fields are inspected independently; this checks structural examples,
    # not a claim that future Python models, state machines or business validation run.
    if name=='PlanningScope':
        exact(value,['order_ids','warehouse_ids','vehicle_ids','epoch_utc','horizon_s'])
        for k in ['order_ids','warehouse_ids','vehicle_ids']:parse('UUID[]',value[k])
        parse('UTC',value['epoch_utc']);parse('Horizon',value['horizon_s']);return
    if name=='ResourceRevision':
        exact(value,['entity_ref','row_version']);parse('EntityRef',value['entity_ref']);parse('NonNegativeInt',value['row_version']);return
    if name=='EntityRef':
        exact(value,['kind','id','revision']);parse('UUID',value['id']);parse('NonNegativeInt?',value['revision']);
        parse('EntityKind',value['kind']) # Sole source: this round's normative enum.
        return
    if name=='TimeWindow':
        exact(value,['earliest_s','latest_s']);parse('NonNegativeInt',value['earliest_s']);parse('NonNegativeInt',value['latest_s'])
        if value['earliest_s']>value['latest_s']:raise ValueError('reversed window')
        return
    if name=='ErrorCode':
        if value not in {'INVALID_INPUT','INVALID_TRANSITION','DEPENDENCY_CYCLE','UNAUTHENTICATED','FORBIDDEN','TOOL_FORBIDDEN','NOT_FOUND','STALE_SNAPSHOT','RESOURCE_CONFLICT','IDEMPOTENCY_CONFLICT','CONFIRMATION_EXPIRED','REQUEST_TOO_LARGE','RATE_LIMITED','PROVIDER_UNAVAILABLE','DEPENDENCY_UNAVAILABLE','INTERNAL_ERROR','RESULT_NOT_READY','UNVERIFIED_SOLVER_RESULT'}:raise ValueError('unregistered ErrorCode')
        return
    if name=='TravelMatrix':
        exact(value,['id','version','node_ids','distance_m','travel_s','source','observed_at','hash'])
        parse('UUID',value['id']);parse('PositiveInt',value['version']);parse('UUID[]',value['node_ids']);parse('UTC',value['observed_at']);parse('Sha256',value['hash'])
        n=len(value['node_ids'])
        if len(set(value['node_ids']))!=n:raise ValueError('duplicate matrix nodes')
        for key in ['distance_m','travel_s']:
            if len(value[key])!=n or any(len(row)!=n for row in value[key]):raise ValueError('matrix shape')
            for row in value[key]:
                for cell in row:parse('NonNegativeInt?',cell)
        for i in range(n):
            for j in range(n):
                if (value['distance_m'][i][j] is None)!=(value['travel_s'][i][j] is None):raise ValueError('unreachable pair mismatch')
        return
    body=(ROOT/'docs/architecture/DOMAIN_CATALOG.md').read_text(encoding='utf-8')
    line=next((r for r in body.splitlines() if r.startswith('| '+name+' /')),None)
    if line:
        fieldcol=line.split('|')[3].strip()
        fields={m.group(1):m.group(2) for m in re.finditer(r'(?:^|;\s*)([a-z_][a-z0-9_]*):([^;]+)',fieldcol)}
        common=['id','status','created_at','updated_at','row_version','schema_version','created_by']
        exact(value,common+list(fields))
        parse('UUID',value['id']);parse('UUID',value['created_by']);parse('UTC',value['created_at']);parse('UTC',value['updated_at']);parse('NonNegativeInt',value['row_version'])
        if value['schema_version']!='2.0.0':raise ValueError('old entity schema')
        for field,expression in fields.items():
            item=value[field]
            if expression.startswith('int'):parse('int?' if '?' in expression else 'int',item)
            elif expression.startswith('UUID'):parse('UUID?' if '?' in expression else 'UUID',item)
            elif expression.startswith('ResourceCalendar'):parse('ResourceCalendar',item);calendar(item)
            elif expression.startswith('TimeWindow'):parse('TimeWindow',item)
            elif expression.startswith('tuple[UUID]'):parse('UUID[]',item)
        for k in ['quantity_capacity','capacity_weight_g','capacity_volume_cm3']:
            if k in value and value[k]<=0:raise ValueError('nonpositive resource capacity')
        if 'calendar' in value:
            cap=value['quantity_capacity'] if name=='Equipment' else 1
            if any(r['available_units']>cap for r in value['calendar']['intervals']):raise ValueError('calendar units exceed resource capacity')
        return
    raise ValueError('example validator has no inherited adapter for '+name)
def calendar(value):
    parse('ResourceCalendar',value)
    end=0
    for interval in value['intervals']:
        if not 0<=interval['start_s']<interval['end_s']<=604800 or interval['start_s']<end:raise ValueError('overlap/order/range')
        end=interval['end_s']
    return True
def project_calendar(value,epoch,horizon):
    calendar(value);offset=int((utc(value['epoch_utc'])-utc(epoch)).total_seconds())
    rows=[]
    for r in value['intervals']:
        start=max(0,r['start_s']+offset);end=min(horizon,r['end_s']+offset)
        if start<end:rows.append(dict(start_s=start,end_s=end,available_units=r['available_units']))
    return dict(epoch_utc=epoch,intervals=rows,version=value['version'])
def calendar_binding(value,epoch,horizon):
    parse('ResourceCalendarBinding',value)
    if value['source_hash']!=digest(value['source_calendar']):raise ValueError('calendar source hash mismatch')
    if value['calendar']!=project_calendar(value['source_calendar'],epoch,horizon):raise ValueError('calendar projection mismatch')
    return True
def job_command(value):
    parse('JobRequest',value)
    if value['kind']!=value['payload']['family'] or value['kind']!=value['payload']['request_ref']['family']:raise ValueError('family mismatch')
    return True
def resolve(value,metadata,raw,actor,current_version=1,enabled=True):
    job_command(value);parse('RequestMetadata',metadata);parse('ActorContext',actor)
    ref=value['payload']['request_ref']
    if ref['request_id']!=metadata['ref']['request_id']:raise ValueError('404 NOT_FOUND')
    if actor['scope_id']!=metadata['scope_id'] or actor['actor_id']!=metadata['owner_actor_id'] or actor['role']!='operator':raise ValueError('403 FORBIDDEN')
    if ref['version']!=current_version:raise ValueError('409 STALE_SNAPSHOT')
    if ref!=metadata['ref'] or hashlib.sha256(raw).hexdigest()!=ref['hash']:raise ValueError('422 INVALID_INPUT hash/ref')
    if value['payload'].get('mode')!=metadata['optimization_mode']:raise ValueError('422 INVALID_INPUT mode')
    strict_json(raw)
    if not enabled:raise ValueError('501 capability unavailable; no Job created')
    return True
def scenario_hash(value):
    return digest(dict(schema_version=value['schema_version'],scenario_id=value['ref']['scenario_id'],dataset_version=value['ref']['dataset_version'],spec=value['spec'],input=value['input'],source=value['source']))
def scenario(value):
    parse('ScenarioBundle',value)
    ref,sp,input_=value['ref'],value['spec'],value['input'];snap=input_['snapshot']
    if (ref['scenario_id'],ref['dataset_version'],ref['schema_version'])!=(sp['id'],sp['version'],sp['schema_version']):raise ValueError('scenario identity mismatch')
    if (snap['scope']['epoch_utc'],snap['scope']['horizon_s'])!=(sp['epoch_utc'],sp['horizon_s']):raise ValueError('epoch/horizon mismatch')
    if snap['hash']!=digest({k:v for k,v in snap.items() if k!='hash'}):raise ValueError('snapshot content hash mismatch')
    counts={k:len(snap[k]) for k in ['orders','cargo','vehicles','drivers','matrices']}
    counts.update({k:len(snap['resources'][k]) for k in ['warehouses','zones','docks','workers','equipment']})
    counts.update(storage_locations=len(snap['resources']['locations']),inventory_entries=len(snap['inventory']),transport_tasks=len(input_['transport_tasks']),warehouse_tasks=len(input_['warehouse_tasks']))
    if counts!=sp['size']:raise ValueError('size mismatch')
    collections=[snap[k] for k in ['orders','cargo','vehicles','drivers','matrices']]+[snap['resources'][k] for k in ['warehouses','zones','locations','docks','workers','equipment']]
    ids=[x['id'] for rows in collections for x in rows]
    if len(set(ids))!=len(ids):raise ValueError('duplicate entity id')
    if len(set(x['event_id'] for x in sp['event_specs']))!=len(sp['event_specs']):raise ValueError('duplicate event id')
    for event in sp['event_specs']:
        if event['payload']['effective_at_s']>sp['horizon_s']:raise ValueError('event outside horizon')
    if ref['content_hash']!=scenario_hash(value):raise ValueError('scenario content hash mismatch')
    return True
def lifecycle(value):
    parse('Job',value)
    if value['kind']!=value['command']['kind'] or value['deadline_utc']!=value['command']['deadline_utc']:raise ValueError('command binding')
    if value['request_hash']!=digest(value['command']):raise ValueError('command content hash')
    if value['attempt']>value['max_attempts']:raise ValueError('attempt limit')
    if value['status']=='running':
        if value['lease_owner'] is None or value['lease_expires_at'] is None:raise ValueError('running needs lease')
    elif value['lease_owner'] is not None or value['lease_expires_at'] is not None:raise ValueError('nonrunning lease not released')
    if value['status'] in {'completed','failed','cancelled'}:
        if value['finished_at'] is None or (value['started_at'] is not None and utc(value['finished_at'])<utc(value['started_at'])):raise ValueError('invalid terminal time')
    if value['status']=='completed':
        if value['result_ref'] is None or value['failure'] is not None or value['result_ref']['family']!=value['kind']:raise ValueError('typed completed result required')
    if value['status']=='failed' and (value['failure'] is None or value['result_ref'] is not None):raise ValueError('failed needs error not result')
    if value['status']=='cancelled' and value['result_ref'] is not None:raise ValueError('cancelled must not fake result')
    return True
def lease_accept(token,current,now):
    parse('LeaseToken',token);parse('LeaseToken',current)
    if token!=current or utc(token['expires_at'])<=utc(now):raise ValueError('lease_lost: no current Job write')
    return True
def import_receipt(value):
    parse('ImportReceipt',value)
    if len(set(r['entity_kind'] for r in value['counts']))!=len(value['counts']):raise ValueError('duplicate count kind')
    if value['inserted']!=sum(r['inserted'] for r in value['counts']) or value['unchanged']!=sum(r['unchanged'] for r in value['counts']):raise ValueError('count sum mismatch')
    if value['status']=='no_change' and (value['inserted']!=0 or value['error'] is not None):raise ValueError('false no_change')
    return True
def patch(value,path,new):
    value=copy.deepcopy(value);part=value
    for key in path[:-1]:part=part[key]
    part[path[-1]]=new
    return value
u=lambda n:str(UUID(int=n))
epoch='2026-09-12T00:00:00Z'
cal=dict(epoch_utc=epoch,intervals=[dict(start_s=0,end_s=10,available_units=1),dict(start_s=10,end_s=20,available_units=0)],version=0)
check('F03 abutting intervals and zero capacity accepted',lambda:calendar(cal))
for label,path,new in [('overlap',['intervals',0,'end_s'],11),('float',['intervals',0,'start_s'],0.5),('bool',['version'],False),('negative version',['version'],-1),('fractional epoch',['epoch_utc'],'2026-09-12T00:00:00.1Z')]:check('F03 rejects '+label,lambda p=path,v=new:calendar(patch(cal,p,v)),False)
check('F03 rejects unsorted intervals',lambda:calendar(dict(cal,intervals=list(reversed(cal['intervals'])))),False)
check('F03 empty calendar means explicit unavailability',lambda:calendar(dict(cal,intervals=[])))
check('F03 explicit capture rebase/intersection without source mutation',lambda:project_calendar(cal,'2026-09-12T00:00:05Z',10)['intervals']==[dict(start_s=0,end_s=5,available_units=1),dict(start_s=5,end_s=10,available_units=0)] and cal['epoch_utc']==epoch)
binding=dict(resource_id=u(2),source_calendar=cal,source_hash=digest(cal),calendar=project_calendar(cal,'2026-09-12T00:00:05Z',10))
check('F03 source/hash/projected calendar is recomputable',lambda:calendar_binding(binding,'2026-09-12T00:00:05Z',10))
check('F03 stale source hash rejected',lambda:calendar_binding(dict(binding,source_hash='0'*64),'2026-09-12T00:00:05Z',10),False)
check('F03 unrebased integer intervals rejected',lambda:calendar_binding(dict(binding,calendar=cal),'2026-09-12T00:00:05Z',10),False)
body=canonical(dict(schema_version='2.0.0',input_id=u(21)))
actor=dict(actor_id=u(9),role='operator',scope_id=u(8))
commands=[]
for family in spec['job_kind_mapping']:
    ref=dict(request_id=u(10),version=1,schema_version='2.0.0',hash=hashlib.sha256(body).hexdigest(),family=family)
    payload=dict(family=family,request_ref=ref)
    if family=='optimization':payload['mode']='transport'
    command=dict(schema_version='2.0.0',kind=family,payload=payload,deadline_utc='2026-09-12T00:01:00Z')
    metadata=dict(ref=copy.deepcopy(ref),scope_id=u(8),owner_actor_id=u(9),optimization_mode=payload.get('mode'),media_type='application/json')
    commands.append((command,metadata))
    check('F01/F04 legal '+family+' branch/ref metadata',lambda c=command,m=metadata:resolve(c,m,body,actor))
command,metadata=commands[0]
for mode in ['transport','warehouse','joint']:
    check('F01 legal optimization mode '+mode,lambda m=mode:job_command(patch(command,['payload','mode'],m)))
for label,path,new in [('unknown kind',['kind'],'routing'),('family mismatch',['payload','family'],'simulation'),('ref family mismatch',['payload','request_ref','family'],'metric'),('zero version',['payload','request_ref','version'],0),('empty hash',['payload','request_ref','hash'],''),('uppercase hash',['payload','request_ref','hash'],'A'*64),('old schema',['schema_version'],'1.0.0')]:check('F01/F04 rejects '+label,lambda p=path,v=new:job_command(patch(command,p,v)),False)
check('F01 nonoptimization extra mode rejected',lambda:job_command(patch(commands[1][0],['payload','mode'],'transport')),False)
check('F04 changed saved bytes rejected',lambda:resolve(command,metadata,body+b' ',actor),False)
check('F04 missing identity rejected',lambda:resolve(command,dict(metadata,ref=dict(metadata['ref'],request_id=u(99))),body,actor),False)
check('F04 old revision rejected',lambda:resolve(command,metadata,body,actor,current_version=2),False)
check('F04 metadata cannot replace a missing real capability',lambda:resolve(command,metadata,body,actor,enabled=False),False)
check('Actor viewer cannot submit',lambda:resolve(command,metadata,body,dict(actor,role='viewer')),False)
check('Actor cross scope rejected',lambda:resolve(command,metadata,body,dict(actor,scope_id=u(99))),False)
check('Actor unknown body permission field rejected',lambda:parse('ActorContext',dict(actor,permission='admin')) or True,False)
check('F04 JSON duplicate keys rejected',lambda:strict_json(b'{"x":1,"x":2}'),False)
check('F04 JSON nonfinite numbers rejected',lambda:strict_json(b'{"x":NaN}'),False)
resources=dict(warehouses=[],zones=[],locations=[],docks=[],workers=[],equipment=[],calendars=[])
snapshot=dict(id=u(50),scope=dict(order_ids=[],warehouse_ids=[],vehicle_ids=[],epoch_utc=epoch,horizon_s=100),orders=[],cargo=[],vehicles=[],drivers=[],resources=resources,inventory=[],revisions=[],matrices=[],hash='0'*64)
snapshot['hash']=digest({k:v for k,v in snapshot.items() if k!='hash'})
size={k:0 for k in types['ScenarioSize']['fields']}
bundle=dict(schema_version='2.0.0',ref=dict(scenario_id=u(1),dataset_version=1,schema_version='2.0.0',content_hash='0'*64),spec=dict(id=u(1),version=1,schema_version='2.0.0',generator_version='1.0.0',seed=42,epoch_utc=epoch,horizon_s=100,size=size,generation_policy='grid',event_specs=[]),input=dict(snapshot=snapshot,transport_tasks=[],warehouse_tasks=[]),source='synthetic')
bundle['ref']['content_hash']=scenario_hash(bundle)
check('F02 complete typed empty scenario boundary accepted',lambda:scenario(bundle))
check('F02 canonical key reordering preserves identity',lambda:scenario_hash(dict(reversed(list(bundle.items()))))==bundle['ref']['content_hash'])
check('F02 changed seed changes identity',lambda:scenario_hash(patch(bundle,['spec','seed'],43))!=bundle['ref']['content_hash'])
oracle=dict(schema_version='2.0.0',scenario_ref=bundle['ref'],expectations=[dict(kind='integer',measure='distance_m',value=9000)])
check('F02 independent typed sidecar accepted',lambda:parse('FixtureExpectations',oracle) is None)
check('F02 oracle mutation cannot affect input hash',lambda:patch(oracle,['expectations',0,'value'],1)!=oracle and scenario_hash(bundle)==bundle['ref']['content_hash'])
for label,path,new in [('version mismatch',['ref','dataset_version'],2),('bad hash',['ref','content_hash'],'1'*63),('size mismatch',['spec','size','orders'],1),('seed tamper without rehash',['spec','seed'],43),('oracle injection',['input','expected_plan'],{}),('duplicate event authority',['input','event_specs'],[])]:check('F02 rejects '+label,lambda p=path,v=new:scenario(patch(bundle,p,v)),False)
check('F02 rejects executable generation policy',lambda:scenario(patch(bundle,['spec','generation_policy'],'eval(script)')),False)
equipment=dict(id=u(2),status='available',created_at=epoch,updated_at=epoch,row_version=0,schema_version='2.0.0',created_by=u(9),warehouse_id=u(3),kind='handling',quantity_capacity=1,allowed_zone_ids=[],calendar=cal)
check('Resource equipment wrapper keeps inner equipment kind',lambda:parse('ResourceDTO',dict(kind='equipment',value=equipment)) is None)
check('Resource mismatched branch/entity rejected',lambda:parse('ResourceDTO',dict(kind='zone',value=equipment)),False)
check('Resource vehicle is outside generic five-kind endpoint',lambda:parse('ResourceDTO',dict(kind='vehicle',value=equipment)),False)
check('Resource capacity negative rejected',lambda:parse('ResourceDTO',dict(kind='equipment',value=dict(equipment,quantity_capacity=-1))),False)
check('F03 Resource calendar units exceed known capacity rejected',lambda:parse('ResourceDTO',dict(kind='equipment',value=patch(equipment,['calendar','intervals',0,'available_units'],2))),False)
tampered=patch(bundle,['input','snapshot','hash'],'1'*64);tampered['ref']['content_hash']=scenario_hash(tampered)
check('F02 rehash outer bundle cannot hide stale inner snapshot',lambda:scenario(tampered),False)
job=dict(id=u(40),created_at=epoch,updated_at=epoch,row_version=0,schema_version='2.0.0',created_by=u(9),status='completed',kind='optimization',command=command,request_hash=digest(command),trace_id=u(41),actor_id=u(9),scope_id=u(8),available_at=epoch,deadline_utc=command['deadline_utc'],attempt=1,max_attempts=3,cancel_requested=False,lease_owner=None,lease_epoch=1,lease_expires_at=None,started_at=epoch,finished_at='2026-09-12T00:00:01Z',result_ref=dict(result_id=u(42),version=1,schema_version='2.0.0',hash='0'*64,family='optimization'),failure=None)
check('F04 completed Job binds immutable command and typed result ref',lambda:lifecycle(job))
for label,path,new in [('completed without result',['result_ref'],None),('wrong result family',['result_ref','family'],'simulation'),('terminal lease retained',['lease_owner'],u(9)),('end before start',['finished_at'],'2026-09-11T23:59:59Z'),('attempt limit',['attempt'],4),('false worker failed',['status'],'failed')]:check('F04 lifecycle rejects '+label,lambda p=path,v=new:lifecycle(patch(job,p,v)),False)
token=dict(job_id=u(40),owner_id=u(9),epoch=2,expires_at='2026-09-12T00:01:00Z')
check('F04 current unexpired lease accepted by contract predicate',lambda:lease_accept(token,token,epoch))
check('F04 old lease epoch rejected',lambda:lease_accept(dict(token,epoch=1),token,epoch),False)
check('F04 expired lease rejected',lambda:lease_accept(token,token,'2026-09-12T00:01:00Z'),False)
# Independent negative mutations must be rejected by the persistent source checker.
check('Registered type/task/module graph closed',lambda:not validate_plan.validate_contract_decisions(spec,manifest))
for name,mutator in [
    ('missing named type',lambda s:s['types'][next(i for i,r in enumerate(s['types']) if r['name']=='JobCommand')]['fields'].update(payload='UnknownPayload')),
    ('future type owner',lambda s:next(r for r in s['types'] if r['name']=='ScenarioRef').update(task='P11-01')),
    ('hidden oracle path',lambda s:next(r for r in s['types'] if r['name']=='PlanningSnapshot')['fields'].update(oracle='FixtureExpectations')),
    ('source enum duplicate',lambda s:s['types'].append(copy.deepcopy(next(r for r in s['types'] if r['name']=='JobKind')))),
]:
    bad=copy.deepcopy(spec);mutator(bad)
    check('Persistent checker catches '+name,lambda b=bad:bool(validate_plan.validate_contract_decisions(b,manifest)))
domain=(ROOT/'docs/architecture/DOMAIN_CATALOG.md').read_text(encoding='utf-8')
for projection in spec['master_projections']:
    line=next(r for r in domain.splitlines() if r.startswith('| '+projection['base']+' /'))
    keys=set(re.findall(r'(?:^|;\s*)([a-z_][a-z0-9_]*):',line.split('|')[3].strip()))
    check('Exact master projection inherited fields '+projection['name'],lambda p=projection,k=keys:set(p['selected_fields'])<=k and not set(p['selected_fields'])&set(p['server_common_fields']))
check('19 master create/patch projections and 9 query types have unique explicit shapes',lambda:len(spec['master_projections'])==19 and len({p['name'] for p in spec['master_projections']})==19 and len(spec['master_queries'])==9)
check('Manifest business node identities and initial states preserved',lambda:[t['id'] for t in manifest['tasks']]==scope['manifest_task_ids'] and all(t['status']=='planned' for t in manifest['tasks']) and all(g['status']=='not_run' for g in manifest['gates']))
with tempfile.TemporaryDirectory(prefix='render-',dir=ROOT/'tmp/N01-R02/examples') as directory:
    render_plan.ROOT=Path(directory);render_plan.main()
    actual={p.relative_to(directory).as_posix():sha(p) for p in Path(directory).rglob('*') if p.is_file()}
    check('114 generator outputs exactly enumerated before mutation',lambda:set(actual)==set(scope['generated_outputs']))
    check('Generated outputs reproduce byte for byte',lambda:all(sha(ROOT/p)==h for p,h in actual.items()))
links=[]
for p in scope['whitelist']:
    if p.endswith('.md') and (ROOT/p).is_file():links+=validate_plan.local_links(ROOT/p,ROOT)
check('All modified-document local file links valid',lambda:not links)
protected_changes=[p for p,h in scope['protected'].items() if not (ROOT/p).is_file() or sha(ROOT/p)!=h]
check(str(len(scope['protected']))+' this-round protected files preserve original bytes',lambda:not protected_changes)
changed=[p for p,h in scope['before'].items() if (ROOT/p).is_file() and sha(ROOT/p)!=h]
freeze=json.loads((ROOT/'docs/architecture/CONTRACT_FREEZE.json').read_text(encoding='utf-8'))
freeze_drift=[r['path'] for r in freeze['artifacts'] if sha(ROOT/r['path'])!=r['sha256']]
inherited_check_count=len(results)
from event_reference_examples import run_examples
event_examples=run_examples(check,parse,spec,digest,patch,epoch)
summary=dict(status='PASS' if all(r['passed'] for r in results) else 'FAIL',checks=len(results),passed=sum(r['passed'] for r in results),failed=sum(not r['passed'] for r in results),results=results,protected_file_count=len(scope['protected']),protected_changes=protected_changes,changed_files=changed,freeze_drift=freeze_drift,limitations=['Executable design examples only, no business classes or HTTP/DB acceptance.','Existing source leaf fields reused; full inherited schema behavior requires real G02 exports/tests.','resolve examples check reference metadata and failure ordering only; no real capability parser/worker was run.', 'Inherited parse-only adapters still do not enforce CalendarDTO overlap, RegionRef nonempty nodes, OnArc temporal order, or complete Scenario FK/calendar binding integrity; N02-R01 limitations are retained.', 'New event-reference predicates validate the normative mapping against a fixed design fact snapshot; they are not domain classes, ingest services, DB/solver/SimPy acceptance, or live revalidation of old audit references.', 'Inherited entity adapters verify named field structure and selected primitive constraints; CargoType/Skill/Qualification and full inherited entity state machines remain outside this bounded design harness.'])
summary.update(round='N01-R02',inherited_check_count=inherited_check_count,event_reference_check_count=len(results)-inherited_check_count,event_case_counts=event_examples['case_counts'],source_inputs={p:sha(ROOT/p) for p in ['contracts/changes/N01-R01-contract-decisions.json','docs/plan/TASK_MANIFEST.json','tmp/N01-R02/scope-before.json','tmp/N01-R01/verify_contracts.py','tmp/N01-R02/examples/verify_design_examples.py','tmp/N01-R02/examples/event_reference_examples.py','tools/ai_coding_plan/validate_plan.py','tools/ai_coding_plan/render_plan.py']})
(OUT/('contract-validation'+suffix+'.json')).write_text(json.dumps(summary,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
(OUT/('contract-examples'+suffix+'.json')).write_text(json.dumps(dict(calendar=cal,job_commands=commands,actor=actor,scenario=bundle,expectations=oracle,resource=dict(kind='equipment',value=equipment),event_references=event_examples),ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps({k:v for k,v in summary.items() if k!='results'},ensure_ascii=False))
sys.exit(0 if summary['status']=='PASS' else 1)
