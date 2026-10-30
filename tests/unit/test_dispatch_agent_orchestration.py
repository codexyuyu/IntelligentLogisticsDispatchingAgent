"""Read-only model-to-tool dispatch tests. No live PostgreSQL or DeepSeek required."""

from __future__ import annotations

from uuid import uuid4

from logistics_agents.llm import LLMReply, ToolCall
from logistics_agents.service import AgentChatService
from logistics_backend.application.dispatch_agent import DispatchOrchestrator
from logistics_contracts.agents import DispatchRequest
from logistics_domain.runtime import ActorContext
from logistics_domain.states import ActorRole


class Provider:
    configured = True

    def __init__(self, calls):
        self.responses = list(calls)
        self.seen = []

    def complete(self, messages, tools=None):
        self.seen.append((messages, tools))
        return self.responses.pop(0)


class Integration:
    def __init__(self):
        self.retrieved = []

    def get(self, run_id, actor):
        self.retrieved.append((run_id, actor.scope_id))
        return {"status": "checked", "joint_validation": {"valid": True},
                "observations": {"on_time": 0.9}, "request": {"scenario_id": "s1"}}


class Simulation:
    def __init__(self):
        self.writes = 0

    def get(self, run_id, actor):
        return {"simulation_id": "sim", "incident": None, "tracks": [], "events": []}

    def state_at(self, run_id, time_s, view, actor):
        return {"vehicle_positions": {"v": {"progress": 0.5}},
                "in_transit_vehicle_ids": ["v"], "active_version": 0,
                "completed_operation_ids": ["w1"], "source_kind": "simulated_from_planned"}

    def incident(self, *args):
        self.writes += 1
        raise AssertionError("model must not register an incident")
    def project_delay(self, result, sim, vehicle_id, time_s, delay_s, budget_ms=None, key=None):
        """只读投影：不写库、不登记事件，符合 preview 的只读语义。"""
        return {"status": "resolved", "strategy": "simulated_local_retimed",
                "impact": {"valid": True, "affected_order_ids": ["o1"], "violations": []},
                "proposal_valid": True, "route_changed": False, "local_solver": True,
                "candidate_tracks": [], "candidate_events": [],
                "applied_to_simulation": False}

    def decide(self, *args):
        self.writes += 1
        raise AssertionError("model must not approve an incident")


class Audit:
    def __init__(self, provider):
        self.chat = AgentChatService(provider)
        self.logged = []

    def record_dispatch(self, command, actor, trace, run, content, stopped_reason, latency_ms=0):
        self.logged.append((run, stopped_reason))
        return {"message": content, "reason": stopped_reason, "turns": run.turns}


def test_agent_calls_real_metric_tool_in_bound_run():
    provider = Provider([
        LLMReply(content="", model="mock", tool_calls=(ToolCall(
            "c1", "get_dispatch_metrics", "{}"),)),
        LLMReply(content="on_time=0.9，来自真实求解观测。", model="mock"),
    ])
    integration, simulation = Integration(), Simulation()
    audit = Audit(provider)
    orchestrator = DispatchOrchestrator(integration, simulation, audit)
    run_id, scope = uuid4(), uuid4()
    actor = ActorContext(actor_id=uuid4(), scope_id=scope, role=ActorRole.OPERATOR)
    reply = orchestrator.execute(DispatchRequest(run_id=run_id, message="准时率?"), actor, uuid4())
    assert reply["reason"] == "final_answer"
    assert reply["turns"][0].content["observations"] == {"on_time": 0.9}
    assert all(pair == (run_id, scope) for pair in integration.retrieved)
    assert simulation.writes == 0
    assert [tool["function"]["name"] for tool in provider.seen[0][1]] == [
        "get_current_run", "get_dispatch_metrics", "get_warehouse_progress",
        "get_vehicle_states", "preview_vehicle_delay"]


def test_invalid_tool_arguments_cannot_execute_and_are_audited():
    provider = Provider([
        LLMReply(content="", model="mock", tool_calls=(ToolCall(
            "c1", "get_vehicle_states", '{"at_s":-1,"run_id":"other"}'),)),
        LLMReply(content="done", model="mock"),
    ])
    audit = Audit(provider)
    command = DispatchRequest(run_id=uuid4(), message="测试非法参数")
    actor = ActorContext(actor_id=uuid4(), scope_id=uuid4(), role=ActorRole.OPERATOR)
    reply = DispatchOrchestrator(Integration(), Simulation(), audit).execute(command, actor, uuid4())
    assert reply["reason"] == "no_tool_evidence"
    assert reply["turns"][0].error_code == "invalid_arguments"


def test_no_model_tool_call_is_not_reported_as_grounded_answer():
    provider = Provider([LLMReply(content="车辆全部准时", model="mock")])
    audit = Audit(provider)
    actor = ActorContext(actor_id=uuid4(), scope_id=uuid4(), role=ActorRole.OPERATOR)
    result = DispatchOrchestrator(Integration(), Simulation(), audit).execute(
        DispatchRequest(run_id=uuid4(), message="车辆情况?"), actor, uuid4())
    assert result["reason"] == "no_tool_evidence"
    assert "未取得有效" in result["message"]


def test_preview_is_read_only_and_checks_existing_incident(monkeypatch):
    from logistics_backend.application import dispatch_agent

    sim = Simulation()
    vehicle = uuid4()
    sim.get = lambda run_id, actor: {"simulation_id": "s", "incident": None,
        "tracks": [{"vehicle_id": str(vehicle)}], "events": [{"kind": "stub"}]}
    monkeypatch.setattr(dispatch_agent, "state_at_time", lambda *_:
                        {"in_transit_vehicle_ids": [str(vehicle)]})
    monkeypatch.setattr(dispatch_agent, "hold_and_shift", lambda *args: [])
    monkeypatch.setattr(dispatch_agent, "delay_impact", lambda *args: {
        "valid": True, "affected_order_ids": ["o1"], "violations": []})
    actor = ActorContext(actor_id=uuid4(), scope_id=uuid4(), role=ActorRole.OPERATOR)
    tool = DispatchOrchestrator(Integration(), sim, Audit(Provider([])))
    result = tool.preview_delay(uuid4(), actor, vehicle, 1400, 60)
    assert result["committed"] is False
    assert result["route_replanned"] is False
    assert result["proposal_valid"] is True
    assert sim.writes == 0


def test_model_cannot_call_approval_api():
    provider = Provider([
        LLMReply(content="", model="mock", tool_calls=(ToolCall(
            "c1", "approve_incident", "{}"),)),
        LLMReply(content="I cannot approve it.", model="mock"),
    ])
    sim = Simulation()
    actor = ActorContext(actor_id=uuid4(), scope_id=uuid4(), role=ActorRole.OPERATOR)
    reply = DispatchOrchestrator(Integration(), sim, Audit(provider)).execute(
        DispatchRequest(run_id=uuid4(), message="请自动批准"), actor, uuid4())
    assert reply["reason"] == "no_tool_evidence"
    assert reply["turns"][0].error_code == "tool_not_found"
    assert sim.writes == 0
