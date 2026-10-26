import json
from pathlib import Path
import pytest
from app.contracts.entities import PlanningSnapshot
from app.application.coordinator import coordinate
from app.evaluation.metrics import planned_metrics, union_seconds, task_change_metrics
from app.evaluation.experiment import run_paired, paired_summary

@pytest.fixture(scope="module")
def inputs():
    root = Path(__file__).resolve().parents[3]
    snap = PlanningSnapshot.model_validate(json.loads((root/'data/scenarios/prep_T1.json').read_text(encoding='utf-8')))
    plan = coordinate(snapshot=snap,order_ids=tuple(o.order_id for o in snap.orders),budget_ms=100,max_coordination_rounds=1,coordination_mode='sequential')
    return snap,plan

def test_planned_t1_and_missing(inputs):
    snap,plan=inputs
    values=planned_metrics(snap,plan,window_start=0,window_end=3600,scope_id='T1')
    assert len(values)==14
    assert values['demand_satisfaction'].value==1
    assert values['on_time_rate'].value==1
    assert values['mean_delay'].value==0
    assert values['transport_distance'].value==9000
    assert values['solve_time'].value is None
    assert values['transport_cost'].missing_reason=='MISSING_REQUIRED_OBSERVATION'
    assert values['warehouse_utilization'].value is None

def test_scope_mismatch(inputs):
    snap,plan=inputs
    with pytest.raises(ValueError,match='snapshot_version'):
        planned_metrics(snap,plan.model_copy(update={'snapshot_version':2}),window_start=0,window_end=3600,scope_id='T1')

def test_partial_window(inputs):
    snap,plan=inputs
    with pytest.raises(ValueError,match='partial_plan'):
        planned_metrics(snap,plan,window_start=0,window_end=100,scope_id='T1')

def test_duplicate_delivery(inputs):
    snap,plan=inputs
    route=plan.routing.routes[0]
    routing=plan.routing.model_copy(update={'routes':(route,route)})
    with pytest.raises(ValueError,match='duplicate_delivery'):
        planned_metrics(snap,plan.model_copy(update={'routing':routing}),window_start=0,window_end=3600,scope_id='T1')

@pytest.mark.parametrize('intervals,expected',[([(0,60),(30,90)],90),([(0,10),(10,20)],20),([(-10,10),(90,120)],20),([],0)])
def test_interval_union(intervals,expected):
    assert union_seconds(intervals,0,100)==expected

def test_interval_reversed():
    with pytest.raises(ValueError): union_seconds([(2,1)],0,100)

def test_disturbance_oracle():
    old={str(i):( ('r1',),0,None) for i in range(4)}
    new={**old,'0':(('r2',),0,None)}
    result=task_change_metrics(old,new)
    assert result['changed_tasks']==1
    assert result['disturbance']==pytest.approx(.1)
    with pytest.raises(ValueError,match='completed_fact'):
        task_change_metrics(old,new,completed_ids=['0'])

def test_membership_and_empty():
    assert task_change_metrics({}, {})['disturbance']==0
    result=task_change_metrics({}, {'a':(('r1',),0,None)})
    assert result['changed_tasks']==1 and result['disturbance']==.1

def test_experiment_failure_and_success_retained(inputs,tmp_path):
    snap,plan=inputs
    def success(snapshot,seed,budget): return plan
    def failed(snapshot,seed,budget): raise RuntimeError('controlled failure')
    rows=run_paired(snap,{'good':success,'bad':failed},range(10),1000,tmp_path/'run')
    assert len(rows)==20
    assert sum(r['status']=='failed' for r in rows)==10
    assert len((tmp_path/'run/runs.jsonl').read_text().splitlines())==20
    summary=paired_summary(rows,'good','bad','transport_distance')
    assert summary['complete_pairs']==0 and summary['mean_paired_difference'] is None
    with pytest.raises(FileExistsError):
        run_paired(snap,{'a':success,'b':success},range(10),1000,tmp_path/'run')

def test_experiment_pairing(inputs,tmp_path):
    snap,plan=inputs
    def same(snapshot,seed,budget): return plan
    rows=run_paired(snap,{'a':same,'b':same},range(10),1000,tmp_path/'paired')
    result=paired_summary(rows,'a','b','transport_distance')
    assert result['complete_pairs']==10
    assert result['bootstrap_ci95']==[0,0]
    rows[0]['metrics']['transport_distance']['source']='actual'
    with pytest.raises(ValueError,match='INCOMPARABLE'):
        paired_summary(rows,'a','b','transport_distance')


def test_volume_utilization_oracle():
    from app.evaluation.metrics import capacity_utilization
    result=capacity_utilization([('zone',0,10,100)],[('zone',0,10,200)],window_start=0,window_end=10)
    assert result['value']==.5
    assert result['numerator']==1000
    assert capacity_utilization([],[],window_start=0,window_end=10)['value'] is None
    with pytest.raises(ValueError,match='capacity_exceeded'):
        capacity_utilization([('zone',0,10,201)],[('zone',0,10,200)],window_start=0,window_end=10)
    with pytest.raises(ValueError,match='overlapping_capacity'):
        capacity_utilization([],[('zone',0,10,200),('zone',5,10,200)],window_start=0,window_end=10)
