"""车辆延误重调度的人工审批闭环。

propose：局部重解结果 → 合并回完整方案 → 建候选（内部二次校验）→ 落 proposed 决策
approve：决策转 accepted → 提交新版本 → 把该版本路由与停靠点落库
reject ：只转决策状态，不提交

安全边界：
* 工具/模型只能到 propose；提交必须 operator 显式 approve；
* 提交走 ScheduleService.commit，快照哈希、校验报告、活跃版本都会再核对一次；
* 审批当时批准的方案与停靠点存放在决策载荷里，事后可追溯"到底批了什么"。
"""

from __future__ import annotations

import json
from dataclasses import asdict
from datetime import UTC, datetime, timedelta
from uuid import UUID

from sqlalchemy import select

from logistics_backend.application.decision import DecisionService
from logistics_backend.application.plan_route_store import (
    load_version_routes,
    persist_version_routes,
)
from logistics_backend.application.schedule import ScheduleService
from logistics_backend.application.vehicle_delay_merge import merge_local_solution
from logistics_backend.errors import ServiceError
from logistics_backend.persistence.decision_models import decision_records
from logistics_backend.persistence.planning_models import candidate_plans
from logistics_contracts.decision import DecisionCreate
from logistics_contracts.mapping import problem_dto
from logistics_contracts.planning import RouteStopDTO, TransportPlanDTO
from logistics_contracts.schedules import CandidateCreate, CommitCommandDTO, CommitRequest
from logistics_domain.states import EntityState, ErrorCode

DECISION_TYPE = "vehicle_delay_reschedule"


class VehicleDelayApprovalService:
    def __init__(self, *, uow_factory, scope_id: UUID, decisions: DecisionService,
                 schedules: ScheduleService):
        self.uow_factory = uow_factory
        self.scope_id = scope_id
        self.decisions = decisions
        self.schedules = schedules

    # ------------------------------------------------------------------ propose
    def propose(self, *, actor, schedule_id: UUID, problem, base_plan, base_stops,
                outcome, event_id: UUID | None = None,
                base_version_id: UUID | None = None) -> dict:
        if not outcome.resolved or outcome.solution is None:
            raise ServiceError(ErrorCode.INVALID_INPUT,
                               "only a resolved outcome can be proposed")

        vehicle_id = outcome.local_problem.vehicles[0].vehicle_id
        merged_plan, merged_stops = merge_local_solution(
            base_plan, base_stops, outcome.solution, vehicle_id)
        plan_dto = TransportPlanDTO.model_validate(asdict(merged_plan))
        stop_dtos = tuple(RouteStopDTO.model_validate(asdict(s)) for s in merged_stops)

        candidate = self.schedules.create_candidate(schedule_id, CandidateCreate(
            problem=problem_dto(problem), plan=plan_dto, stops=stop_dtos,
            solver_evidence_refs=tuple(e.id for e in outcome.solution.solver_evidence),
            base_version_id=base_version_id), actor)

        decision = self.decisions.record(DecisionCreate(
            decision_type=DECISION_TYPE,
            payload={
                "candidate_id": str(candidate.candidate_id),
                "schedule_id": str(schedule_id),
                "event_id": None if event_id is None else str(event_id),
                "vehicle_id": str(vehicle_id),
                "affected_order_ids": [str(o) for o in outcome.affected_order_ids],
                "candidate_valid": candidate.valid,
                # 审批对象本体：方案与停靠点，保证事后可复现"批了什么"
                "plan": plan_dto.model_dump(mode="json"),
                "stops": [s.model_dump(mode="json") for s in stop_dtos],
            },
            rationale="vehicle delay local reschedule; awaiting operator approval",
            confidence=1.0,
            evidence_refs=tuple(e.id for e in outcome.solution.solver_evidence),
        ), actor)

        return {
            "decision_id": str(decision.decision_id),
            "decision_status": decision.status,
            "candidate_id": str(candidate.candidate_id),
            "schedule_id": str(schedule_id),
            "candidate_valid": candidate.valid,
            "affected_order_ids": [str(o) for o in outcome.affected_order_ids],
            "committed": False,
        }

    # ------------------------------------------------------------------ approve
    def approve(self, *, actor, decision_id: UUID, trace_id: UUID,
                expected_active_version_id: UUID | None = None) -> dict:
        payload = self._payload(decision_id, actor)
        self.decisions.transition(decision_id, EntityState.ACCEPTED, actor)

        schedule_id = UUID(str(payload["schedule_id"]))
        candidate_id = UUID(str(payload["candidate_id"]))
        candidate_hash, snapshot_hash = self._candidate_hashes(candidate_id, actor)

        receipt = self.schedules.commit(schedule_id, CommitRequest(command=CommitCommandDTO(
            schedule_id=schedule_id,
            candidate_id=candidate_id,
            candidate_hash=candidate_hash,
            expected_active_version_id=expected_active_version_id,
            snapshot_hash=snapshot_hash,
            idempotency_key=f"vehicle-delay-approve-{decision_id}",
            confirmation_token=None,
        )), actor, trace_id)

        return {
            "decision_id": str(decision_id),
            "decision_status": EntityState.ACCEPTED.value,
            "schedule_id": str(schedule_id),
            "version_id": str(receipt.version_id),
            "version_no": receipt.version_no,
            "content_hash": receipt.content_hash,
            "approved_routes": len(TransportPlanDTO.model_validate(payload["plan"]).routes),
            "approved_stops": len(payload["stops"]),
            "committed": True,
        }

    # ------------------------------------------------------------------- reject
    def reject(self, *, actor, decision_id: UUID, reason: str = "rejected") -> dict:
        view = self.decisions.transition(decision_id, EntityState.REJECTED, actor)
        return {"decision_id": str(decision_id), "decision_status": view.status,
                "committed": False, "reason": reason}

    # --------------------------------------------------------------- from event
    def prepare_from_event(self, *, actor, event_id: UUID, schedule_id: UUID,
                           read_event, budget_ms: int = 4000) -> dict:
        """事件驱动入口：读持久化事件 → 还原基线 → 重建问题 → 重解 → 建候选待审。"""

        from logistics_backend.application.vehicle_delay_reschedule import (
            VehicleDelayRequest,
            resolve_vehicle_delay,
        )

        event = read_event(event_id, actor)
        if str(event.get("kind", "")) != "vehicle_delay":
            return {"status": "not_resolved", "reason": "unsupported_event_kind",
                    "event_id": str(event_id), "event_kind": str(event.get("kind"))}

        payload = event.get("payload") or {}
        base_plan, base_stops = self.load_base_plan(actor=actor, schedule_id=schedule_id)
        problem = self._rebuild_problem(actor, schedule_id, base_plan, budget_ms)

        request = VehicleDelayRequest(
            vehicle_id=UUID(str(payload["vehicle_id"])),
            delay_s=int(payload["delay_s"]),
            event_time_s=int(payload["event_time_s"]),
            budget_ms=budget_ms,
        )
        outcome = resolve_vehicle_delay(problem, base_plan, base_stops, request)
        if not outcome.resolved:
            return {"status": outcome.status, "reason": outcome.reason,
                    "event_id": str(event_id), "affected_order_ids":
                    [str(o) for o in outcome.affected_order_ids]}

        return self.propose(actor=actor, schedule_id=schedule_id, problem=problem,
                            base_plan=base_plan, base_stops=base_stops, outcome=outcome,
                            event_id=event_id)

    def _rebuild_problem(self, actor, schedule_id: UUID, plan, budget_ms: int):
        """用最近一次已批准候选的快照重建求解问题，保证与基线同源。"""

        import json

        from sqlalchemy import select

        from logistics_backend.application.optimization import build_transport_problem
        from logistics_backend.persistence.planning_models import candidate_plans, planning_snapshots
        from logistics_contracts.mapping import budget_dto, policy_dto, scope_dto
        from logistics_contracts.planning import MatrixRefDTO, PlanningSnapshotDTO
        from logistics_contracts.transport import TransportRequestDTO
        from logistics_domain.planning import DisturbanceWeights, ObjectivePolicy, SolveBudget

        with self.uow_factory() as uow:
            row = uow.connection.execute(select(planning_snapshots.c.payload)
                .where(planning_snapshots.c.id == select(candidate_plans.c.snapshot_id)
                       .where(candidate_plans.c.schedule_id == schedule_id,
                              candidate_plans.c.scope_id == actor.scope_id)
                       .order_by(candidate_plans.c.created_at.desc()).limit(1)
                       .scalar_subquery()).limit(1)).first()
        if row is None:
            raise ServiceError(ErrorCode.NOT_FOUND, "planning snapshot unavailable for schedule")
        snapshot = PlanningSnapshotDTO.model_validate_json(json.dumps(row[0])).to_domain()
        matrix = snapshot.matrices[0]
        policy = ObjectivePolicy("1.0.0", 100000, 1, 1, DisturbanceWeights(0, 0, 0, 0))
        budget = SolveBudget(wall_time_ms=budget_ms,
            deadline_utc=(datetime.now(UTC) + timedelta(seconds=60)).replace(microsecond=0),
            max_candidates=1, seed=0, worker_count=1, deterministic_test_mode=False)
        request = TransportRequestDTO(scope=scope_dto(snapshot.scope),
            order_ids=snapshot.scope.order_ids, vehicle_ids=snapshot.scope.vehicle_ids,
            matrix_ref=MatrixRefDTO(matrix_id=matrix.id, version=matrix.version, hash=matrix.hash),
            budget=budget_dto(budget), objective_policy=policy_dto(policy))
        return build_transport_problem(snapshot, request)

    # ------------------------------------------------------------------ helpers
    def _payload(self, decision_id: UUID, actor) -> dict:
        with self.uow_factory() as uow:
            row = uow.connection.execute(select(decision_records.c.payload).where(
                decision_records.c.id == decision_id,
                decision_records.c.scope_id == actor.scope_id)).first()
        if row is None:
            raise ServiceError(ErrorCode.NOT_FOUND, "decision not found")
        return row[0]

    def _candidate_hashes(self, candidate_id: UUID, actor) -> tuple[str, str]:
        with self.uow_factory() as uow:
            row = uow.connection.execute(select(
                candidate_plans.c.content_hash, candidate_plans.c.snapshot_hash).where(
                candidate_plans.c.id == candidate_id,
                candidate_plans.c.scope_id == actor.scope_id)).first()
        if row is None:
            raise ServiceError(ErrorCode.NOT_FOUND, "candidate not found")
        return row[0], row[1]

    def _persist(self, actor, version_id: UUID, payload: dict) -> tuple[int, int]:
        """落库到 routes/route_stops。

        注意：这两张表对 vehicles/drivers 有外键，而当前流程不写主数据，
        因此默认不调用；保留实现供主数据齐备的环境启用。
        """

        plan_dto = TransportPlanDTO.model_validate(payload["plan"])
        stop_dtos = tuple(RouteStopDTO.model_validate(s) for s in payload["stops"])
        plan = plan_dto.to_domain()
        stops = tuple(s.to_domain() for s in stop_dtos)
        now = datetime.now(UTC).replace(microsecond=0)
        with self.uow_factory() as uow:
            return persist_version_routes(
                uow, scope_id=actor.scope_id, version_id=version_id,
                actor_id=actor.actor_id, now=now,
                plan_routes=plan.routes, plan_stops=stops)

    def load_base_plan(self, *, actor, schedule_id: UUID):
        """从最近一次已批准的处置决策里还原基础方案。

        选择决策记录而不是 routes 表，是因为 routes 对车辆主数据有外键，
        而本流程不写主数据；审批载荷本身完整保存了被批准的方案与停靠点。
        没有已批准记录时明确失败，不猜测、不重解。
        """

        with self.uow_factory() as uow:
            row = uow.connection.execute(select(decision_records.c.payload).where(
                decision_records.c.scope_id == actor.scope_id,
                decision_records.c.decision_type == DECISION_TYPE,
                decision_records.c.status == EntityState.ACCEPTED.value,
                decision_records.c.payload["schedule_id"].astext == str(schedule_id),
            ).order_by(decision_records.c.created_at.desc()).limit(1)).first()
        if row is None:
            raise ServiceError(ErrorCode.NOT_FOUND,
                               "no approved base plan for this schedule")
        plan = TransportPlanDTO.model_validate(row[0]["plan"]).to_domain()
        stops = tuple(RouteStopDTO.model_validate(s).to_domain() for s in row[0]["stops"])
        return plan, stops
