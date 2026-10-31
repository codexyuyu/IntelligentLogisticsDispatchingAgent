"""Pure and mock-based AI review checks; never connects to PostgreSQL."""
from uuid import uuid4
from types import SimpleNamespace

from logistics_backend.application.decision_analysis import DecisionAnalysisService, decision_recommendation


def test_recommendation_uses_verified_objective_not_route_changed():
    assert decision_recommendation({'delta_vs_hold': {'improves_objective': False}}, True) == 'keep_original'
    assert decision_recommendation({'delta_vs_hold': {'improves_objective': True}}, True) == 'review_candidate'
    assert decision_recommendation({'delta_vs_hold': {'improves_objective': True}}, False) == 'not_approvable'
    assert decision_recommendation(None, True) == 'insufficient_comparison'


class FakeUow:
    def __init__(self, writes):
        self.writes = writes
        self.connection = self
    def __enter__(self):
        return self
    def __exit__(self, *args):
        return None
    def execute(self, statement):
        self.writes.append(statement)


class Provider:
    def __init__(self, configured=True, broken=False):
        self.configured = configured
        self.broken = broken
        self.calls = 0
    def complete(self, messages):
        self.calls += 1
        if self.broken:
            raise RuntimeError('secret provider connection details')
        assert '1000' in messages[-1].content
        return SimpleNamespace(model='deepseek-chat', content='根据实际求解数据，该方案仍需要人工审批。')


def _service(provider):
    writes = []
    service = DecisionAnalysisService(None, None, None, provider, lambda: FakeUow(writes))
    run, target = uuid4(), uuid4()
    service._evidence = lambda kind, tid, actor: (run, {'metrics': [{'value': 1000}]},
        [{'name': 'get_solver_candidate_metrics', 'ok': True, 'source': 'test'}], None)
    actor = SimpleNamespace(scope_id=uuid4(), actor_id=uuid4())
    return service, writes, actor, target


def test_model_reply_is_explicit_and_audited():
    provider = Provider()
    service, writes, actor, target = _service(provider)
    result = service.analyze('dispatch_task', target, actor)
    assert result['status'] == 'model_success'
    assert result['model'] == 'deepseek-chat'
    assert result['tool_trace'][-1]['ok'] is True
    assert provider.calls == 1 and len(writes) == 1


def test_unconfigured_model_does_not_generate_fake_answer():
    provider = Provider(configured=False)
    service, writes, actor, target = _service(provider)
    result = service.analyze('dispatch_task', target, actor)
    assert result['status'] == 'model_unavailable'
    assert result['reply'] == '' and result['model'] is None
    assert result['tool_trace'][-1]['ok'] is False
    assert provider.calls == 0 and len(writes) == 1


def test_model_failure_keeps_solver_evidence_and_hides_exception():
    provider = Provider(broken=True)
    service, writes, actor, target = _service(provider)
    result = service.analyze('dispatch_task', target, actor)
    assert result['status'] == 'model_failed'
    assert result['reply'] == ''
    assert result['error_code'] == 'provider_request_failed'
    assert 'secret' not in str(result)
    assert len(writes) == 1
