"""真实 DeepSeek 工具调用验证（一次性脚本，不在产品路径上）。

用途：证明「模型看到事件后，自己决定调用 prepare_vehicle_delay_reschedule，
拿到真实求解结果，再据此作答」。这是唯一需要真实 API Key 才能验证的一环。

用法：
    1. 在项目根放置 .env（已被 .gitignore 忽略），内容：
           DEEPSEEK_API_KEY=sk-...
           DEEPSEEK_MODEL=deepseek-chat
    2. 用项目 venv 运行：
           python scripts/verify_live_llm.py [--out 结果.json]

安全：本脚本不打印、不记录 Key；只输出 configured 布尔值与模型名。
退出码：0=模型按预期调用了工具；1=模型未调用/调用失败；2=未配置 Key。
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import uuid4

ROOT = Path(__file__).resolve().parents[1]
for _member in ("apps/backend/src", "packages/domain/src", "packages/contracts/src",
                "packages/optimization/src", "packages/agents/src",
                "packages/simulation/src", "packages/evaluation/src"):
    _path = str(ROOT / _member)
    if _path not in sys.path:
        sys.path.insert(0, _path)


def load_env(path: Path) -> dict[str, str]:
    """极简 .env 读取：只认 KEY=VALUE，不处理引号与变量插值。"""

    if not path.exists():
        return {}
    values: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8-sig").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        values[key.strip()] = value.strip()
    return values


def _budget(ms: int = 4000):
    from logistics_domain.planning import SolveBudget

    return SolveBudget(
        wall_time_ms=ms,
        deadline_utc=(datetime.now(UTC) + timedelta(seconds=180)).replace(microsecond=0),
        max_candidates=1, seed=0, worker_count=1, deterministic_test_mode=False)


def build_problem_and_plan():
    """用仓库自带合成场景，跑一次真实运输求解，得到基础方案。"""

    from logistics_backend.application.optimization import build_transport_problem
    from logistics_backend.application.scenario_import import prepare_scenario
    from logistics_contracts.integration import ScenarioImport
    from logistics_contracts.mapping import budget_dto, policy_dto, scope_dto
    from logistics_contracts.planning import MatrixRefDTO
    from logistics_contracts.transport import TransportRequestDTO
    from logistics_domain.planning import DisturbanceWeights, ObjectivePolicy
    from logistics_optimization.transport.solver import OrToolsTransportSolver

    payload = json.loads(
        (ROOT / "data" / "scenarios" / "partner_coldchain_synthetic.json")
        .read_text(encoding="utf-8"))
    prepared = prepare_scenario(ScenarioImport.model_validate(payload))
    if prepared["status"] != "checked":
        raise SystemExit(f"场景未通过校验：{prepared}")
    snapshot = ScenarioImport.model_validate(prepared["payload"]).snapshot.to_domain()
    matrix = snapshot.matrices[0]
    policy = ObjectivePolicy("1.0.0", 100000, 1, 1, DisturbanceWeights(0, 0, 0, 0))
    request = TransportRequestDTO(
        scope=scope_dto(snapshot.scope),
        order_ids=snapshot.scope.order_ids, vehicle_ids=snapshot.scope.vehicle_ids,
        matrix_ref=MatrixRefDTO(matrix_id=matrix.id, version=matrix.version, hash=matrix.hash),
        budget=budget_dto(_budget()), objective_policy=policy_dto(policy))
    problem = build_transport_problem(snapshot, request)
    solution = OrToolsTransportSolver().solve(problem, _budget())
    if solution.candidate is None:
        raise SystemExit("基础方案求解失败，无法构造事件场景")
    return problem, solution.candidate, solution.stops


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", help="把完整运行记录写入该 JSON 文件")
    parser.add_argument("--max-turns", type=int, default=4)
    args = parser.parse_args()

    env = load_env(ROOT / ".env")
    for key in ("DEEPSEEK_API_KEY", "DEEPSEEK_BASE_URL", "DEEPSEEK_MODEL"):
        if env.get(key):
            os.environ.setdefault(key, env[key])

    from logistics_agents.llm import DeepSeekProvider, LLMSettings
    from logistics_agents.service import AgentChatService
    from logistics_backend.application.tools import ToolService
    from logistics_backend.application import vehicle_delay_tool as vdt
    from logistics_domain.runtime import ActorContext, ActorRole

    settings = LLMSettings.from_env()
    print(f"provider.configured = {settings.configured}")
    print(f"model               = {settings.model}")
    print(f"base_url            = {settings.base_url}")
    if not settings.configured:
        print("\n未配置 Key：在项目根创建 .env 并写入 DEEPSEEK_API_KEY 后重试。")
        return 2

    problem, base_plan, base_stops = build_problem_and_plan()
    vehicle_id = base_plan.routes[0].vehicle_id
    event_id = uuid4()
    # 本脚本走内存路径，不落库，故 actor 的 scope 用独立值即可（工具只校验角色）
    actor = ActorContext(actor_id=uuid4(), role=ActorRole.OPERATOR, scope_id=uuid4())

    tool_service = ToolService(jobs=None, agents=None)
    vdt.register_vehicle_delay_tool(tool_service, vdt.VehicleDelayPlanner(
        read_event=lambda eid, _a: {"event_id": eid, "kind": "vehicle_delay",
                                    "payload": {"vehicle_id": str(vehicle_id),
                                                "delay_s": 60, "event_time_s": 0}},
        base_plan=lambda _a: (problem, base_plan, base_stops)))

    prompt = (f"车辆 {vehicle_id} 发生了延误，事件编号是 {event_id}。"
              "请判断是否需要重排，并说明依据。")
    print(f"\nuser> {prompt}\n")

    service = AgentChatService(DeepSeekProvider(settings))
    run = service.run_with_tools(
        prompt,
        tools=[spec.to_openai_tool() for spec in tool_service.specs()],
        executor=lambda name, arguments: tool_service.invoke(name, actor, arguments),
        max_turns=args.max_turns)

    print(f"stopped_reason = {run.stopped_reason}")
    print(f"tool_calls     = {len(run.turns)}")
    for turn in run.turns:
        print(f"  [turn {turn.turn}] {turn.name} args={json.dumps(dict(turn.arguments or {}), ensure_ascii=False)}")
        print(f"            ok={turn.ok} error={turn.error_code}")
        if turn.ok:
            content = dict(turn.content)
            print(f"            status={content.get('status')} reason={content.get('reason')} "
                  f"committed={content.get('committed')} "
                  f"requires_human_approval={content.get('requires_human_approval')}")
            validation = content.get("validation") or {}
            print(f"            validation.valid={validation.get('valid')} "
                  f"violations={len(validation.get('violations') or [])}")
            detail = content.get("detail") or {}
            if detail:
                print(f"            engine={detail.get('engine')} solver={detail.get('solver_status')}")
    print(f"\nassistant> {run.reply.content}\n")

    record = {
        "schema": "live-llm-verification/1",
        "ran_at": datetime.now(UTC).replace(microsecond=0).isoformat(),
        "model": run.reply.model,
        "provider_configured": settings.configured,
        "event_id": str(event_id),
        "vehicle_id": str(vehicle_id),
        "prompt": prompt,
        "stopped_reason": run.stopped_reason,
        "turns": [
            {"turn": t.turn, "tool": t.name, "arguments": dict(t.arguments or {}),
             "ok": t.ok, "error_code": t.error_code,
             "status": dict(t.content).get("status") if t.ok else None,
             "validation_valid": (dict(t.content).get("validation") or {}).get("valid")
             if t.ok else None}
            for t in run.turns
        ],
        "final_answer": run.reply.content,
    }
    if args.out:
        Path(args.out).write_text(json.dumps(record, ensure_ascii=False, indent=2),
                                  encoding="utf-8")
        print(f"已写入 {args.out}")

    used_target_tool = any(t.name == vdt.TOOL_NAME and t.ok for t in run.turns)
    return 0 if used_target_tool else 1


if __name__ == "__main__":
    raise SystemExit(main())
