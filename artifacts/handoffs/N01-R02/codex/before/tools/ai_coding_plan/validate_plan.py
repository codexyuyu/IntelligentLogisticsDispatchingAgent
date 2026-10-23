"""Stdlib checks for planning artifacts. Never runs or certifies application tests."""
from pathlib import Path
from datetime import datetime, timezone
from copy import deepcopy
import argparse
import hashlib
import json
import io
import platform
import re
import sys
import unittest

ROOT=Path(__file__).resolve().parents[2]
REQUIRED=['Context','Current State','Objective','Scope','Out of Scope','Architecture Constraints','Files','Domain Model','Input','Output','Interfaces','Data Contract','Business Rules','Algorithm','Edge Cases','Error Handling','Logging','Observability','Testing','Test Cases','Acceptance Criteria','Validation Commands','Documentation','Completion Report']
OR_FIELDS=['Decision Variables','Constraints','Objective Function','Solver Configuration','Result Extraction','Validation']
ENTITY_NAMES=['Order','Cargo','Vehicle','Driver','Warehouse','WarehouseZone','StorageLocation','Dock','Worker','Equipment','TransportTask','WarehouseTask','Route','RouteStop','Schedule','ScheduleTask','ScheduleVersion','Constraint','OptimizationRequest','OptimizationResult','Simulation','SimulationSnapshot','Event','ExceptionEvent','RescheduleRequest','RescheduleResult','AgentRun','ToolCall','DecisionRecord','Experiment','Metric','ExperimentResult']
EXPECTED_GROUPS={'00-master','01-foundation','02-domain','03-database','04-api','05-transport-solver','06-warehouse-solver','07-simulation','08-exception','09-agents','10-frontend','11-evaluation','12-integration','13-release'}
MASTER_HEADINGS=['项目目标','非目标','架构原则','系统上下文','技术架构','模块划分','模块依赖图','Domain Model','API Boundary','Agent Boundary','Solver Boundary','Simulation Boundary','数据库边界','前端边界','测试策略','Observability','Security','Demo Strategy','Milestones','Definition of Done']

def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()

def validate_graph(data):
    errors=[];nodes=data['tasks']+data['gates'];by_id={n['id']:n for n in nodes}
    if len(by_id)!=len(nodes):errors.append('duplicate node id')
    for n in nodes:
        for d in n['deps']:
            if d not in by_id:errors.append(f'{n["id"]}: missing dependency {d}')
        actual={q['id'] for q in nodes if n['id'] in q['deps']}
        if actual!=set(n.get('blocks',[])):errors.append(f'{n["id"]}: reverse blocks mismatch')
    color={};anc={}
    def visit(x):
        if color.get(x)==1:raise ValueError('cycle: '+x)
        if color.get(x)==2:return anc[x]
        color[x]=1;result=set()
        for d in by_id[x]['deps']:
            if d in by_id:result.add(d);result.update(visit(d))
        color[x]=2;anc[x]=result;return result
    try:
        for n in nodes:visit(n['id'])
    except ValueError as exc:errors.append(str(exc));return errors
    for t in data['tasks']:
        for pid in t.get('parallel',[]):
            q=by_id.get(pid)
            if not q:errors.append('missing parallel task '+pid);continue
            if q['phase']!=t['phase']:errors.append('parallel crosses phase gate')
            if pid in anc[t['id']] or t['id'] in anc[pid]:errors.append('parallel dependency conflict')
            if set(q.get('allowed_files',[]))&set(t.get('allowed_files',[])):errors.append('parallel write conflict')
            if t['id'] not in q.get('parallel',[]):errors.append('parallel relation is not symmetric')
    return errors

def validate_prompt(body,tid,solver=False):
    errors=[];headings=re.findall(r'^## (.+)$',body,re.M)
    if headings!=REQUIRED:errors.append(tid+': missing, duplicate or reordered required section')
    sections=re.split(r'^## .+$',body,flags=re.M)[1:]
    if any(len(s.strip())<25 for s in sections):errors.append(tid+': empty/trivial section')
    if solver:
        for name in OR_FIELDS:
            if not re.search(r'^### '+re.escape(name)+r'$',body,re.M):errors.append(tid+': missing OR section '+name)
    for token in ['Files created','Files modified','Tests added','Commands executed','Test results','Known limitations','Remaining risks','Unit Test','Integration Test','docs/architecture/issues/','fake implementation','hard-coded demo answer']:
        if token not in body:errors.append(tid+': missing required item '+token)
    if '```powershell\n' not in body:errors.append(tid+': missing executable command block')
    return errors

def local_links(path,root):
    errors=[];text=path.read_text(encoding='utf-8-sig')
    # Ignore fenced examples; links in visible prose/tables remain checked.
    text=re.sub(r'```.*?```','',text,flags=re.S)
    for raw in re.findall(r'\[[^\]\n]+\]\(([^)\n]+)\)',text):
        dest=raw.strip().split('#',1)[0]
        if not dest or re.match(r'^[a-z]+://',dest):continue
        dest=dest.strip('<>')
        target=(path.parent/dest).resolve()
        if not target.is_relative_to(root.resolve()):errors.append(str(path)+': link escapes plan root '+dest)
        elif not target.exists():errors.append(str(path.relative_to(root))+': missing local link '+dest)
    return errors

def validate_cases(body, task):
    """Compare concrete case rows, so prompt/manifest drift cannot pass silently."""
    section = re.search(r'^## Test Cases\s*\n(.*?)(?=^## |\Z)', body, re.M | re.S)
    rows = re.findall(r'^\|\s*\d+\s*\|\s*(.*?)\s*\|', section.group(1), re.M) if section else []
    return [] if rows == task['cases'] else [task['id']+': prompt/manifest Test Cases drift']

CONTRACT_DECISIONS_PATH='contracts/changes/N01-R01-contract-decisions.json'
CONTRACT_PRIMITIVES={'UUID','UTC','str','int','bool','Sha256','PositiveInt','NonNegativeInt','Seed','Horizon','SchemaVersion','VersionText','SafeText'}
CONTRACT_SOURCE_PATHS={'docs/architecture/DOMAIN_CATALOG.md','docs/architecture/DATA_CONTRACTS.md','docs/architecture/IMPLEMENTATION_CONVENTIONS.md','docs/api/API_CONTRACT.md','docs/algorithms/OPTIMIZATION_CONTRACT.md','docs/algorithms/SIMULATION_CONTRACT.md','docs/algorithms/METRICS_CONTRACT.md','docs/plan/TEST_FIXTURES.md'}
JOB_KIND_VALUES=('optimization','simulation','reschedule','experiment','metric')

def contract_type_reference(expression):
    """The registry has a small closed type language; arbitrary Python is invalid."""
    if not isinstance(expression,str) or not expression:
        raise ValueError('empty or non-string type expression')
    if expression.startswith('='):
        if len(expression)==1:raise ValueError('empty literal')
        return None
    if not re.fullmatch(r'[A-Za-z_][A-Za-z0-9_]*(?:\[\])?(?:\?)?',expression):
        raise ValueError('invalid type expression '+expression)
    return re.sub(r'(?:\[\])?\?$', '',expression) if expression.endswith('?') else expression.removesuffix('[]')

def validate_contract_decisions(data, manifest):
    """Validate design closure and task availability, never certify implementation."""
    errors=[]
    def fail(message):errors.append('contract decisions: '+message)
    if not isinstance(data,dict):return ['contract decisions: registry must be an object']
    if data.get('decision_round')!='N01-R01':fail('unexpected decision round')
    if data.get('contract_version')!='2.0.0':fail('contract version must be 2.0.0')
    if data.get('plan_version')!=manifest.get('plan_version'):fail('registry/manifest plan version mismatch')
    tasks={t['id']:t for t in manifest.get('tasks',[])}
    nodes={n['id']:n for n in manifest.get('tasks',[])+manifest.get('gates',[])}
    ancestors={};visiting=set()
    def available_before(tid):
        if tid in ancestors:return ancestors[tid]
        if tid in visiting:fail('task dependency cycle '+tid);return set()
        visiting.add(tid);result=set()
        for dependency in nodes.get(tid,{}).get('deps',[]):
            if dependency not in nodes:fail('missing task dependency '+dependency);continue
            result.add(dependency);result.update(available_before(dependency))
        visiting.remove(tid);ancestors[tid]=result;return result
    for tid in nodes:available_before(tid)
    def available(defining_task, consuming_task):
        return defining_task==consuming_task or defining_task in ancestors.get(consuming_task,set())
    def valid_path(path):
        return isinstance(path,str) and bool(path) and '\\' not in path and ':' not in path and not path.startswith('/') and '..' not in path.split('/')
    types={};references={};module_tasks={}
    rows=data.get('types')
    if not isinstance(rows,list) or not rows:fail('nonempty types list required');rows=[]
    for row in rows:
        if not isinstance(row,dict):fail('type entry must be an object');continue
        name=row.get('name')
        if not isinstance(name,str) or not re.fullmatch(r'[A-Za-z_][A-Za-z0-9_]*',name):fail('invalid type name');continue
        if name in types:fail('duplicate type '+name);continue
        if name in CONTRACT_PRIMITIVES:fail('type shadows primitive '+name)
        types[name]=row;references[name]=set()
        task=row.get('task');path=row.get('path');kind=row.get('kind')
        if task not in tasks:fail(name+': unknown definition task '+str(task))
        if not valid_path(path):fail(name+': invalid carrier path '+str(path))
        elif task in tasks and path not in tasks[task].get('allowed_files',[]):fail(name+': carrier outside definition task whitelist '+path)
        if isinstance(path,str):module_tasks.setdefault(path,set()).add(task)
        if kind not in {'record','enum','union','existing','mapped'}:fail(name+': unknown kind '+str(kind))
        fields=row.get('fields',{})
        if not isinstance(fields,dict):fail(name+': fields must be an object');fields={}
        if kind=='record' and not fields:fail(name+': empty record is not a complete type')
        extra=row.get('extra_fields',{})
        if not isinstance(extra,dict):fail(name+': extra_fields must be an object');extra={}
        if extra and kind!='mapped':fail(name+': only mapped boundary types allow extra_fields')
        fields={**fields,**extra}
        for field,expression in fields.items():
            if not isinstance(field,str) or not re.fullmatch(r'[a-z_][A-Za-z0-9_]*',field):fail(name+': invalid field name '+str(field))
            try:ref=contract_type_reference(expression)
            except ValueError as exc:fail(name+'.'+str(field)+': '+str(exc));continue
            if ref and ref not in CONTRACT_PRIMITIVES:references[name].add(ref)
        base=row.get('base')
        if kind=='mapped' and not base:fail(name+': mapped type requires base')
        if base:
            try:ref=contract_type_reference(base)
            except ValueError as exc:fail(name+': invalid base '+str(exc));ref=None
            if kind=='mapped' and (not ref or ref in CONTRACT_PRIMITIVES or base!=ref):fail(name+': mapped base must be one named type')
            if ref and ref not in CONTRACT_PRIMITIVES:references[name].add(ref)
        if kind=='enum':
            members=row.get('members')
            if not isinstance(members,dict) or not members:fail(name+': enum members required')
            elif any(not isinstance(k,str) or not isinstance(v,str) or not v for k,v in members.items()):fail(name+': invalid enum member/value')
            elif len(set(members.values()))!=len(members):fail(name+': duplicate enum serialization value')
        if kind=='union':
            variants=row.get('variants')
            if row.get('discriminator') not in {'kind','family','entity_kind'}:fail(name+': union discriminator must be kind, family or entity_kind')
            if not isinstance(variants,dict) or not variants:fail(name+': nonempty union variants required')
            else:
                for tag,expression in variants.items():
                    if not isinstance(tag,str) or not tag:fail(name+': empty union tag')
                    try:ref=contract_type_reference(expression)
                    except ValueError as exc:fail(name+': invalid variant '+str(exc));continue
                    if not ref or ref in CONTRACT_PRIMITIVES:fail(name+': union branch must be a named type')
                    else:references[name].add(ref)
        if kind=='existing':
            source=row.get('source','')
            if not isinstance(source,str) or '#' not in source:fail(name+': existing leaf requires registered document and section');continue
            source_path,section=source.split('#',1)
            if source_path not in CONTRACT_SOURCE_PATHS or not section:fail(name+': unregistered existing source '+source);continue
            target=ROOT/source_path
            if not target.is_file():fail(name+': existing source file missing '+source_path);continue
            body=target.read_text(encoding='utf-8-sig')
            headings=re.findall(r'^#{1,6}\s+(.+?)\s*$',body,re.M)
            anchors={re.sub(r'[^\w\s-]','',h.lower()).replace(' ','-') for h in headings}
            if section not in anchors and not re.search(r'\b'+re.escape(section)+r'\b',body):fail(name+': existing source section missing '+source)
            if not re.search(r'\b'+re.escape(name)+r'\b',body):fail(name+': type absent from existing source '+source_path)
    for name,refs in references.items():
        for ref in refs:
            if ref not in types:fail(name+': missing referenced type '+ref);continue
            defining=types[ref].get('task');consumer=types[name].get('task')
            if defining in tasks and consumer in tasks and not available(defining,consumer):fail(name+': future or unordered type dependency '+ref+' ('+defining+' -> '+consumer+')')
        row=types[name]
        if row.get('kind')=='union' and isinstance(row.get('variants'),dict):
            discriminator=row.get('discriminator')
            for tag,branch in row['variants'].items():
                if branch in types and types[branch].get('fields',{}).get(discriminator)!='='+tag:fail(name+': branch '+branch+' discriminator literal does not match '+str(tag))
    def check_dag(graph,label):
        color={}
        def visit(node):
            if color.get(node)==1:fail(label+' cycle '+node);return
            if color.get(node)==2:return
            color[node]=1
            for dependency in graph.get(node,set()):
                if dependency in graph:visit(dependency)
            color[node]=2
        for node in graph:visit(node)
    check_dag(references,'type reference')
    modules=data.get('module_dependencies')
    if not isinstance(modules,dict):fail('module_dependencies must be an object');modules={}
    module_graph={}
    for path,dependencies in modules.items():
        if not valid_path(path):fail('invalid module path '+str(path));continue
        if path not in module_tasks:fail('module has no registered defining types '+path)
        if not isinstance(dependencies,list) or any(not isinstance(p,str) for p in dependencies):fail(path+': invalid module dependency list');continue
        if len(set(dependencies))!=len(dependencies):fail(path+': duplicate module dependency')
        module_graph[path]=set(dependencies)
        for dependency in dependencies:
            if not valid_path(dependency) or dependency not in module_tasks:fail(path+': unregistered dependency module '+dependency);continue
            if path.startswith('packages/domain/') and not dependency.startswith('packages/domain/'):fail(path+': domain imports non-domain module '+dependency)
            consuming_tasks=module_tasks.get(path,set())
            defining_tasks=module_tasks.get(dependency,set())
            for consuming in consuming_tasks:
                if consuming in tasks and not any(defining in tasks and available(defining,consuming) for defining in defining_tasks):fail(path+': future or unordered module dependency '+dependency)
    for path in module_tasks:
        if path not in modules:fail('registered carrier missing from module dependency graph '+path)
    for name,refs in references.items():
        source_path=types[name].get('path')
        for ref in refs:
            if ref in types:
                target_path=types[ref].get('path')
                if source_path!=target_path and target_path not in module_graph.get(source_path,set()):fail(name+': undeclared module dependency '+str(target_path))
    check_dag(module_graph,'module dependency')
    def require(name,kind=None,task=None,path=None):
        row=types.get(name)
        if not row:fail('required type missing '+name);return {}
        if kind and row.get('kind')!=kind:fail(name+': required kind '+kind)
        if task and row.get('task')!=task:fail(name+': wrong definition task; required '+task)
        if path and row.get('path')!=path:fail(name+': wrong unique carrier; required '+path)
        return row
    states='packages/domain/src/logistics_domain/states.py'
    primitives='packages/domain/src/logistics_domain/primitives.py'
    runtime='packages/domain/src/logistics_domain/runtime.py'
    job_kind=require('JobKind','enum','P02-01',states)
    if job_kind.get('members')!={value.upper():value for value in JOB_KIND_VALUES}:fail('JobKind: exact five members/values required')
    mapping=data.get('job_kind_mapping')
    expected_mapping={value:value.title()+'JobPayload' for value in JOB_KIND_VALUES}
    if mapping!=expected_mapping:fail('JobKind/payload mapping mismatch')
    job_command=require('JobCommand','record','P02-04',runtime)
    if job_command.get('fields',{}).get('kind')!='JobKind' or job_command.get('fields',{}).get('payload')!='JobPayload':fail('JobCommand must bind JobKind to JobPayload')
    job_payload=require('JobPayload','union','P02-04',runtime)
    if job_payload.get('variants')!=expected_mapping:fail('JobPayload: exact five mapped branches required')
    if job_payload.get('discriminator')!='family':fail('JobPayload: family discriminator required')
    request_ref=require('RequestRef','record','P02-04',runtime)
    if request_ref.get('fields',{}).get('family')!='JobKind':fail('RequestRef must use the unique JobKind family')
    if request_ref.get('fields')!=dict(request_id='UUID',version='PositiveInt',schema_version='=2.0.0',hash='Sha256',family='JobKind'):fail('RequestRef: exact versioned immutable identity required')
    for family,payload in expected_mapping.items():
        row=require(payload,'record','P02-04',runtime)
        if row.get('fields',{}).get('family')!='='+family:fail(payload+': missing or mismatched family literal')
        if row.get('fields',{}).get('request_ref')!='RequestRef':fail(payload+': requires the shared RequestRef')
    optimization_modes=require('JobOptimizationMode','enum','P02-01',states)
    if optimization_modes.get('members')!={value.upper():value for value in ('transport','warehouse','joint')}:fail('JobOptimizationMode: transport/warehouse/joint modes required')
    if types.get('OptimizationJobPayload',{}).get('fields',{}).get('mode')!='JobOptimizationMode':fail('OptimizationJobPayload must carry JobOptimizationMode')
    request=require('JobRequest','mapped','P02-04','packages/contracts/src/logistics_contracts/runtime.py')
    if request.get('base')!='JobCommand':fail('JobRequest must map the early JobCommand')
    for name in ('CalendarInterval','ResourceCalendar'):require(name,'record','P02-01',primitives)
    interval=types.get('CalendarInterval',{})
    if interval.get('fields')!=dict(start_s='NonNegativeInt',end_s='NonNegativeInt',available_units='NonNegativeInt'):fail('CalendarInterval: complete start/end/available_units fields required')
    calendar=require('ResourceCalendar')
    if calendar.get('fields')!=dict(epoch_utc='UTC',intervals='CalendarInterval[]',version='NonNegativeInt'):fail('ResourceCalendar: complete epoch/interval/version fields required')
    calendar_dto=require('CalendarDTO','mapped')
    if calendar_dto.get('base')!='ResourceCalendar':fail('CalendarDTO must map shared ResourceCalendar')
    if calendar_dto.get('extra_fields')!=dict(schema_version='=2.0.0'):fail('CalendarDTO: HTTP version must be explicit')
    for name in ('ScenarioSpec','ScenarioRef','ScenarioInput','ScenarioBundle'):require(name,'record','P02-04',runtime)
    if types.get('ScenarioRef',{}).get('fields')!=dict(scenario_id='UUID',dataset_version='PositiveInt',schema_version='=2.0.0',content_hash='Sha256'):fail('ScenarioRef: exact id/dataset/schema/hash fields required')
    if types.get('ScenarioBundle',{}).get('fields')!=dict(schema_version='=2.0.0',ref='ScenarioRef',spec='ScenarioSpec',input='ScenarioInput',source='=synthetic'):fail('ScenarioBundle: exact runtime input envelope required')
    spec=types.get('ScenarioSpec',{})
    if spec.get('fields',{}).get('event_specs')!='ScenarioEventSpec[]':fail('ScenarioSpec must uniquely own ScenarioEventSpec[]')
    for name in ('ScenarioInput','ScenarioBundle'):
        if 'event_specs' in types.get(name,{}).get('fields',{}):fail(name+': event specs duplicated outside ScenarioSpec')
        reachable=set();pending=[name]
        while pending:
            current=pending.pop()
            if current in reachable:continue
            reachable.add(current);pending.extend(references.get(current,set()))
        forbidden=sorted(ref for ref in reachable if ref.startswith(('FixtureExpectation','Expected')) or ref in {'CandidatePlan','Route','RouteStop','SolverEvidence'})
        if forbidden:fail(name+': formal input leaks fixture expectations or solver answers '+', '.join(forbidden))
    return errors

def validate_artifacts(data,task_id=None):
    errors=validate_graph(data);tasks=data['tasks'];gates=data['gates']
    decisions=ROOT/CONTRACT_DECISIONS_PATH
    if not decisions.is_file():errors.append('missing contract decision registry '+CONTRACT_DECISIONS_PATH)
    else:
        try:errors+=validate_contract_decisions(json.loads(decisions.read_text(encoding='utf-8')),data)
        except (ValueError,TypeError,KeyError) as exc:errors.append('invalid contract decision registry: '+str(exc))
    if len(gates)!=40 or {g['id'] for g in gates}!={f'G{p:02d}' for p in range(40)}:errors.append('40 numbered gates required')
    if {t['phase'] for t in tasks}!=set(range(40)):errors.append('phase coverage gap')
    if {Path(t['prompt']).parent.name for t in tasks}!=EXPECTED_GROUPS:errors.append('14 prompt group coverage mismatch')
    if len({t['prompt'] for t in tasks})!=len(tasks):errors.append('duplicate prompt path')
    selected=[t for t in tasks if not task_id or t['id']==task_id]
    if task_id and not selected:errors.append('unknown task '+task_id)
    for t in tasks:
        p=t['phase']
        if p>0 and f'G{p-1:02d}' not in t['deps']:errors.append(t['id']+': missing preceding phase gate')
        if t['phase_gate']!=f'G{p:02d}':errors.append(t['id']+': mismatched phase gate')
        if t['status']!='planned':errors.append(t['id']+': planning artifact claims implementation progress')
        if not t['files'] or not t['commands'] or len(t['cases'])<2:errors.append(t['id']+': missing concrete artifacts/commands/cases')
        if any(x.startswith(('demo/','demos/')) for x in t['allowed_files']):errors.append(t['id']+': modifies protected legacy')
        for field in ['unit_test','integration_test']:
            if not t.get(field):errors.append(t['id']+': missing '+field)
        for cmd in t['commands']:
            for test_path in re.findall(r'(?:tests/[A-Za-z0-9_./-]+\.(?:py|ts)|apps/frontend/src/test/[A-Za-z0-9_./-]+\.tsx)',cmd):
                if test_path not in t['allowed_files']:errors.append(t['id']+': command test path outside Files: '+test_path)
    for g in gates:
        if set(g['deps'])!={t['id'] for t in tasks if t['phase']==g['phase']}:errors.append(g['id']+': missing task gate dependency')
        if g['status']!='not_run':errors.append(g['id']+': planning artifact claims a passed gate')
    for t in selected:
        file=ROOT/t['prompt']
        if not file.exists():errors.append('missing prompt '+t['prompt']);continue
        body=file.read_text(encoding='utf-8')
        errors+=validate_prompt(body,t['id'],t['kind']=='solver')
        errors+=validate_cases(body,t)
        for command in t['commands']:
            if command not in body:errors.append(t['id']+': prompt/manifest command drift')
        for required_path in t['allowed_files']:
            if required_path not in body:errors.append(t['id']+': Files/manifest drift '+required_path)
    actual=set(p.relative_to(ROOT).as_posix() for p in (ROOT/'docs/prompts').glob('*/*.md'))
    expected={t['prompt'] for t in tasks}
    if actual!=expected:errors.append('orphaned or missing prompt files: '+str(actual^expected))
    master=(ROOT/'PROJECT_MASTER_PLAN.md').read_text(encoding='utf-8')
    for n,h in enumerate(MASTER_HEADINGS,1):
        if f'## {n}. {h}' not in master:errors.append('missing Master Plan section '+h)
    catalog=(ROOT/'docs/architecture/DOMAIN_CATALOG.md').read_text(encoding='utf-8')
    for name in ENTITY_NAMES:
        if f'| {name} /' not in catalog:errors.append('missing required entity '+name)
    if len(ENTITY_NAMES)!=32:errors.append('entity catalog checker has incorrect count')
    trace=(ROOT/'docs/plan/REQUIREMENTS_TRACEABILITY.md').read_text(encoding='utf-8')
    by_id={n['id'] for n in tasks+gates}
    for ref in re.findall(r'\b(?:P\d{2}-\d{2}|G\d{2})\b',trace):
        if ref not in by_id:errors.append('traceability has unknown node '+ref)
    paths=[ROOT/'PROJECT_MASTER_PLAN.md',ROOT/'TASK_GRAPH.md',ROOT/'AI-CODING-PLAN.md']
    for directory in ['docs/architecture','docs/api','docs/algorithms','docs/plan','docs/prompts','docs/workflow']:
        paths.extend((ROOT/directory).rglob('*.md'))
    for path in paths:
        if path.name!='USER_REQUIREMENTS.md':errors+=local_links(path,ROOT)
    return errors,dict(tasks=len(tasks),gates=len(gates),prompt_groups=len(EXPECTED_GROUPS),required_prompt_sections=len(REQUIRED),required_entities=len(ENTITY_NAMES),markdown_files=len(paths),selected_prompts=len(selected))

class CheckerTests(unittest.TestCase):
    def test_matching_cases(self):
        task = dict(id='P01-02', cases=['input => expected'])
        self.assertEqual(validate_cases('## Test Cases\n\n| 1 | input => expected | assert |\n', task), [])
    def test_missing_case(self):
        task = dict(id='P01-02', cases=['input => expected', 'missing => reject'])
        self.assertTrue(validate_cases('## Test Cases\n\n| 1 | input => expected | assert |\n', task))
    def test_extra_case(self):
        task = dict(id='P01-02', cases=['input => expected'])
        self.assertTrue(validate_cases('## Test Cases\n\n| 1 | input => expected | assert |\n| 2 | extra => reject | assert |\n', task))
    def fixture(self):
        tasks=[dict(id='P00-01',phase=0,deps=[],blocks=['P00-02'],parallel=[],allowed_files=['a']),dict(id='P00-02',phase=0,deps=['P00-01'],blocks=['G00'],parallel=[],allowed_files=['b'])]
        return dict(tasks=tasks,gates=[dict(id='G00',phase=0,deps=['P00-02'],blocks=[])])
    def test_valid_graph(self):self.assertEqual(validate_graph(self.fixture()),[])
    def test_cycle(self):
        d=self.fixture();d['tasks'][0]['deps']=['G00'];self.assertTrue(any('cycle' in x for x in validate_graph(d)))
    def test_missing_dependency(self):
        d=self.fixture();d['tasks'][1]['deps']=['P99-01'];self.assertTrue(any('missing dependency' in x for x in validate_graph(d)))
    def test_reverse_blocks(self):
        d=self.fixture();d['tasks'][0]['blocks']=[];self.assertTrue(any('blocks mismatch' in x for x in validate_graph(d)))
    def test_duplicate_id(self):
        d=self.fixture();d['tasks'].append(deepcopy(d['tasks'][0]));self.assertTrue(any('duplicate node' in x for x in validate_graph(d)))
    def test_parallel_dependency(self):
        d=self.fixture();d['tasks'][0]['parallel']=['P00-02'];d['tasks'][1]['parallel']=['P00-01'];self.assertTrue(any('parallel dependency' in x for x in validate_graph(d)))
    def test_parallel_write_collision(self):
        d=self.fixture();d['tasks'][1]['deps']=[];d['tasks'][0]['blocks']=[]
        for t in d['tasks']:t['allowed_files']=['shared'];t['parallel']=['P00-02' if t['id']=='P00-01' else 'P00-01']
        self.assertTrue(any('parallel write' in x for x in validate_graph(d)))
    def test_cross_phase_parallel(self):
        d=self.fixture();d['tasks'][1]['phase']=1;d['tasks'][0]['parallel']=['P00-02'];self.assertTrue(any('crosses phase' in x for x in validate_graph(d)))
    def test_missing_prompt_sections(self):self.assertTrue(validate_prompt('# incomplete','P00-01'))
    def test_reordered_prompt_sections(self):
        body='\n'.join('## '+x+'\n'+'x'*40 for x in reversed(REQUIRED));self.assertTrue(any('reordered' in x for x in validate_prompt(body,'P00-01')))
    def test_missing_solver_sections(self):
        body='\n'.join('## '+x+'\n'+'x'*40 for x in REQUIRED);self.assertEqual(sum('missing OR section' in x for x in validate_prompt(body,'P07-01',True)),6)
    def test_entity_set(self):self.assertEqual(len(set(ENTITY_NAMES)),32)

class ContractDecisionTests(unittest.TestCase):
    """Independent miniature graphs exercise semantics, not copies of the registry."""
    def fixture(self):
        states='packages/domain/src/logistics_domain/states.py'
        primitives='packages/domain/src/logistics_domain/primitives.py'
        planning='packages/domain/src/logistics_domain/planning.py'
        runtime='packages/domain/src/logistics_domain/runtime.py'
        contracts_runtime='packages/contracts/src/logistics_contracts/runtime.py'
        http='packages/contracts/src/logistics_contracts/http.py'
        tasks=[
            dict(id='P02-01',deps=[],allowed_files=[states,primitives]),
            dict(id='P02-03',deps=['P02-01'],allowed_files=[planning]),
            dict(id='P02-04',deps=['P02-03'],allowed_files=[runtime,contracts_runtime]),
            dict(id='P05-02',deps=['P02-04'],allowed_files=[http]),
            dict(id='P05-03',deps=['P05-02'],allowed_files=[contracts_runtime]),
        ]
        rows=[]
        def record(name,fields,task='P02-04',path=runtime):
            rows.append(dict(name=name,kind='record',fields=fields,task=task,path=path,rules=[]))
        def enum(name,members):rows.append(dict(name=name,kind='enum',members=members,task='P02-01',path=states,rules=[]))
        enum('JobKind',{value.upper():value for value in JOB_KIND_VALUES})
        enum('JobOptimizationMode',{value.upper():value for value in ('transport','warehouse','joint')})
        record('CalendarInterval',dict(start_s='NonNegativeInt',end_s='NonNegativeInt',available_units='NonNegativeInt'),'P02-01',primitives)
        record('ResourceCalendar',dict(epoch_utc='UTC',intervals='CalendarInterval[]',version='NonNegativeInt'),'P02-01',primitives)
        rows.append(dict(name='CalendarDTO',kind='mapped',base='ResourceCalendar',extra_fields=dict(schema_version='=2.0.0'),task='P05-02',path=http,rules=[]))
        rows.append(dict(name='PlanningSnapshot',kind='existing',source='docs/architecture/DATA_CONTRACTS.md#PlanningSnapshot',task='P02-03',path=planning,rules=[]))
        record('RequestRef',dict(request_id='UUID',version='PositiveInt',schema_version='=2.0.0',hash='Sha256',family='JobKind'))
        mapping={value:value.title()+'JobPayload' for value in JOB_KIND_VALUES}
        for family,payload in mapping.items():
            fields=dict(family='='+family,request_ref='RequestRef')
            if family=='optimization':fields['mode']='JobOptimizationMode'
            record(payload,fields)
        rows.append(dict(name='JobPayload',kind='union',variants=mapping,discriminator='family',task='P02-04',path=runtime,rules=[]))
        record('JobCommand',dict(schema_version='=2.0.0',kind='JobKind',payload='JobPayload',deadline_utc='UTC'))
        rows.append(dict(name='JobRequest',kind='mapped',base='JobCommand',task='P02-04',path=contracts_runtime,rules=[]))
        record('ScenarioEventSpec',dict(event_id='UUID',effective_at_s='NonNegativeInt'))
        record('ScenarioSpec',dict(schema_version='=2.0.0',event_specs='ScenarioEventSpec[]'))
        record('ScenarioRef',dict(scenario_id='UUID',dataset_version='PositiveInt',schema_version='=2.0.0',content_hash='Sha256'))
        record('ScenarioInput',dict(snapshot='PlanningSnapshot'))
        record('ScenarioBundle',dict(schema_version='=2.0.0',ref='ScenarioRef',spec='ScenarioSpec',input='ScenarioInput',source='=synthetic'))
        data=dict(contract_version='2.0.0',plan_version='1.0.3',decision_round='N01-R01',types=rows,
            module_dependencies={states:[],primitives:[],planning:[],runtime:[states,planning],http:[primitives],contracts_runtime:[runtime]},
            job_kind_mapping=mapping)
        return data,dict(plan_version='1.0.3',tasks=tasks,gates=[])
    def row(self,data,name):return next(r for r in data['types'] if r['name']==name)
    def assert_failure(self,data,manifest,detail):
        self.assertTrue(any(detail in error for error in validate_contract_decisions(data,manifest)),detail)
    def test_closed_contract_graph(self):
        data,manifest=self.fixture();self.assertEqual(validate_contract_decisions(data,manifest),[])
    def test_unknown_referenced_type(self):
        data,manifest=self.fixture();self.row(data,'ScenarioInput')['fields']['missing']='NeverDefined[]?'
        self.assert_failure(data,manifest,'missing referenced type NeverDefined')
    def test_duplicate_definition(self):
        data,manifest=self.fixture();data['types'].append(deepcopy(self.row(data,'RequestRef')))
        self.assert_failure(data,manifest,'duplicate type RequestRef')
    def test_reference_cycle(self):
        data,manifest=self.fixture();self.row(data,'RequestRef')['fields']['parent']='JobCommand'
        self.assert_failure(data,manifest,'type reference cycle')
    def test_wrong_carrier(self):
        data,manifest=self.fixture();self.row(data,'ScenarioInput')['path']='packages/domain/src/logistics_domain/unapproved.py'
        self.assert_failure(data,manifest,'carrier outside definition task whitelist')
    def test_future_definition_task(self):
        data,manifest=self.fixture();planning=self.row(data,'PlanningSnapshot')['path']
        manifest['tasks'].append(dict(id='P06-01',deps=['P05-03'],allowed_files=[planning]))
        self.row(data,'PlanningSnapshot')['task']='P06-01'
        self.assert_failure(data,manifest,'future or unordered type dependency PlanningSnapshot')
    def test_module_cycle(self):
        data,manifest=self.fixture();states=self.row(data,'JobKind')['path'];runtime=self.row(data,'RequestRef')['path']
        data['module_dependencies'][states]=[runtime]
        self.assert_failure(data,manifest,'module dependency cycle')
    def test_domain_cannot_import_contracts(self):
        data,manifest=self.fixture();runtime=self.row(data,'RequestRef')['path'];http=self.row(data,'CalendarDTO')['path']
        data['module_dependencies'][runtime].append(http)
        self.assert_failure(data,manifest,'domain imports non-domain module')
    def test_missing_cross_module_dependency(self):
        data,manifest=self.fixture();runtime=self.row(data,'RequestRef')['path'];data['module_dependencies'][runtime]=[]
        self.assert_failure(data,manifest,'undeclared module dependency')
    def test_missing_optimization_mode(self):
        data,manifest=self.fixture();self.row(data,'JobOptimizationMode')['members'].pop('JOINT')
        self.assert_failure(data,manifest,'transport/warehouse/joint modes required')
    def test_mismatched_kind_mapping(self):
        data,manifest=self.fixture();data['job_kind_mapping']['metric']='SimulationJobPayload'
        self.assert_failure(data,manifest,'JobKind/payload mapping mismatch')
    def test_union_discriminator_must_match_branch(self):
        data,manifest=self.fixture();self.row(data,'JobPayload')['variants']['metric']='SimulationJobPayload'
        self.assert_failure(data,manifest,'discriminator literal does not match metric')
    def test_payload_family_literal_required(self):
        data,manifest=self.fixture();self.row(data,'MetricJobPayload')['fields'].pop('family')
        self.assert_failure(data,manifest,'missing or mismatched family literal')
    def test_request_reference_family_is_unique_enum(self):
        data,manifest=self.fixture();self.row(data,'RequestRef')['fields']['family']='=optimization'
        self.assert_failure(data,manifest,'RequestRef must use the unique JobKind family')
    def test_request_hash_cannot_be_optional(self):
        data,manifest=self.fixture();self.row(data,'RequestRef')['fields']['hash']='Sha256?'
        self.assert_failure(data,manifest,'exact versioned immutable identity required')
    def test_scenario_identity_must_bind_dataset_and_schema(self):
        data,manifest=self.fixture();self.row(data,'ScenarioRef')['fields'].pop('dataset_version')
        self.assert_failure(data,manifest,'exact id/dataset/schema/hash fields required')
    def test_expectation_cannot_leak_transitively(self):
        data,manifest=self.fixture();runtime=self.row(data,'ScenarioInput')['path']
        data['types'].append(dict(name='FixtureExpectations',kind='record',fields=dict(distance='NonNegativeInt'),task='P02-04',path=runtime,rules=[]))
        self.row(data,'ScenarioRef')['fields']['oracle']='FixtureExpectations'
        self.assert_failure(data,manifest,'formal input leaks fixture expectations')
    def test_formal_input_cannot_contain_solver_answer(self):
        data,manifest=self.fixture();runtime=self.row(data,'ScenarioInput')['path']
        data['types'].append(dict(name='CandidatePlan',kind='record',fields=dict(candidate_id='UUID'),task='P02-04',path=runtime,rules=[]))
        self.row(data,'ScenarioInput')['fields']['answer']='CandidatePlan'
        self.assert_failure(data,manifest,'solver answers CandidatePlan')
    def test_direct_expected_scalar_cannot_leak(self):
        data,manifest=self.fixture();runtime=self.row(data,'ScenarioInput')['path']
        data['types'].append(dict(name='ExpectedInteger',kind='record',fields=dict(value='int'),task='P02-04',path=runtime,rules=[]))
        self.row(data,'ScenarioInput')['fields']['hint']='ExpectedInteger'
        self.assert_failure(data,manifest,'formal input leaks fixture expectations')
    def test_calendar_ownership_cannot_move_later(self):
        data,manifest=self.fixture();primitives=self.row(data,'ResourceCalendar')['path']
        manifest['tasks'][1]['allowed_files'].append(primitives);self.row(data,'ResourceCalendar')['task']='P02-03'
        self.assert_failure(data,manifest,'ResourceCalendar: wrong definition task')
    def test_calendar_dto_cannot_define_second_domain_type(self):
        data,manifest=self.fixture();self.row(data,'CalendarDTO')['base']='CalendarInterval'
        self.assert_failure(data,manifest,'CalendarDTO must map shared ResourceCalendar')
    def test_calendar_version_cannot_be_omitted(self):
        data,manifest=self.fixture();self.row(data,'ResourceCalendar')['fields'].pop('version')
        self.assert_failure(data,manifest,'complete epoch/interval/version fields required')
    def test_boundary_extra_field_cannot_hide_a_missing_type(self):
        data,manifest=self.fixture();self.row(data,'CalendarDTO')['extra_fields']['hidden']='UnknownDTO'
        self.assert_failure(data,manifest,'missing referenced type UnknownDTO')
    def test_job_request_cannot_reference_future_dto(self):
        data,manifest=self.fixture();self.row(data,'JobRequest')['base']='TransportRequestDTO'
        self.assert_failure(data,manifest,'JobRequest must map the early JobCommand')
    def test_event_spec_has_one_authority(self):
        data,manifest=self.fixture();self.row(data,'ScenarioInput')['fields']['event_specs']='ScenarioEventSpec[]'
        self.assert_failure(data,manifest,'event specs duplicated outside ScenarioSpec')
    def test_free_dictionary_is_not_a_type(self):
        data,manifest=self.fixture();self.row(data,'ScenarioInput')['fields']['untyped']='dict[str,Any]'
        self.assert_failure(data,manifest,'invalid type expression')
    def test_existing_leaf_requires_evidenced_source(self):
        data,manifest=self.fixture();self.row(data,'PlanningSnapshot')['source']='docs/architecture/DATA_CONTRACTS.md#InventedSection'
        self.assert_failure(data,manifest,'existing source section missing')
    def test_empty_record_is_rejected(self):
        data,manifest=self.fixture();self.row(data,'ScenarioInput')['fields']={}
        self.assert_failure(data,manifest,'empty record is not a complete type')

def run_self_tests():
    suite=unittest.TestSuite(unittest.defaultTestLoader.loadTestsFromTestCase(t) for t in (CheckerTests,ContractDecisionTests))
    output=io.StringIO()
    result=unittest.TextTestRunner(stream=output,verbosity=2).run(suite)
    global SELF_TEST_LOG
    SELF_TEST_LOG=output.getvalue()
    print(SELF_TEST_LOG,file=sys.stderr)
    return result.wasSuccessful(),result.testsRun

def record_g00(data,counts):
    required=[]
    for t in data['tasks']:
        if t['phase']==0:
            required.extend(t['files']);required.append(t['task_doc']);required.append(t['report'])
    missing=[p for p in required if not (ROOT/p).is_file()]
    if missing:raise ValueError('G00 NOT recorded: Phase00 deliverables/reports missing: '+', '.join(missing))
    freeze=json.loads((ROOT/'docs/architecture/CONTRACT_FREEZE.json').read_text(encoding='utf-8'))
    required_contracts={'PROJECT_MASTER_PLAN.md','TASK_GRAPH.md','docs/architecture/ARCHITECTURE_OVERVIEW.md',
        'docs/architecture/DOMAIN_CATALOG.md','docs/architecture/DATA_CONTRACTS.md','docs/architecture/IMPLEMENTATION_CONVENTIONS.md',
        'docs/api/API_CONTRACT.md','docs/algorithms/OPTIMIZATION_CONTRACT.md','docs/algorithms/SIMULATION_CONTRACT.md',
        'docs/algorithms/METRICS_CONTRACT.md','docs/plan/TEST_FIXTURES.md','docs/plan/PHASE_GATES.md'}
    entries=freeze.get('artifacts',[])
    if not required_contracts.issubset({x.get('path') for x in entries}):raise ValueError('G00 NOT recorded: incomplete contract hash coverage')
    if freeze.get('unresolved_blocking_issues')!=[] or not freeze.get('reviewer') or not freeze.get('reviewed_at'):
        raise ValueError('G00 NOT recorded: blocking issues or missing review record')
    inventory=json.loads((ROOT/'docs/architecture/BASELINE_INVENTORY.json').read_text(encoding='utf-8'))
    baseline=inventory.get('entries',[])
    must_have={'demo/README.md','demo/DEV_LOG.md','demo/OWNERSHIP.json','demo/contracts/README.md'}
    if not must_have.issubset({x.get('source_path') for x in baseline}) or not any(x.get('source_path','').startswith('demo/backend/app/contracts/') for x in baseline):
        raise ValueError('G00 NOT recorded: missing legacy baseline coverage')
    for row in entries+[dict(path=x.get('source_path'),sha256=x.get('sha256')) for x in baseline]:
        relative=row.get('path')
        if not isinstance(relative,str):raise ValueError('G00 NOT recorded: invalid artifact path')
        target=(ROOT/relative).resolve()
        if not target.is_relative_to(ROOT) or not target.is_file() or sha(target)!=row.get('sha256'):
            raise ValueError('G00 NOT recorded: artifact hash mismatch '+relative)
    for t in data['tasks']:
        if t['phase']==0:
            report=(ROOT/t['report']).read_text(encoding='utf-8')
            for key in ['Files created','Files modified','Tests added','Commands executed','Test results','Known limitations','Remaining risks']:
                if key not in report:raise ValueError('G00 NOT recorded: incomplete report '+t['id'])
    log=ROOT/'artifacts/gates/G00-checks.log';log.parent.mkdir(parents=True,exist_ok=True)
    log.write_text(SELF_TEST_LOG+'\nArtifact validation:\n'+json.dumps(counts,ensure_ascii=False,indent=2)+'\nerrors=[]\n',encoding='utf-8')
    hashes={p:sha(ROOT/p) for p in required+sorted(required_contracts)}
    evidence=dict(schema_version='1.0.0',gate_id='G00',status='passed',scope='Phase00 document contract verification only',
        finished_at=datetime.now(timezone.utc).isoformat(),checker_counts=counts,
        code_revision='content-sha256:'+hashlib.sha256(json.dumps(hashes,sort_keys=True).encode()).hexdigest(),
        input_artifact_hashes=hashes,dependency_evidence_hashes={},environment_fingerprint=dict(python=platform.python_version(),os=platform.system()),
        commands=[dict(argv=['python','tools/ai_coding_plan/validate_plan.py','--self-test','--record-g00'],cwd=str(ROOT),exit_code=0,log_path='artifacts/gates/G00-checks.log',log_hash=sha(log))],
        reviewer=freeze['reviewer'],
        limitations=['No application gate has been executed. G01 must establish the runtime gate runner.'])
    out=ROOT/'artifacts/gates/G00.json';out.parent.mkdir(parents=True,exist_ok=True);out.write_text(json.dumps(evidence,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print('Recorded Phase00 document evidence:',out)

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--self-test',action='store_true');parser.add_argument('--task');parser.add_argument('--record-g00',action='store_true');parser.add_argument('--write-report',action='store_true')
    args=parser.parse_args();ok=True;test_count=0
    if args.self_test:ok,test_count=run_self_tests()
    data=json.loads((ROOT/'docs/plan/TASK_MANIFEST.json').read_text(encoding='utf-8'))
    report_path=ROOT/'docs/plan/VERIFICATION_REPORT.md'
    # Ensure links can be checked on first report creation, before success is asserted.
    if args.write_report and not report_path.exists():report_path.write_text('# 规划验证报告\n\n检查执行中，尚未通过。\n',encoding='utf-8')
    errors,counts=validate_artifacts(data,args.task)
    if not ok:errors.append('checker self-tests failed')
    if args.record_g00:
        if not args.self_test:errors.append('--record-g00 requires --self-test')
        if not errors:
            try:record_g00(data,counts)
            except (ValueError,TypeError,KeyError) as exc:errors.append(str(exc))
    summary=dict(status='PASS' if not errors else 'FAIL',checker_tests=test_count,**counts,errors=errors)
    if args.write_report:
        content='# 规划验证报告\n\n'+f'日期：2026-09-12。结果：**{summary["status"]}**。仅验证本轮AI-CODING-PLAN文档系统；不是任何应用业务Gate签收。\n\n'
        content+='执行命令：`python tools/ai_coding_plan/validate_plan.py --self-test --write-report`。\n\n'
        content+='| 检查项 | 结果 |\n| --- | --- |\n'
        for name,value in counts.items():content+=f'| {name} | {value} |\n'
        content+=f'| 检查器正反例测试 | {test_count} |\n| 错误 | {len(errors)} |\n\n'
        content+='检查覆盖：任务及Gate DAG无环、依赖存在、Blocks反向一致、严格前阶段Gate、同阶段并行依赖/写文件冲突、14目录和Prompt一对一、24个必需章节、OR-Tools六项算法结构、Files与命令一致、32实体覆盖、需求任务引用、20项Master内容、本地Markdown链接。\n\n'
        content+='所有Task保留planned，G00–G39保留not_run。本次未执行未来pytest/浏览器/数据库/OR-Tools/SimPy/真实LLM/性能测试；未改变旧demo业务代码或外部任务状态。静态通过不能证明算法正确、实际性能或业务可用性，后续必须逐Prompt实现并提交Gate原始证据。\n'
        if errors:content+='\n错误：\n\n'+'\n'.join('- '+e for e in errors)+'\n'
        report_path.write_text(content,encoding='utf-8')
    print(json.dumps(summary,ensure_ascii=False,indent=2))
    return 1 if errors else 0

if __name__=='__main__':sys.exit(main())
