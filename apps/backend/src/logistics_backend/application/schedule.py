"""Schedule creation/listing service (P16 subset)."""

from __future__ import annotations

import dataclasses
import json
from datetime import datetime, timezone
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert

from logistics_backend.errors import ServiceError
from logistics_backend.persistence.planning_models import (
    candidate_plans,
    planning_snapshots,
    schedules,
)
from logistics_contracts.mapping import plan_dto, snapshot_dto
from logistics_contracts.planning import (
    CandidatePlanDTO,
    CommitCommandDTO,
    CommitReceiptDTO,
    CostBreakdownDTO,
    ObjectiveBreakdownDTO,
    ScheduleDTO,
    ScheduleTaskDTO,
    WarehousePlanDTO,
)
from logistics_contracts.schedules import (
    CandidateCreate,
    CandidateView,
    CommitRequest,
    ScheduleCreate,
    SchedulePage,
    ScheduleView,
)
from logistics_domain.planning import (
    CandidatePlan,
    ObjectiveBreakdown,
    Schedule,
    ScheduleTask,
    TaskKind,
    WarehousePlan,
    content_hash,
)
from logistics_domain.states import EntityState, ErrorCode


class ScheduleService:
    def __init__(self, uow_factory, workspace_id: UUID, snapshots=None, commits=None):
        self.uow_factory = uow_factory
        self.workspace_id = workspace_id
        self.snapshots = snapshots
        self.commits = commits

    def create(self, command: ScheduleCreate, actor) -> ScheduleView:
        now = datetime.now(timezone.utc).replace(microsecond=0)
        scope = command.scope.to_domain()
        schedule = Schedule(id=uuid4(), status=EntityState.DRAFT, created_at=now,
            updated_at=now, row_version=0, schema_version="2.0.0",
            created_by=actor.actor_id, name=command.name, scope=scope,
            active_version_id=None, epoch_utc=scope.epoch_utc,
            horizon_s=scope.horizon_s)
        payload = ScheduleDTO(id=schedule.id, status=schedule.status,
            created_at=now, updated_at=now, row_version=0, schema_version="2.0.0",
            created_by=actor.actor_id, name=schedule.name, scope=command.scope,
            active_version_id=None, epoch_utc=scope.epoch_utc,
            horizon_s=scope.horizon_s).model_dump(mode="json")
        with self.uow_factory() as uow:
            uow.connection.execute(schedules.insert().values(
                id=schedule.id, scope_id=actor.scope_id, status=schedule.status.value,
                created_at=now, updated_at=now, created_by=actor.actor_id, row_version=0,
                schema_version="2.0.0", payload=payload, name=schedule.name,
                active_version_id=None, epoch_utc=scope.epoch_utc,
                horizon_s=scope.horizon_s))
        return self._view(schedule.id, schedule.name, schedule.status.value, scope.epoch_utc,
                          scope.horizon_s, None)

    def create_candidate(self, schedule_id: UUID, command: CandidateCreate,
                         actor) -> CandidateView:
        if self.snapshots is None:
            raise ServiceError(ErrorCode.DEPENDENCY_UNAVAILABLE, "snapshot store unavailable")
        scope = command.scope.to_domain()
        with self.uow_factory() as uow:
            schedule = uow.connection.execute(select(schedules).where(
                schedules.c.id == schedule_id,
                schedules.c.scope_id == actor.scope_id)).mappings().first()
        if schedule is None:
            raise ServiceError(ErrorCode.NOT_FOUND, "schedule not found")
        if (schedule["epoch_utc"] != scope.epoch_utc
                or schedule["horizon_s"] != scope.horizon_s):
            raise ServiceError(ErrorCode.STALE_SNAPSHOT,
                "candidate scope epoch/horizon differs from the schedule")
        snapshot = self.snapshots.capture(scope)
        self._persist_snapshot(snapshot, actor)
        plan = command.plan.to_domain()
        stops = tuple(stop.to_domain() for stop in command.stops)
        routes = {route.id: route for route in plan.routes}
        candidate_id = uuid4()
        now = datetime.now(timezone.utc).replace(microsecond=0)
        tasks = []
        for stop in stops:
            route = routes.get(stop.route_id)
            if route is None:
                raise ServiceError(ErrorCode.INVALID_INPUT, "stop route is not in the plan")
            for task_id in stop.task_ids:
                tasks.append(ScheduleTask(id=uuid4(), status=EntityState.PLANNED,
                    created_at=now, updated_at=now, row_version=0, schema_version="2.0.0",
                    created_by=actor.actor_id, version_id=candidate_id, task_id=task_id,
                    task_kind=TaskKind.TRANSPORT,
                    assigned_resource_ids=(route.vehicle_id,),
                    planned_start_s=stop.service_start_s,
                    planned_end_s=max(stop.departure_s, stop.service_start_s + 1),
                    sequence=stop.sequence))
        objective = ObjectiveBreakdown(business_cost_cents=plan.cost.total_cents,
            optional_unserved_penalty=0, soft_late_penalty=0, disturbance_penalty=0,
            makespan_penalty=0, objective_total=plan.cost.total_cents)
        body = {"schedule_id": schedule_id, "snapshot_id": snapshot.id,
            "snapshot_hash": snapshot.hash, "epoch_utc": scope.epoch_utc,
            "horizon_s": scope.horizon_s, "transport_plan": plan,
            "task_assignments": tuple(tasks), "objective": objective,
            "solver_evidence_refs": command.solver_evidence_refs}
        digest = content_hash(body)
        candidate = CandidatePlan(id=candidate_id, schedule_id=schedule_id,
            base_version_id=command.base_version_id, snapshot_id=snapshot.id,
            snapshot_hash=snapshot.hash, epoch_utc=scope.epoch_utc,
            horizon_s=scope.horizon_s, transport_plan=plan,
            warehouse_plan=WarehousePlan((), (), (), plan.cost),
            task_assignments=tuple(tasks), objective=objective, content_hash=digest,
            solver_evidence_refs=command.solver_evidence_refs)
        dto = CandidatePlanDTO(id=candidate.id, schedule_id=schedule_id,
            base_version_id=command.base_version_id, snapshot_id=snapshot.id,
            snapshot_hash=snapshot.hash, epoch_utc=scope.epoch_utc,
            horizon_s=scope.horizon_s, transport_plan=command.plan,
            warehouse_plan=WarehousePlanDTO(assignments=(), storage_intervals=(),
                setup_operations=(), cost=CostBreakdownDTO(
                    distance_cents=plan.cost.distance_cents,
                    fixed_vehicle_cents=plan.cost.fixed_vehicle_cents,
                    service_cents=plan.cost.service_cents,
                    overtime_cents=plan.cost.overtime_cents,
                    setup_cents=plan.cost.setup_cents,
                    total_cents=plan.cost.total_cents)),
            task_assignments=tuple(ScheduleTaskDTO(id=task.id, status=task.status,
                created_at=now, updated_at=now, row_version=0, schema_version="2.0.0",
                created_by=actor.actor_id, version_id=candidate_id, task_id=task.task_id,
                task_kind=task.task_kind, assigned_resource_ids=task.assigned_resource_ids,
                planned_start_s=task.planned_start_s, planned_end_s=task.planned_end_s,
                sequence=task.sequence) for task in tasks),
            objective=ObjectiveBreakdownDTO(business_cost_cents=objective.business_cost_cents,
                optional_unserved_penalty=0, soft_late_penalty=0, disturbance_penalty=0,
                makespan_penalty=0, objective_total=objective.objective_total),
            content_hash=digest, solver_evidence_refs=command.solver_evidence_refs)
        with self.uow_factory() as uow:
            uow.connection.execute(candidate_plans.insert().values(
                id=candidate.id, scope_id=actor.scope_id, schedule_id=schedule_id,
                base_version_id=command.base_version_id, snapshot_id=snapshot.id,
                snapshot_hash=snapshot.hash, content_hash=digest, created_at=now,
                payload=json.loads(dto.model_dump_json())))
        return CandidateView(candidate_id=candidate.id, schedule_id=schedule_id,
            snapshot_id=snapshot.id, content_hash=digest)

    def _persist_snapshot(self, snapshot, actor) -> None:
        now = datetime.now(timezone.utc).replace(microsecond=0)
        dto = snapshot_dto(snapshot)
        payload = json.loads(dto.model_dump_json())
        with self.uow_factory() as uow:
            uow.connection.execute(pg_insert(planning_snapshots).values(
                id=snapshot.id, scope_id=actor.scope_id,
                scope_hash=content_hash(snapshot.scope), content_hash=snapshot.hash,
                status="recorded", created_at=now, updated_at=now,
                created_by=actor.actor_id, row_version=0, schema_version="2.0.0",
                payload=payload).on_conflict_do_nothing())

    def commit(self, schedule_id: UUID, request: CommitRequest, actor,
               trace_id: UUID) -> CommitReceiptDTO:
        if request.command.schedule_id != schedule_id:
            raise ServiceError(ErrorCode.INVALID_INPUT, "commit schedule id mismatch")
        if self.commits is None:
            raise ServiceError(ErrorCode.DEPENDENCY_UNAVAILABLE, "commit store unavailable")
        receipt = self.commits.commit(request.command.to_domain(),
            request.report.to_domain(), actor=actor, trace_id=trace_id)
        return CommitReceiptDTO.model_validate(dataclasses.asdict(receipt))

    def list(self, actor, limit: int = 50) -> SchedulePage:
        with self.uow_factory() as uow:
            rows = uow.connection.execute(select(schedules).where(
                schedules.c.scope_id == actor.scope_id)
                .order_by(schedules.c.created_at.desc()).limit(min(max(limit, 1), 200))
            ).mappings().all()
        return SchedulePage(items=tuple(self._view(row["id"], row["name"], row["status"],
            row["epoch_utc"], row["horizon_s"], row["active_version_id"]) for row in rows))

    @staticmethod
    def _view(schedule_id, name, status, epoch_utc, horizon_s, active_version_id):
        return ScheduleView(schedule_id=schedule_id, name=name, status=status,
            epoch_utc=epoch_utc, horizon_s=horizon_s, active_version_id=active_version_id)
