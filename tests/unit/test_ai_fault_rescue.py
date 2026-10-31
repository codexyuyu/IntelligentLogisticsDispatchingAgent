"""No DB, no external DeepSeek call, no OR-Tools installation required."""
from logistics_agents.llm import LLMReply, ToolCall
from logistics_backend.application import ai_fault_rescue as ai


class FakeProvider:
    configured = True
    def __init__(self, calls=None):
        self.calls = calls or list(ai.TOOL_SEQUENCE)
        self.position = 0
    def complete(self, messages, tools=None):
        if tools:
            target = self.calls[self.position]
            self.position += 1
            return LLMReply(content='', model='fake-deepseek',
                            tool_calls=(ToolCall(id=f't{self.position}', name=target, arguments='{}'),))
        return LLMReply(content='方案已计算，必须人工审批。', model='fake-deepseek')


class OfflineProvider:
    configured = False


def _fake_solution(budget_ms):
    assert budget_ms == 1800
    return {'solver':'OR-Tools RoutingModel', 'status':'solved', 'candidate_valid':True,
            'reason':None, 'metrics':{
                'no_rescue': {'objective_cents':8000, 'distance_m':9000, 'delivered_orders':6},
                'candidate': {'objective_cents':9000, 'distance_m':11000, 'delivered_orders':8}},
            'rescue_assignments':{'demo-o4':'demo-truck-01', 'demo-o5':'demo-truck-03'},
            'recovered_orders':2}


def test_model_calls_real_server_tools_and_does_not_autoapprove(monkeypatch):
    monkeypatch.setattr(ai.fixture, 'solve_breakdown_showcase', _fake_solution)
    result = ai.collaborate(FakeProvider(), 1800)
    assert result['ai_status'] == 'model_success'
    assert [x['tool'] for x in result['tool_trace']] == list(ai.TOOL_SEQUENCE)
    assert result['comparison']['cost_delta_cents'] == 1000  # not fabricated savings
    assert result['comparison']['recovered_orders'] == 2
    assert result['approval_required'] is True and result['approval_performed'] is False
    assert result['rescue']['candidate_valid'] is True


def test_missing_key_does_not_solve(monkeypatch):
    monkeypatch.setattr(ai.fixture, 'solve_breakdown_showcase', lambda _: 1/0)
    result = ai.collaborate(OfflineProvider())
    assert result['ai_status'] == 'model_unavailable' and result['rescue'] is None
    assert result['tool_trace'] == []


def test_model_skipping_context_is_rejected_without_solver_call(monkeypatch):
    monkeypatch.setattr(ai.fixture, 'solve_breakdown_showcase', lambda _: 1/0)
    result = ai.collaborate(FakeProvider(['solve_rescue_dispatch']))
    assert result['ai_status'] == 'model_invalid_tool_call'
    assert result['tool_trace'] == [] and result['rescue'] is None


def test_solver_unavailable_is_not_labeled_solved(monkeypatch):
    monkeypatch.setattr(ai.fixture, 'solve_breakdown_showcase', lambda _: 1/0)
    result = ai.collaborate(FakeProvider())
    assert result['ai_status'] == 'solver_failed'
    assert [t['tool'] for t in result['tool_trace']] == ['get_incident_context']


def test_solver_unsolved_keeps_true_status(monkeypatch):
    monkeypatch.setattr(ai.fixture, 'solve_breakdown_showcase',
                        lambda _: {'solver':'OR-Tools', 'status':'no_solution_within_budget',
                                   'candidate_valid':False, 'reason':'search timeout',
                                   'metrics':{'no_rescue':{'delivered_orders':6, 'objective_cents':500,
                                                           'distance_m':1000}}})
    result = ai.collaborate(FakeProvider())
    assert result['ai_status'] == 'model_success'
    assert result['comparison']['candidate'] is None
    assert result['comparison']['recovered_orders'] is None
    assert result['rescue']['candidate_valid'] is False
