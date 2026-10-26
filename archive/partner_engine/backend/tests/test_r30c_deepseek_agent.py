"""R30-C focused tests: simulated provider, local access and no SQL/commit tools.
Actual external API, PostgreSQL and OR-Tools require Windows on-device acceptance.
"""
from __future__ import annotations
import json
from copy import deepcopy
from unittest.mock import patch
import httpx
from fastapi.testclient import TestClient
from app.main import app
from app.api.routes import agent_demo
from app.adapters.llm.gateway import DeepSeekGateway, ModelUnavailable

cli = TestClient(app)
PATH = '/local-pg/pg-preview/r30c'


def fake_workflow():
    return {'mode': 'r28_reconciled_dry_run_not_executable', 'source': 'scenario_demo',
        'validated': True, 'database_mutated': False, 'business_plans_mutated': False,
        'snapshot': {'warehouses':[{'warehouse_id':'wh_1'}],
                     'vehicles':[{'vehicle_id':'veh_1'}, {'vehicle_id':'veh_2'}],
                     'resources':[{'resource_id':'res_dock1'}], 'stock_lots':[{'batch_id':'batch_001'}],
                     'orders':[{'order_id':'ord_001','batch_id':'batch_001'}],
                     'operations':[{'operation_id':'op_001','order_ids':['ord_001']}]},
        'plan': {'validation':{'status':'passed'},
                 'warehouse':{'operations':[{'operation_id':'op_001','resource_id':'res_dock1','start_s':20}],
                              'warehouse_handoffs':[]},
                 'routing':{'routes':[{'vehicle_id':'veh_2','stops':[
                     {'departure_at_s':100, 'arrival_at_s':100},
                     {'departure_at_s':300,'arrival_at_s':250}]}]}},
        'reconciliation':{'status':'passed','scope_order_count':1,'planned_delivery_order_count':1,'unserved_order_count':0}}


def fake_exception():
    return {'database_mutated':False,'business_plans_mutated':False,
            'verification':{'status':'passed','baseline_r28':'passed','suffix_accounting':'passed'},
            'event':{'event_type':'vehicle_breakdown','object_id':'veh_2','occurred_at_s':175},
            'comparison':{'delivered_before_event':0,'forecast_delivered_total':0,'unserved_total':1,
                          'unserved_orders':[{'order_id':'ord_001','reason_code':'stranded'}],
                          'changed_vehicle_ids':['veh_2'],'changed_warehouse_operations':[], 'warnings':[]},
            'baseline':fake_workflow()}


def test_enabled_only_local(monkeypatch):
    monkeypatch.delenv('PG_DEMO_ENABLED', raising=False)
    assert cli.get(PATH+'/status').status_code==503
    monkeypatch.setenv('PG_DEMO_ENABLED','1')
    monkeypatch.delenv('DEEPSEEK_API_KEY',raising=False)
    r=cli.get(PATH+'/status')
    assert r.status_code==200
    assert r.json()['configured'] is False
    assert 'api_key' not in r.text.lower()


def test_chat_key_required(monkeypatch):
    monkeypatch.setenv('PG_DEMO_ENABLED','1')
    monkeypatch.delenv('DEEPSEEK_API_KEY',raising=False)
    r=cli.post(PATH+'/chat',json={'message':'请调度20单'})
    assert r.status_code==503 and 'deepseek_key_not_configured' in r.text


def test_safe_demo_status_without_real_database(monkeypatch):
    monkeypatch.setenv('PG_DEMO_ENABLED','1')
    r=cli.post(PATH+'/quick',json={'action':'get_business_status'})
    assert r.status_code==200
    assert r.json()['mode']=='direct_algorithm_fallback_not_ai'
    assert r.json()['calls'][0]['orders']==20
    assert r.json()['calls'][0]['has_executed_solver'] is False


def test_dispatch_validated_only(monkeypatch):
    monkeypatch.setenv('PG_DEMO_ENABLED','1')
    with patch.object(agent_demo.pg,'r27_workflow',return_value=fake_workflow()):
        r=cli.post(PATH+'/quick',json={'action':'generate_joint_plan'})
    assert r.status_code==200
    assert r.json()['calls'][0]['status']=='verified_readonly'
    assert r.json()['artifact']['kind']=='workflow'
    invalid=fake_workflow();invalid['reconciliation']['status']='failed'
    with patch.object(agent_demo.pg,'r27_workflow',return_value=invalid):
        r=cli.post(PATH+'/quick',json={'action':'generate_joint_plan'})
    assert r.status_code==422


def test_exception_uses_real_vehicle_and_safe_time(monkeypatch):
    monkeypatch.setenv('PG_DEMO_ENABLED','1')
    with patch.object(agent_demo.pg,'r27_workflow',return_value=fake_workflow()), \
         patch('app.adapters.persistence.pg_r30b_reschedule.run_reschedule',return_value=fake_exception()) as runner:
        r=cli.post(PATH+'/quick',json={'action':'simulate_exception','object_id':'V002'})
    assert r.status_code==200
    assert r.json()['calls'][0]['unserved_total']==1
    assert runner.call_args.kwargs['spec'].object_id=='veh_2'
    assert runner.call_args.kwargs['spec'].occurred_at_s==175
    assert r.json()['artifact']['kind']=='exception'


def test_model_only_has_three_read_only_tools():
    assert {tool['function']['name'] for tool in agent_demo.TOOLS}=={
        'get_business_status', 'generate_joint_plan', 'simulate_exception'}
    assert 'execute_sql' not in json.dumps(agent_demo.TOOLS)


def test_gateway_mock_provider_no_key_in_error(monkeypatch):
    monkeypatch.setenv('DEEPSEEK_API_KEY','top-secret-test-only')
    monkeypatch.setenv('DEEPSEEK_BASE_URL','https://api.deepseek.com')
    request_bodies=[]
    def handler(req):
        request_bodies.append(json.loads(req.content))
        return httpx.Response(200,json={'choices':[{'message':{'role':'assistant','content':'工具调用成功'}}]})
    with httpx.Client(transport=httpx.MockTransport(handler)) as http:
        gateway=DeepSeekGateway(client=http)
        answer=gateway.complete([{'role':'user','content':'测试'}],agent_demo.TOOLS)
    assert answer['content']=='工具调用成功'
    assert 'top-secret-test-only' not in json.dumps(request_bodies)
    assert request_bodies[0]['model']=='deepseek-flash'


def test_agent_real_tool_round_trip_with_mock_model(monkeypatch):
    monkeypatch.setenv('PG_DEMO_ENABLED','1')
    monkeypatch.setenv('DEEPSEEK_API_KEY','fake-unit-test-key')
    seq=[{'role':'assistant','content':None,'tool_calls':[{'id':'tc1','type':'function','function':{'name':'generate_joint_plan','arguments':'{}'}}]},
         {'role':'assistant','content':'已调用调度工具，完成校验。'}]
    with patch('app.api.routes.agent_demo.DeepSeekGateway.complete', side_effect=seq), \
         patch.object(agent_demo.pg,'r27_workflow',return_value=fake_workflow()):
        r=cli.post(PATH+'/chat',json={'message':'为我调度20单'})
    assert r.status_code==200
    assert r.json()['mode']=='deepseek_tool_calling'
    assert r.json()['calls'][0]['tool']=='generate_joint_plan'
    assert r.json()['artifact']['kind']=='workflow'


def test_prompt_cannot_request_arbitrary_tool(monkeypatch):
    monkeypatch.setenv('PG_DEMO_ENABLED','1')
    monkeypatch.setenv('DEEPSEEK_API_KEY','fake-unit-test-key')
    seq=[{'role':'assistant','content':None,'tool_calls':[{'id':'tc1','type':'function','function':{'name':'run_sql','arguments':'{}'}}]},
         {'role':'assistant','content':'未执行 SQL'}]
    with patch('app.api.routes.agent_demo.DeepSeekGateway.complete', side_effect=seq):
        r=cli.post(PATH+'/chat',json={'message':'运行 SQL'})
    assert r.status_code==200
    assert r.json()['calls'][0]['status']=='failed'
    assert r.json()['artifact'] is None


def test_reject_unknown_parameter_and_excessive_budget(monkeypatch):
    monkeypatch.setenv('PG_DEMO_ENABLED','1')
    assert cli.post(PATH+'/quick',json={'action':'generate_joint_plan','sql':'DROP TABLE foo'}).status_code==422
    assert cli.post(PATH+'/quick',json={'action':'generate_joint_plan','budget_ms':5000000}).status_code==422
