"""Preparation checks only; no solver/PostgreSQL/competition acceptance claim."""
import copy
import hashlib
import json
import sqlite3
import unittest
import uuid
import sys
sys.dont_write_bytecode = True
from build import ROOT, KINDS, canonical, generate, import_sqlite

def check(b):
    rows=b['entities']; ids={r['id'] for r in rows}
    if len(ids)!=len(rows): raise ValueError('duplicate_id')
    for r in rows:
        if uuid.UUID(r['id']).version!=5:raise ValueError('uuid5')
        if r['source']!='synthetic':raise ValueError('source')
        for key in ['weight_g','volume_cm3','duration_s','capacity_weight_g','capacity_volume_cm3']:
            if key in r and (type(r[key]) is not int or r[key]<0):raise ValueError('integer_units')
        if 'min_temp_decic' in r and r['min_temp_decic']>r['max_temp_decic']:raise ValueError('temperature')
        for key,value in r.items():
            if key.endswith('_id') and value not in ids:raise ValueError('dangling_field')
            if key.endswith('_ids') and any(v not in ids for v in value):raise ValueError('dangling_field')
        if 'calendar' in r:
            intervals=r['calendar']['intervals']
            if any(a<0 or a>=z for a,z in intervals):raise ValueError('calendar')
            if any(intervals[i][1]>intervals[i+1][0] for i in range(len(intervals)-1)):raise ValueError('calendar_overlap')
        for requirement in r.get('requirements', []):
            if not requirement['resource_ids'] or any(v not in ids for v in requirement['resource_ids']):
                raise ValueError('dangling_requirement')
            if type(requirement['quantity']) is not int or requirement['quantity'] <= 0:
                raise ValueError('requirement_quantity')
    for e in b['refs']:
        if e['source_id'] not in ids or e['target_id'] not in ids:raise ValueError('dangling_ref')
    by_id={r['id']:r for r in rows}
    def visit(id_,active,done):
        if id_ in active:raise ValueError('dag_cycle')
        if id_ in done:return
        active.add(id_)
        for pred in by_id[id_].get('predecessor_ids',[]):visit(pred,active,done)
        active.remove(id_);done.add(id_)
    done=set()
    for r in rows:visit(r['id'],set(),done)
    for m in b['matrices']:
        n=len(m['node_ids'])
        if len(set(m['node_ids']))!=n or any(x not in ids for x in m['node_ids']):raise ValueError('matrix_nodes')
        if any(len(m[k])!=n or any(len(row)!=n for row in m[k]) for k in ['distance_m','travel_s','connected']):raise ValueError('matrix_shape')
        for i in range(n):
            for j in range(n):
                d,t=m['distance_m'][i][j],m['travel_s'][i][j]
                if m['connected'][i][j]:
                    if type(d) is not int or type(t) is not int or min(d,t)<0:raise ValueError('matrix_units')
                    if i==j and (d!=0 or t!=0):raise ValueError('matrix_diagonal')
                elif d is not None or t is not None:raise ValueError('unreachable_null')
    # Necessary aggregate capacity/temperature checks; not feasibility or optimality proof.
    for s in ['T1','A8','B20']:
        vehicles=[r for r in rows if r['scenario']==s and r['kind']=='Vehicle']
        cargo=[r for r in rows if r['scenario']==s and r['kind']=='Cargo']
        for cold in [True,False]:
            group=[r for r in cargo if (r['min_temp_decic']>=0)==cold]
            eligible=[v for v in vehicles if all(c['min_temp_decic']<=v['setpoint_decic']<=c['max_temp_decic'] for c in group)]
            for dim in ['weight_g','volume_cm3']:
                if sum(c[dim] for c in group)>sum(v['capacity_'+dim] for v in eligible):raise ValueError('aggregate_capacity')
    return True

def t1_replay(b,order=(1,2)):
    m=b['matrices'][0]
    orders=[r for r in b['entities'] if r['scenario']=='T1' and r['kind']=='Order']
    vehicle=next(r for r in b['entities'] if r['scenario']=='T1' and r['kind']=='Vehicle')
    time=0;previous=0;distance=0;driving=0;stops=[]
    for node in order:
        travel=m['travel_s'][previous][node];driving+=travel;time+=travel
        distance+=m['distance_m'][previous][node]
        o=orders[node-1];arrival=time;time=max(time,o['delivery_window'][0])
        if time>o['delivery_window'][1]:raise ValueError('hard_window')
        time+=o['service_s'];stops.append([arrival,time-o['service_s'],time]);previous=node
    driving+=m['travel_s'][previous][0];time+=m['travel_s'][previous][0];distance+=m['distance_m'][previous][0]
    return dict(distance_m=distance,return_s=time,drive_s=driving,stops=stops,cost_cents=distance*vehicle['rate_cents_per_km']//1000+vehicle['fixed_cost_cents'])

class PreparationTests(unittest.TestCase):
    def setUp(self):self.b=generate()
    def test_deterministic_and_generated_json(self):
        self.assertEqual(canonical(self.b),canonical(generate()))
        self.assertEqual(self.b,json.loads((ROOT/'generated/bundle.json').read_text(encoding='utf-8')))
    def test_integrity(self):self.assertTrue(check(self.b))
    def test_counts_and_five_operation_chains(self):
        for s,n in [('T1',2),('A8',8),('B20',20)]:
            self.assertEqual(sum(r['scenario']==s and r['kind']=='Order' for r in self.b['entities']),n)
        rows=self.b['entities']; tasks=[r for r in rows if r['kind']=='WarehouseTask']
        self.assertEqual(len(tasks),100)
        for order in [r for r in rows if r['scenario']=='B20' and r['kind']=='Order']:
            chain=[r for r in tasks if r['order_id']==order['id']]
            self.assertEqual([r['preparation_operation'] for r in chain],['unload','receive','sort','dispatch','load'])
            self.assertEqual([r['duration_s'] for r in chain],[60,30,60,30,60])
            self.assertEqual(chain[0]['predecessor_ids'],[])
            for i in range(1,5):self.assertEqual(chain[i]['predecessor_ids'],[chain[i-1]['id']])
        self.assertEqual(len(KINDS),32)
        self.assertTrue(all(not x for x in self.b['runtime'].values()))
    def test_initial_stock_no_double_count(self):
        stock=[r for r in self.b['entities'] if r['kind']=='InitialStock' and r['scenario']=='B20']
        arrivals=[r for r in self.b['entities'] if r['kind']=='ExternalArrival']
        self.assertEqual(sum(r['quantity_units'] for r in stock),0)
        self.assertEqual(sum(r['quantity_units'] for r in arrivals),20)
    def test_t1_hand_replay(self):
        self.assertEqual(t1_replay(self.b),dict(distance_m=9000,return_s=1020,drive_s=900,stops=[[300,300,360],[560,560,620]],cost_cents=1400))
        with self.assertRaisesRegex(ValueError,'hard_window'):t1_replay(self.b,(2,1))
    def test_t1_wait_variant(self):
        orders=[r for r in self.b['entities'] if r['scenario']=='T1' and r['kind']=='Order']
        orders[0]['delivery_window']=[350,350]
        self.assertEqual(t1_replay(self.b)['return_s'],1070)
        self.assertEqual(t1_replay(self.b)['stops'],[[300,350,410],[610,610,670]])
        orders[1]['delivery_window']=[0,600]
        with self.assertRaisesRegex(ValueError,'hard_window'):t1_replay(self.b)
    def test_reject_weight_and_volume_capacity(self):
        for dim,cap in [('capacity_weight_g',799999),('capacity_volume_cm3',1999999)]:
            b=copy.deepcopy(self.b);v=next(r for r in b['entities'] if r['scenario']=='T1' and r['kind']=='Vehicle');v[dim]=cap
            with self.assertRaisesRegex(ValueError,'aggregate_capacity'):check(b)
    def test_reject_bad_temperature(self):
        c=next(r for r in self.b['entities'] if r['kind']=='Cargo');c['min_temp_decic']=81
        with self.assertRaisesRegex(ValueError,'temperature'):check(self.b)
    def test_reject_dangling_reference(self):
        self.b['refs'][0]['target_id']='missing'
        with self.assertRaisesRegex(ValueError,'dangling_ref'):check(self.b)
    def test_reject_cycle(self):
        t=next(r for r in self.b['entities'] if r['kind']=='WarehouseTask');t['predecessor_ids']=[t['id']]
        with self.assertRaisesRegex(ValueError,'dag_cycle'):check(self.b)
    def test_reject_matrix_shape(self):
        self.b['matrices'][0]['travel_s'][0].pop()
        with self.assertRaisesRegex(ValueError,'matrix_shape'):check(self.b)
    def test_unreachable_requires_null(self):
        self.b['matrices'][0]['connected'][0][1]=False
        with self.assertRaisesRegex(ValueError,'unreachable_null'):check(self.b)
    def test_w1_arithmetic_and_half_open_inventory(self):
        w=json.loads((ROOT/'generated/W1.json').read_text(encoding='utf-8'))
        durations=sum(t['duration_s'] for t in w['tasks'])
        self.assertEqual(durations,20);self.assertEqual(durations+w['setup']['duration_s'],25)
        stock=w['inventory_case']
        def occupied(t):return (8 if 0<=t<20 else 0)+(3 if t>=10 else 0)
        self.assertGreater(occupied(10)*stock['unit_weight_g'],stock['capacity_weight_g'])
        self.assertLessEqual(3*stock['unit_weight_g'],stock['capacity_weight_g'])
    def test_sqlite_roundtrip_and_idempotence(self):
        with sqlite3.connect(':memory:') as c:
            import_sqlite(c,self.b)
            first=c.execute('SELECT * FROM entities ORDER BY id').fetchall()
            refs=c.execute('SELECT * FROM refs ORDER BY source_id,relation,target_id').fetchall()
            self.assertEqual(import_sqlite(c,self.b), 0)
            self.assertEqual(first,c.execute('SELECT * FROM entities ORDER BY id').fetchall())
            self.assertEqual(refs,c.execute('SELECT * FROM refs ORDER BY source_id,relation,target_id').fetchall())
            self.assertEqual(len(first),len(self.b['entities']))
            self.assertEqual({r[0]:json.loads(r[5]) for r in first},{r['id']:r for r in self.b['entities']})
        with sqlite3.connect(f'file:{ROOT / "generated/preview.sqlite3"}?mode=ro',uri=True) as c:
            self.assertEqual(c.execute('PRAGMA integrity_check').fetchone()[0],'ok')
            self.assertEqual(c.execute('PRAGMA foreign_key_check').fetchall(),[])
            self.assertEqual(c.execute('SELECT count(*) FROM entities').fetchone()[0],len(first))
    def test_sqlite_invalid_fk_rolls_back(self):
        b=copy.deepcopy(self.b);b['refs'][0]['target_id']='missing'
        with sqlite3.connect(':memory:') as c:
            with self.assertRaises(sqlite3.IntegrityError):import_sqlite(c,b)
            self.assertEqual(c.execute('SELECT count(*) FROM entities').fetchone()[0],0)
    def test_sqlite_conflicting_reimport_rejected(self):
        with sqlite3.connect(':memory:') as c:
            import_sqlite(c,self.b)
            original=c.execute('SELECT * FROM entities ORDER BY id').fetchall()
            b=copy.deepcopy(self.b)
            b['entities'][-1]['service_s']=999
            with self.assertRaisesRegex(ValueError,'existing_entity_conflict'):
                import_sqlite(c,b)
            self.assertEqual(original,c.execute('SELECT * FROM entities ORDER BY id').fetchall())
    def test_nested_resource_reference_rejected(self):
        task=next(r for r in self.b['entities'] if r['kind']=='WarehouseTask')
        task['requirements'][0]['resource_ids']=['missing']
        with self.assertRaisesRegex(ValueError,'dangling_requirement'):check(self.b)
    def test_manifest(self):
        manifest=json.loads((ROOT/'manifest.json').read_text(encoding='utf-8'))
        for path,expected in manifest['files'].items():
            self.assertEqual(hashlib.sha256((ROOT/path).read_bytes()).hexdigest(),expected,path)

if __name__=='__main__':unittest.main(verbosity=2)
