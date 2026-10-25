"""Independent synthetic preparation data; no production DTO or migration imports."""
import csv
import hashlib
import json
from pathlib import Path
import sqlite3
import uuid

ROOT = Path(__file__).resolve().parent
EPOCH = '2026-09-12T00:00:00Z'
NAMESPACE = uuid.UUID('6f981297-f4aa-5031-a136-a97377c931bc')
KINDS = 'Order Cargo Vehicle Driver Warehouse WarehouseZone StorageLocation Dock Worker Equipment TransportTask WarehouseTask Route RouteStop Schedule ScheduleTask ScheduleVersion Constraint OptimizationRequest OptimizationResult Simulation SimulationSnapshot Event ExceptionEvent RescheduleRequest RescheduleResult AgentRun ToolCall DecisionRecord Experiment Metric ExperimentResult'.split()
SCHEMA = '''CREATE TABLE IF NOT EXISTS entities (
 id TEXT PRIMARY KEY, scenario TEXT NOT NULL, kind TEXT NOT NULL, code TEXT NOT NULL,
 source TEXT NOT NULL CHECK(source='synthetic'), payload TEXT NOT NULL,
 UNIQUE(scenario,kind,code));
CREATE TABLE IF NOT EXISTS refs (
 source_id TEXT NOT NULL REFERENCES entities(id), relation TEXT NOT NULL,
 target_id TEXT NOT NULL REFERENCES entities(id),
 PRIMARY KEY(source_id,relation,target_id));'''

def uid(scenario, kind, code):
    return str(uuid.uuid5(NAMESPACE, f'{scenario}/{kind}/{code}'))

def canonical(obj):
    return json.dumps(obj, ensure_ascii=False, sort_keys=True, separators=(',', ':'))

def generate():
    rows, refs, matrices = [], [], []
    def add(s, kind, code, **data):
        row = dict(id=uid(s, kind, code), scenario=s, kind=kind, code=code,
                   source='synthetic', schema_version='preparation-v1', **data)
        rows.append(row)
        return row['id']
    def edge(a, rel, b):
        refs.append(dict(source_id=a, relation=rel, target_id=b))
    for s, count, depots, horizon in [('T1', 2, 1, 3600), ('A8', 8, 1, 28800), ('B20', 20, 2, 28800)]:
        nodes, xy, depot_resources = [], [], []
        def calendar():
            return dict(epoch_utc=EPOCH, version=0, intervals=[[0, horizon]])
        for d in range(depots):
            n = add(s, 'Node', f'D{d+1}', x=d*10, y=0, coordinate_system='synthetic_grid')
            nodes.append(n); xy.append((d*10, 0))
            wh = add(s, 'Warehouse', f'H{d+1}', node_id=n, timezone='UTC', calendar=calendar())
            edge(wh, 'LOCATED_AT', n)
            zones = []
            for z, temp in enumerate([40] if s == 'T1' else [40, -200]):
                zone = add(s, 'WarehouseZone', f'H{d+1}Z{z+1}', warehouse_id=wh, setpoint_decic=temp,
                           capacity_weight_g=2000000, capacity_volume_cm3=20000000, cargo_type_mapping='pending')
                loc = add(s, 'StorageLocation', f'H{d+1}L{z+1}', zone_id=zone,
                          capacity_weight_g=2000000, capacity_volume_cm3=20000000, calendar=calendar())
                edge(zone, 'IN_WAREHOUSE', wh); edge(loc, 'IN_ZONE', zone)
                zones.append((zone, loc))
            dock = add(s, 'Dock', f'H{d+1}D', warehouse_id=wh, capacity=1, initial_setup_class='40',
                       setup_duration_s=30 if s == 'B20' else 0, calendar=calendar())
            edge(dock, 'IN_WAREHOUSE', wh)
            workers = []
            for w in range(2):
                worker = add(s, 'Worker', f'H{d+1}W{w+1}', warehouse_id=wh, skills_mapping='pending', calendar=calendar())
                workers.append(worker); edge(worker, 'IN_WAREHOUSE', wh)
            equipment = {}
            for kind in ['sorting', 'handling']:
                eq = add(s, 'Equipment', f'H{d+1}{kind}', warehouse_id=wh, preparation_kind=kind,
                         equipment_kind_mapping='pending', quantity_capacity=1, calendar=calendar())
                equipment[kind] = eq; edge(eq, 'IN_WAREHOUSE', wh)
            for v, temp in enumerate([40] if s == 'T1' else [40, -200]):
                driver = add(s, 'Driver', f'H{d+1}S{v+1}', shift=[0,horizon], max_drive_s=horizon,
                             max_work_s=horizon, qualifications_mapping='pending')
                vehicle = add(s, 'Vehicle', f'H{d+1}V{v+1}', start_node_id=n, end_node_id=n, driver_id=driver,
                              capacity_weight_g=800000 if s=='T1' else 1000000,
                              capacity_volume_cm3=2000000 if s=='T1' else 10000000, setpoint_decic=temp,
                              calendar=calendar(), fixed_cost_cents=500, rate_cents_per_km=100, single_trip=True,
                              allowed_cargo_types_mapping='pending')
                edge(vehicle, 'DRIVEN_BY', driver); edge(vehicle, 'STARTS_AT', n); edge(vehicle, 'ENDS_AT', n)
            depot_resources.append((n, wh, zones, dock, workers, equipment))
        for i in range(count):
            x, y = i%5+1, i//5+1
            node = add(s, 'Node', f'C{i+1}', x=x, y=y, coordinate_system='synthetic_grid')
            nodes.append(node); xy.append((x,y))
            d = i//10 if s == 'B20' else 0
            chilled = s == 'T1' or (i < 4 if s == 'A8' else i%10 < 5)
            origin, wh, zones, dock, workers, equipment = depot_resources[d]
            zone, loc = zones[0 if chilled else 1]
            order_id, cargo_id = uid(s,'Order',f'O{i+1}'), uid(s,'Cargo',f'C{i+1}')
            add(s, 'Order', f'O{i+1}', pickup_node_id=origin, delivery_node_id=node, cargo_ids=[cargo_id],
                pickup_window=[0,horizon], delivery_window=[0, (600 if i==0 else 1200) if s=='T1' else 24000],
                soft_due_at_s=(360 if i==0 else 620) if s=='T1' else 20000, service_s=60, must_serve=True)
            add(s, 'Cargo', f'C{i+1}', order_id=order_id, quantity_units=1, weight_g=400000 if s=='T1' else 100000,
                volume_cm3=1000000, min_temp_decic=20 if chilled else -250, max_temp_decic=80 if chilled else -180,
                cargo_type_mapping='pending', max_exposure_s=120, batch_ref=f'{s}-synthetic-{i+1}')
            edge(order_id,'PICKUP_AT',origin); edge(order_id,'DELIVERY_AT',node); edge(cargo_id,'BELONGS_TO',order_id)
            initial = add(s,'InitialStock',f'I{i+1}', cargo_id=cargo_id, location_id=loc,
                          quantity_units=0 if s=='B20' else 1, weight_g=0 if s=='B20' else (400000 if s=='T1' else 100000),
                          volume_cm3=0 if s=='B20' else 1000000, as_of_s=0,
                          boundary='before_departure', outbound_completed_before_epoch=s!='B20')
            edge(initial,'STOCK_OF',cargo_id); edge(initial,'AT_LOCATION',loc)
            previous = []
            if s == 'B20':
                ext = add(s,'ExternalArrival',f'E{i+1}', cargo_id=cargo_id, arrival_s=0, quantity_units=1,
                          weight_g=100000, volume_cm3=1000000, warehouse_id=wh)
                edge(ext,'SUPPLIES',cargo_id); edge(ext,'ARRIVES_AT',wh)
                for op, duration in [('unload',60),('receive',30),('sort',60),('dispatch',30),('load',60)]:
                    req = [dict(resource_ids=workers, selection='choose_one', quantity=1)]
                    if op in ['unload','load']:
                        req += [dict(resource_ids=[dock],quantity=1), dict(resource_ids=[equipment['handling']],quantity=1)]
                    if op=='sort': req += [dict(resource_ids=[equipment['sorting']],quantity=1)]
                    task = add(s,'WarehouseTask',f'O{i+1}-{op}', order_id=order_id, warehouse_id=wh, cargo_id=cargo_id,
                               preparation_operation=op, duration_s=duration, window=[0,24000], predecessor_ids=previous,
                               requirements=req, setup_class='40' if chilled else '-200', inventory_location_id=loc)
                    edge(task,'FOR_ORDER',order_id); edge(task,'IN_WAREHOUSE',wh); edge(task,'USES_LOCATION',loc)
                    for requirement in req:
                        for resource in requirement['resource_ids']: edge(task,'ELIGIBLE_RESOURCE',resource)
                    for pred in previous: edge(task,'DEPENDS_ON',pred)
                    previous=[task]
            task=add(s,'TransportTask',f'T{i+1}', order_id=order_id, leg_no=1, pickup_node_id=origin,
                     delivery_node_id=node,cargo_ids=[cargo_id],predecessor_ids=previous,service_s=60)
            edge(task,'FOR_ORDER',order_id)
            for pred in previous: edge(task,'DEPENDS_ON',pred)
        distance = [[1000*(abs(a[0]-b[0])+abs(a[1]-b[1])) for b in xy] for a in xy]
        travel = [[(d+9)//10 for d in row] for row in distance]
        if s=='T1':
            distance=[[0,3000,7000],[5000,0,2000],[4000,6000,0]]
            travel=[[0,300,700],[500,0,200],[400,600,0]]
        matrices.append(dict(scenario=s,node_ids=nodes,distance_m=distance,travel_s=travel,version='synthetic-v1',
                             connected=[[True for _ in nodes] for _ in nodes], model='fixture_asymmetric' if s=='T1' else 'synthetic_manhattan_10m_per_s'))
    return dict(schema_version='preparation-v1',source='synthetic',seed=42,epoch_utc=EPOCH,
                units=dict(time='s',distance='m',weight='g',volume='cm3',money='CNY_cent',temperature='decic'),
                entities=rows,refs=refs,matrices=matrices,runtime={kind:[] for kind in KINDS[12:]})

def import_sqlite(conn, bundle):
    conn.execute('PRAGMA foreign_keys=ON')
    conn.executescript(SCHEMA)
    before=conn.total_changes
    with conn:
        for r in bundle['entities']:
            values = (r['id'],r['scenario'],r['kind'],r['code'],r['source'],canonical(r))
            existing = conn.execute('SELECT * FROM entities WHERE id=?', (r['id'],)).fetchone()
            if existing is not None and existing != values:
                raise ValueError('existing_entity_conflict')
            conn.execute('INSERT INTO entities VALUES(?,?,?,?,?,?) ON CONFLICT(id) DO NOTHING', values)
        for r in bundle['refs']:
            conn.execute('INSERT INTO refs VALUES(?,?,?) ON CONFLICT DO NOTHING',tuple(r[k] for k in ['source_id','relation','target_id']))
    return conn.total_changes-before

def write_json(path, obj):
    path.write_text(json.dumps(obj,ensure_ascii=False,sort_keys=True,indent=2)+'\n',encoding='utf-8')

def write_csv(path, rows, fields):
    with path.open('w',newline='',encoding='utf-8') as f:
        writer=csv.DictWriter(f,fieldnames=fields);writer.writeheader()
        for row in rows:
            writer.writerow({k:canonical(row[k]) if isinstance(row[k],(dict,list)) else row[k] for k in fields})

def build():
    b=generate(); out=ROOT/'generated';out.mkdir(exist_ok=True)
    write_json(out/'bundle.json',b)
    write_csv(out/'entities.csv',[dict(id=r['id'],scenario=r['scenario'],kind=r['kind'],code=r['code'],source=r['source'],payload=r) for r in b['entities']],['id','scenario','kind','code','source','payload'])
    write_csv(out/'graph_nodes.csv',[dict(id=r['id'],scenario=r['scenario'],kind=r['kind'],code=r['code']) for r in b['entities']],['id','scenario','kind','code'])
    write_csv(out/'graph_edges.csv',b['refs'],['source_id','relation','target_id'])
    for kind in KINDS:
        records=[r for r in b['entities'] if r['kind']==kind]
        write_json(out/f'{kind}.json',records)
    with sqlite3.connect(out/'preview.sqlite3') as conn:
        import_sqlite(conn,b)
        for kind in KINDS:
            conn.execute(f'CREATE VIEW IF NOT EXISTS "{kind}" AS SELECT * FROM entities WHERE kind=\'{kind}\'')
    sql=["-- Preparation staging only; NOT production migrations. PostgreSQL execution NOT VERIFIED.", 'BEGIN;', 'CREATE SCHEMA IF NOT EXISTS competition_preparation;', 'SET LOCAL search_path=competition_preparation;',SCHEMA.replace('payload TEXT','payload JSONB').replace('id TEXT PRIMARY KEY','id UUID PRIMARY KEY').replace('source_id TEXT','source_id UUID').replace('target_id TEXT','target_id UUID')]
    sql.insert(2, "DO $$ BEGIN IF current_database() <> 'logistics_prep_test' THEN RAISE EXCEPTION 'Preparation import requires isolated logistics_prep_test database'; END IF; END $$;")
    def quote(v):return "'"+v.replace("'","''")+"'"
    for r in b['entities']:
        sql.append('INSERT INTO entities VALUES('+','.join(quote(v) for v in [r['id'],r['scenario'],r['kind'],r['code'],r['source'],canonical(r)])+') ON CONFLICT(id) DO UPDATE SET payload=CASE WHEN entities.payload=excluded.payload AND entities.scenario=excluded.scenario AND entities.kind=excluded.kind AND entities.code=excluded.code AND entities.source=excluded.source THEN entities.payload ELSE NULL END;')
    for r in b['refs']:
        sql.append('INSERT INTO refs VALUES('+','.join(quote(r[k]) for k in ['source_id','relation','target_id'])+') ON CONFLICT DO NOTHING;')
    sql.append('COMMIT;');(out/'postgres_staging.sql').write_text('\n'.join(sql)+'\n',encoding='utf-8')
    write_json(out/'W1.json',dict(source='synthetic',schema_version='preparation-v1',epoch_utc=EPOCH,
        warehouse='H1',setpoint_decic=40,window=[0,100],dock_capacity=1,worker_capacity=2,
        equipment=[dict(code='E1',kind='sorting',capacity=1),dict(code='E2',kind='handling',capacity=1)],
        tasks=[dict(code='A',duration_s=10,predecessors=[],setup_class='raw',dock_units=1,worker_units=1),dict(code='B',duration_s=10,predecessors=['A'],setup_class='clean',dock_units=1,worker_units=1)],
        setup=dict(from_class='raw',to_class='clean',duration_s=5,dock_units=1,worker_units=1),
        inventory_case=dict(capacity_weight_g=10000,capacity_volume_cm3=10000,initial_quantity=8,unit_weight_g=1000,unit_volume_cm3=1000,initial_interval=[0,20],new_quantity=3,invalid_arrival_s=10,valid_arrival_s=20),
        oracle_only=dict(with_setup_makespan_s=25,without_setup_makespan_s=20),not_a_solver_result=True))
    write_json(out/'event_templates.json',dict(source='synthetic',status='template_not_occurred',base_scenario='B20',
        prerequisites=['independently validated and committed B schedule','actual execution snapshot','branch per experiment'],
        templates=[dict(code='C1',trigger='selected actual departure + 150 seconds',kind='vehicle_failure',required=['actual position','remaining cargo','explicit rescue vehicle and driver','rescue travel matrix','transfer 60s','exposure <=120s'],missing_data_outcome='MANUAL_REQUIRED'),
        dict(code='C2',trigger=['before target load','actual departure + 150 seconds'],kind='order_cancel',required=['return or explicit disposal for in-transit cargo','preserve delivered history']),
        dict(code='C3',trigger='first actual departure with future arcs',kind='weather',multiplier_numerator=3,multiplier_denominator=2,rounding='ceil',required=['new matrix version','preserve distance and travelled arc facts'])]))
    coverage=[]
    for k in KINDS:
        count=sum(r['kind']==k for r in b['entities'])
        coverage.append(dict(entity=k,rows=count,state='input_preparation_mapping_pending' if count else 'empty_not_executed',producer='preparation generator' if count else 'future validated application/solver/simulator/agent/evaluation service'))
    write_json(out/'entity_coverage.json',coverage)
    (out/'graph_import.cypher').write_text('// Optional Neo4j input projection; not executed or required by current architecture.\n// Copy graph CSV files to the configured Neo4j import directory.\nCREATE CONSTRAINT prep_node_id IF NOT EXISTS FOR (n:PreparationNode) REQUIRE n.id IS UNIQUE;\nLOAD CSV WITH HEADERS FROM "file:///graph_nodes.csv" AS row MERGE (n:PreparationNode {id: row.id}) SET n.scenario=row.scenario,n.kind=row.kind,n.code=row.code,n.source="synthetic";\nLOAD CSV WITH HEADERS FROM "file:///graph_edges.csv" AS row MATCH (a:PreparationNode {id:row.source_id}), (b:PreparationNode {id:row.target_id}) MERGE (a)-[r:INPUT_RELATION {kind:row.relation}]->(b);\n',encoding='utf-8')
    write_manifest()
    print(canonical(dict(entities=len(b['entities']),references=len(b['refs']),scenarios=['T1','A8','B20'],postgres_executed=False)))

def write_manifest():
    files={str(p.relative_to(ROOT)).replace('\\','/'):hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(ROOT.rglob('*')) if p.is_file() and p.name!='manifest.json' and '__pycache__' not in p.parts}
    write_json(ROOT/'manifest.json',dict(schema_version='preparation-manifest-v1',files=files,source='synthetic'))

if __name__=='__main__':build()
