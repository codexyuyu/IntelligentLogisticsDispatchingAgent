"""车辆延误工具：事件事实来自持久化载荷，工具产出待审方案且从不提交。"""

import json
from pathlib import Path
from uuid import UUID, uuid4

import pytest

from logistics_agents.tools import ToolRegistry
from logistics_backend.application import vehicle_delay_tool as vdt
from logistics_backend.application.tools import ToolService
from logistics_backend.application.vehicle_delay_reschedule import NOT_RESOLVED, RESOLVED
from logistics_contracts.integration import ScenarioImport
from logistics_contracts.mapping import budget_dto, policy_dto, scope_dto
from logistics_contracts.planning import MatrixRefDTO
from logistics_contracts.transport import TransportRequestDTO
from logistics_backend.application.scenario_import import prepare_scenario
from logistics_backend.application.optimization import build_transport_problem
from logistics_domain.planning import DisturbanceWeights, ObjectivePolicy, SolveBudget
from logistics_domain.runtime import ActorContext, ActorRole
from logistics_optimization.transport.solver import OrToolsTransportSolver

from datetime import UTC, datetime, timedelta

ROOT = Path(__file__).resolve().parents[2]
SCENARIO = ROOT / "data" / "scenarios" / "partner_coldchain_synthetic.json"


def _budget(ms=4000):
    return SolveBudget(wall_time_ms=ms,
        deadline_utc=(datetime.now(UTC) + timedelta(seconds=120)).replace(microsecond=0),
        max_candidates=1, seed=0, worker_count=1, deterministic_test_mode=False)


@pytest.fixture(scope="module")
def actor():
    return ActorContext(actor_id=uuid4(), role=ActorRole.OPERATOR, scope_id=uuid4())


@pytest.fixture(scope="module")
def base_plan():
    payload = json.loads(SCENARIO.read_text(encoding="utf-8"))
    prepared = prepare_scenario(ScenarioImport.model_validate(payload))
    assert prepared["status"] == "checked", prepared
    snapshot = ScenarioImport.model_validate(prepared["payload"]).snapshot.to_domain()
    matrix = snapshot.matrices[0]
    policy = ObjectivePolicy("1.0.0", 100000, 1, 1, DisturbanceWeights(0, 0, 0, 0))
    request = TransportRequestDTO(scope=scope_dto(snapshot.scope),
        order_ids=snapshot.scope.order_ids, vehicle_ids=snapshot.scope.vehicle_ids,
        matrix_ref=MatrixRefDTO(matrix_id=matrix.id, version=matrix.version, hash=matrix.hash),
        budget=budget_dto(_budget()), objective_policy=policy_dto(policy))
    problem = build_transport_problem(snapshot, request)
    solution = OrToolsTransportSolver().solve(problem, _budget())
    assert solution.candidate is not None
    return problem, solution.candidate, solution.stops


def _tool_service():
    # jobs/agents 在本工具路径上不参与，传 None 即可
    return ToolService(jobs=None, agents=None)


def _register(tool_service, *, kind, payload, plan_fixture):
    def read_event(event_id, actor):
        return {"event_id": event_id, "kind": kind, "payload": payload}

    def base(actor):
        return plan_fixture

    planner = vdt.VehicleDelayPlanner(read_event=read_event, base_plan=base)
    vdt.register_vehicle_delay_tool(tool_service, planner)
    return tool_service


def test_tool_is_registered_with_operator_only(actor):
    service = _tool_service()
    _register(service, kind="vehicle_delay", payload={}, plan_fixture=None)
    specs = {spec.name: spec for spec in service.specs()}
    assert vdt.TOOL_NAME in specs
    assert specs[vdt.TOOL_NAME].allowed_roles == ("operator",)


def test_tool_rejects_unknown_role(actor, base_plan):
    service = _tool_service()
    _register(service, kind="vehicle_delay", payload={}, plan_fixture=base_plan)
    viewer = ActorContext(actor_id=uuid4(), role=ActorRole.VIEWER, scope_id=actor.scope_id)
    result = service.invoke(vdt.TOOL_NAME, viewer, {"event_id": str(uuid4())})
    assert result.ok is False
    assert result.error_code == "tool_forbidden"


def test_tool_resolves_delay_and_returns_pending_approval(actor, base_plan):
    problem, plan, _ = base_plan
    vehicle_id = plan.routes[0].vehicle_id
    service = _tool_service()
    _register(service, kind="vehicle_delay",
              payload={"vehicle_id": str(vehicle_id), "delay_s": 60, "event_time_s": 0},
              plan_fixture=base_plan)

    result = service.invoke(vdt.TOOL_NAME, actor, {"event_id": str(uuid4())})

    assert result.ok is True, result
    content = result.content
    assert content["status"] == RESOLVED, (content.get("reason"), content.get("detail"))
    assert content["committed"] is False
    assert content["requires_human_approval"] is True
    assert content["validation"]["valid"] is True
    assert content["affected_order_ids"]
    assert content["detail"]["engine"]  # 真实引擎证据
    assert content["vehicle_id"] == str(vehicle_id)


def test_tool_rejects_non_vehicle_delay_event(actor, base_plan):
    service = _tool_service()
    _register(service, kind="temperature_alert",
              payload={"vehicle_id": str(uuid4())}, plan_fixture=base_plan)
    result = service.invoke(vdt.TOOL_NAME, actor, {"event_id": str(uuid4())})
    assert result.ok is True
    assert result.content["status"] == NOT_RESOLVED
    assert result.content["reason"] == "unsupported_event_kind"


def test_tool_reports_invalid_payload_instead_of_solving(actor, base_plan):
    service = _tool_service()
    _register(service, kind="vehicle_delay", payload={"vehicle_id": "not-a-uuid"},
              plan_fixture=base_plan)
    result = service.invoke(vdt.TOOL_NAME, actor, {"event_id": str(uuid4())})
    assert result.ok is True
    assert result.content["status"] == NOT_RESOLVED
    assert result.content["reason"] == "invalid_event_payload"


def test_tool_never_commits_even_when_resolved(actor, base_plan):
    problem, plan, _ = base_plan
    service = _tool_service()
    _register(service, kind="vehicle_delay",
              payload={"vehicle_id": str(plan.routes[0].vehicle_id), "delay_s": 30,
                       "event_time_s": 0}, plan_fixture=base_plan)
    content = service.invoke(vdt.TOOL_NAME, actor, {"event_id": str(uuid4())}).content
    if content["status"] == RESOLVED:
        assert content["committed"] is False
        assert content["requires_human_approval"] is True


def test_planner_is_independent_of_registry(actor, base_plan):
    """工具只是壳：核心编排可以被直接调用，便于后续 API 复用。"""

    planner = vdt.VehicleDelayPlanner(
        read_event=lambda eid, a: {"kind": "vehicle_delay",
            "payload": {"vehicle_id": str(base_plan[1].routes[0].vehicle_id),
                        "delay_s": 60, "event_time_s": 0}},
        base_plan=lambda a: base_plan,
    )
    content = planner.prepare(actor, uuid4())
    assert set(content) >= {"status", "reason", "affected_order_ids", "validation", "committed"}
    assert content["committed"] is False


class _ScriptedModel:
    """模拟模型决策：首轮只给 event_id 要求调工具，次轮据此作答。"""

    def __init__(self, event_id):
        self.event_id = event_id
        self.round = 0
        self.tool_names_offered: tuple = ()
        self.fed_back: dict | None = None

    @property
    def configured(self) -> bool:
        return True

    def complete(self, messages, tools=None):
        from logistics_agents.llm import LLMReply, ToolCall

        self.round += 1
        if self.round == 1:
            self.tool_names_offered = tuple(
                t["function"]["name"] for t in (tools or []))
            return LLMReply(content="", model="scripted", tool_calls=(
                ToolCall(id="c1", name=vdt.TOOL_NAME,
                         arguments=json.dumps({"event_id": str(self.event_id)})),))
        self.fed_back = json.loads([m for m in messages if m.role == "tool"][-1].content)
        return LLMReply(content="已生成待审方案，请人工确认。", model="scripted")


def test_model_driven_loop_reaches_real_solver(actor, base_plan):
    """模型只给 event_id；车辆、时长、时刻全部来自事件载荷，末端是真实求解器。

    这证明协议与链路可用，不证明真模型会做同样的选择——那需要真实 provider。
    """

    from logistics_agents.service import AgentChatService

    problem, plan, _ = base_plan
    event_id = uuid4()
    service = _tool_service()
    _register(service, kind="vehicle_delay",
              payload={"vehicle_id": str(plan.routes[0].vehicle_id),
                       "delay_s": 60, "event_time_s": 0},
              plan_fixture=base_plan)

    model = _ScriptedModel(event_id)
    run = AgentChatService(model).run_with_tools(
        f"事件 {event_id} 怎么处理？",
        tools=[spec.to_openai_tool() for spec in service.specs()],
        executor=lambda name, args: service.invoke(name, actor, args),
        max_turns=3)

    assert run.stopped_reason == "final_answer"
    assert vdt.TOOL_NAME in model.tool_names_offered
    assert len(run.turns) == 1 and run.turns[0].ok is True

    content = dict(run.turns[0].content)
    assert content["status"] == RESOLVED, (content.get("reason"), content.get("detail"))
    assert content["committed"] is False
    assert content["requires_human_approval"] is True
    assert content["validation"]["valid"] is True
    assert content["detail"]["engine"]  # 真实求解器证据，非 mock

    # 模型看到的回填内容就是工具真实产出
    assert model.fed_back is not None and model.fed_back["ok"] is True
    assert model.fed_back["content"]["status"] == RESOLVED


def test_tool_schema_declares_event_id_only(actor):
    """参数契约：模型只能指定事件，不能指定延误对象或时长。"""

    service = _tool_service()
    _register(service, kind="vehicle_delay", payload={}, plan_fixture=None)
    schema = {s.name: s.to_openai_tool() for s in service.specs()}[vdt.TOOL_NAME]
    params = schema["function"]["parameters"]
    assert params["required"] == ["event_id"]
    assert set(params["properties"]) == {"event_id", "budget_ms"}
    assert "vehicle_id" not in params["properties"]
