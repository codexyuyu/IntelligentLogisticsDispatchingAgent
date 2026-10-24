"""Schedule creation/listing service (P16 subset)."""

from __future__ import annotations

import dataclasses
import json
from datetime import UTC, datetime
from uuid import UUID, uuid4

from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert as pg_insert

from logistics_backend.application.optimization import TransportResultStore
from logistics_backend.errors import ServiceError
from logistics_backend.persistence.planning_models import (
    candidate_plans,
    planning_snapshots,
    schedule_tasks,
    schedule_versions,
    schedules,
)
from logistics_backend.persistence.validation_models import validation_reports
from logistics_contracts.mapping import (
    operation_assignment_dto,
    setup_operation_dto,
    snapshot_dto,
    storage_interval_dto,
)
from logistics_contracts.planning import (
    CandidatePlanDTO,
    CommitReceiptDTO,
    CostBreakdownDTO,
    ObjectiveBreakdownDTO,
    ScheduleDTO,
    ScheduleTaskDTO,
    ValidationReportDTO,
    WarehousePlanDTO,
)
from logistics_contracts.schedules import (
    CandidateCreate,
    CandidateFromJob,
    CandidateView,
    CommitRequest,
    ScheduleCreate,
    ScheduleDiffView,
    SchedulePage,
    ScheduleTaskChange,
    ScheduleTaskView,
    ScheduleVersionDetailView,
    ScheduleVersionPage,
    ScheduleVersionView,
    ScheduleView,
)
from logistics_contracts.transport import TransportJobContent, TransportProblemDTO
from logistics_domain.planning import (
    CandidatePlan,
    CostBreakdown,
    ObjectiveBreakdown,
    Schedule,
    ScheduleTask,
    TaskKind,
    WarehousePlan,
    content_hash,
)
from logistics_domain.states import EntityState, ErrorCode
from logistics_optimization.validation.transport import validate_transport
from logistics_optimization.validation.warehouse import validate_warehouse


class ScheduleService:
    def __init__(self, uow_factory, workspace_id: UUID, snapshots=None, commits=None,
                 jobs=None):
        self.uow_factory = uow_factory
        self.workspace_id = workspace_id
        self.snapshots = snapshots
        self.commits = commits
        self.jobs = jobs
        self.transport_results = TransportResultStore()

    def create(self, command: ScheduleCreate, actor) -> ScheduleView:
        now = datetime.now(UTC).replace(microsecond=0)
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
        problem = command.problem.to_domain()
        snapshot = problem.snapshot
        scope = snapshot.scope
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
        self._persist_snapshot(snapshot, actor)
        plan = command.plan.to_domain()
        stops = tuple(stop.to_domain() for stop in command.stops)
        routes = {route.id: route for route in plan.routes}
        candidate_id = uuid4()
        now = datetime.now(UTC).replace(microsecond=0)
        tasks = []
        seen_tasks = set()
        for stop in stops:
            route = routes.get(stop.route_id)
            if route is None:
                raise ServiceError(ErrorCode.INVALID_INPUT, "stop route is not in the plan")
            for task_id in stop.task_ids:
                if task_id in seen_tasks:
                    continue
                seen_tasks.add(task_id)
                tasks.append(ScheduleTask(id=uuid4(), status=EntityState.PLANNED,
                    created_at=now, updated_at=now, row_version=0, schema_version="2.0.0",
                    created_by=actor.actor_id, version_id=candidate_id, task_id=task_id,
                    task_kind=TaskKind.TRANSPORT,
                    assigned_resource_ids=(route.vehicle_id,),
                    planned_start_s=stop.service_start_s,
                    planned_end_s=max(stop.departure_s, stop.service_start_s + 1),
                    sequence=stop.sequence))
        warehouse_plan = WarehousePlan((), (), (), plan.cost)
        warehouse_violations = ()
        warehouse_valid = True
        if (command.warehouse_problem is None) != (command.warehouse_solution is None):
            raise ServiceError(ErrorCode.INVALID_INPUT,
                "warehouse problem and solution must be supplied together")
        if command.warehouse_problem is not None and command.warehouse_solution is not None:
            warehouse_problem = command.warehouse_problem.to_domain()
            warehouse_solution = command.warehouse_solution.to_domain()
            warehouse_report = validate_warehouse(warehouse_problem, warehouse_solution)
            warehouse_valid = warehouse_report.valid
            warehouse_violations = warehouse_report.violations
            warehouse_business = (warehouse_solution.objective.business_cost_cents
                                  if warehouse_solution.objective is not None else 0)
            warehouse_cost = CostBreakdown(0, 0, warehouse_business, 0, 0, warehouse_business)
            warehouse_plan = WarehousePlan(warehouse_solution.assignments,
                warehouse_solution.storage_allocations, warehouse_solution.setup_operations,
                warehouse_cost)
            grouped = {}
            for assignment in warehouse_solution.assignments:
                grouped.setdefault(assignment.task_id, []).append(assignment)
            for task_id, values in grouped.items():
                if any(task.task_id == task_id for task in tasks):
                    raise ServiceError(ErrorCode.INVALID_INPUT,
                        "warehouse task id collides with a transport task")
                tasks.append(ScheduleTask(id=uuid4(), status=EntityState.PLANNED,
                    created_at=now, updated_at=now, row_version=0, schema_version="2.0.0",
                    created_by=actor.actor_id, version_id=candidate_id,
                    task_id=task_id, task_kind=TaskKind.WAREHOUSE,
                    assigned_resource_ids=tuple(sorted(
                        {value.resource_id for value in values}, key=str)),
                    planned_start_s=min(value.start_s for value in values),
                    planned_end_s=max(value.end_s for value in values),
                    sequence=None))
        total_business = plan.cost.total_cents + warehouse_plan.cost.total_cents
        objective = ObjectiveBreakdown(business_cost_cents=total_business,
            optional_unserved_penalty=0, soft_late_penalty=0, disturbance_penalty=0,
            makespan_penalty=0, objective_total=total_business)
        body = {"schedule_id": schedule_id, "snapshot_id": snapshot.id,
            "snapshot_hash": snapshot.hash, "epoch_utc": scope.epoch_utc,
            "horizon_s": scope.horizon_s, "transport_plan": plan,
            "warehouse_plan": warehouse_plan,
            "task_assignments": tuple(tasks), "objective": objective,
            "solver_evidence_refs": command.solver_evidence_refs}
        digest = content_hash(body)
        transport_report = validate_transport(plan, problem, stops)
        report = dataclasses.replace(transport_report,
            valid=transport_report.valid and warehouse_valid,
            violations=transport_report.violations + warehouse_violations,
            candidate_hash=digest, snapshot_hash=snapshot.hash)
        candidate = CandidatePlan(id=candidate_id, schedule_id=schedule_id,
            base_version_id=command.base_version_id, snapshot_id=snapshot.id,
            snapshot_hash=snapshot.hash, epoch_utc=scope.epoch_utc,
            horizon_s=scope.horizon_s, transport_plan=plan,
            warehouse_plan=warehouse_plan,
            task_assignments=tuple(tasks), objective=objective, content_hash=digest,
            solver_evidence_refs=command.solver_evidence_refs)
        dto = CandidatePlanDTO(id=candidate.id, schedule_id=schedule_id,
            base_version_id=command.base_version_id, snapshot_id=snapshot.id,
            snapshot_hash=snapshot.hash, epoch_utc=scope.epoch_utc,
            horizon_s=scope.horizon_s, transport_plan=command.plan,
            warehouse_plan=WarehousePlanDTO(
                assignments=tuple(operation_assignment_dto(value)
                                  for value in warehouse_plan.assignments),
                storage_intervals=tuple(storage_interval_dto(value)
                                        for value in warehouse_plan.storage_intervals),
                setup_operations=tuple(setup_operation_dto(value)
                                       for value in warehouse_plan.setup_operations),
                cost=CostBreakdownDTO(
                    distance_cents=warehouse_plan.cost.distance_cents,
                    fixed_vehicle_cents=warehouse_plan.cost.fixed_vehicle_cents,
                    service_cents=warehouse_plan.cost.service_cents,
                    overtime_cents=warehouse_plan.cost.overtime_cents,
                    setup_cents=warehouse_plan.cost.setup_cents,
                    total_cents=warehouse_plan.cost.total_cents)),
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
        report_payload = json.loads(ValidationReportDTO.model_validate(
            dataclasses.asdict(report)).model_dump_json())
        with self.uow_factory() as uow:
            uow.connection.execute(validation_reports.insert().values(
                id=report.id, scope_id=actor.scope_id, candidate_id=candidate_id,
                candidate_hash=digest, snapshot_hash=snapshot.hash,
                rules_version=report.rules_version, valid=report.valid,
                report=report_payload, created_at=now, created_by=actor.actor_id))
            uow.connection.execute(candidate_plans.insert().values(
                id=candidate.id, scope_id=actor.scope_id, schedule_id=schedule_id,
                base_version_id=command.base_version_id, snapshot_id=snapshot.id,
                snapshot_hash=snapshot.hash, content_hash=digest, created_at=now,
                payload=json.loads(dto.model_dump_json())))
        return CandidateView(candidate_id=candidate.id, schedule_id=schedule_id,
            snapshot_id=snapshot.id, snapshot_hash=snapshot.hash, content_hash=digest,
            validation_report_id=report.id, valid=report.valid)

    def _persist_snapshot(self, snapshot, actor) -> None:
        now = datetime.now(UTC).replace(microsecond=0)
        dto = snapshot_dto(snapshot)
        payload = json.loads(dto.model_dump_json())
        with self.uow_factory() as uow:
            uow.connection.execute(pg_insert(planning_snapshots).values(
                id=snapshot.id, scope_id=actor.scope_id,
                scope_hash=content_hash(snapshot.scope), content_hash=snapshot.hash,
                status="recorded", created_at=now, updated_at=now,
                created_by=actor.actor_id, row_version=0, schema_version="2.0.0",
                payload=payload).on_conflict_do_nothing())

    def create_candidate_from_job(self, schedule_id: UUID, command: CandidateFromJob,
                                  actor) -> CandidateView:
        if self.jobs is None:
            raise ServiceError(ErrorCode.DEPENDENCY_UNAVAILABLE, "job service unavailable")
        job = self.jobs.get(command.job_id, actor)
        content = self.jobs.load_request(command.job_id, actor)
        try:
            payload = TransportJobContent.model_validate_json(content)
            problem = payload.problem
        except Exception:
            problem = TransportProblemDTO.model_validate_json(content)
        solution = self.transport_results.read(job)
        if solution.candidate is None or not solution.stops:
            raise ServiceError(ErrorCode.UNVERIFIED_SOLVER_RESULT,
                "completed job has no candidate stops")
        refs = tuple(evidence.id for evidence in solution.solver_evidence)
        if not refs:
            raise ServiceError(ErrorCode.UNVERIFIED_SOLVER_RESULT,
                "completed job has no solver evidence")
        return self.create_candidate(schedule_id, CandidateCreate(
            problem=problem, plan=solution.candidate, stops=solution.stops,
            solver_evidence_refs=refs, base_version_id=command.base_version_id), actor)

    def commit(self, schedule_id: UUID, request: CommitRequest, actor,
               trace_id: UUID) -> CommitReceiptDTO:
        if request.command.schedule_id != schedule_id:
            raise ServiceError(ErrorCode.INVALID_INPUT, "commit schedule id mismatch")
        if self.commits is None:
            raise ServiceError(ErrorCode.DEPENDENCY_UNAVAILABLE, "commit store unavailable")
        with self.uow_factory() as uow:
            row = uow.connection.execute(select(validation_reports).where(
                validation_reports.c.candidate_id == request.command.candidate_id,
                validation_reports.c.scope_id == actor.scope_id)).mappings().first()
        if row is None:
            raise ServiceError(ErrorCode.UNVERIFIED_SOLVER_RESULT,
                "candidate has no stored validation report")
        report = ValidationReportDTO.model_validate(row["report"]).to_domain()
        receipt = self.commits.commit(request.command.to_domain(),
            report, actor=actor, trace_id=trace_id)
        return CommitReceiptDTO.model_validate(dataclasses.asdict(receipt))

    def list(self, actor, limit: int = 50) -> SchedulePage:
        with self.uow_factory() as uow:
            rows = uow.connection.execute(select(schedules).where(
                schedules.c.scope_id == actor.scope_id)
                .order_by(schedules.c.created_at.desc()).limit(min(max(limit, 1), 200))
            ).mappings().all()
        return SchedulePage(items=tuple(self._view(row["id"], row["name"], row["status"],
            row["epoch_utc"], row["horizon_s"], row["active_version_id"]) for row in rows))

    def versions(self, schedule_id: UUID, actor, limit: int = 50) -> ScheduleVersionPage:
        self._require_schedule(schedule_id, actor)
        with self.uow_factory() as uow:
            rows = uow.connection.execute(select(schedule_versions).where(
                schedule_versions.c.schedule_id == schedule_id,
                schedule_versions.c.scope_id == actor.scope_id)
                .order_by(schedule_versions.c.version_no.desc())
                .limit(min(max(limit, 1), 200))).mappings().all()
        return ScheduleVersionPage(items=tuple(self._version_view(row) for row in rows))

    def current_version(self, schedule_id: UUID, actor) -> ScheduleVersionDetailView:
        schedule = self._require_schedule(schedule_id, actor)
        if schedule["active_version_id"] is None:
            raise ServiceError(ErrorCode.NOT_FOUND, "schedule has no committed version")
        return self.version_detail(schedule_id, schedule["active_version_id"], actor)

    def version_detail(self, schedule_id: UUID, version_id: UUID,
                       actor) -> ScheduleVersionDetailView:
        self._require_schedule(schedule_id, actor)
        with self.uow_factory() as uow:
            row = uow.connection.execute(select(schedule_versions).where(
                schedule_versions.c.id == version_id,
                schedule_versions.c.schedule_id == schedule_id,
                schedule_versions.c.scope_id == actor.scope_id)).mappings().first()
            if row is None:
                raise ServiceError(ErrorCode.NOT_FOUND, "schedule version not found")
            task_rows = uow.connection.execute(select(schedule_tasks).where(
                schedule_tasks.c.version_id == version_id,
                schedule_tasks.c.scope_id == actor.scope_id)
                .order_by(schedule_tasks.c.sequence, schedule_tasks.c.id)).mappings().all()
        tasks = tuple(ScheduleTaskView(task_id=task["task_id"],
            task_kind=task["task_kind"],
            assigned_resource_ids=tuple(UUID(value) for value in
                task["payload"].get("assigned_resource_ids", ())),
            planned_start_s=task["planned_start_s"], planned_end_s=task["planned_end_s"],
            sequence=task["sequence"], status=task["status"]) for task in task_rows)
        return ScheduleVersionDetailView(version=self._version_view(row), tasks=tasks)

    def diff(self, schedule_id: UUID, base_version_id: UUID, candidate_version_id: UUID,
             actor) -> ScheduleDiffView:
        self._require_schedule(schedule_id, actor)
        if base_version_id == candidate_version_id:
            with self.uow_factory() as uow:
                row = uow.connection.execute(select(schedule_versions).where(
                    schedule_versions.c.id == base_version_id,
                    schedule_versions.c.schedule_id == schedule_id,
                    schedule_versions.c.scope_id == actor.scope_id)).mappings().first()
                if row is None:
                    raise ServiceError(ErrorCode.NOT_FOUND, "schedule version not found")
                unchanged = int(uow.connection.execute(select(func.count()).select_from(schedule_tasks)
                    .where(schedule_tasks.c.version_id == base_version_id,
                           schedule_tasks.c.scope_id == actor.scope_id)).scalar_one())
            return ScheduleDiffView(schedule_id=schedule_id, base_version_id=base_version_id,
                candidate_version_id=candidate_version_id, base_hash=row["content_hash"],
                candidate_hash=row["content_hash"], added_task_ids=(), removed_task_ids=(),
                changed_tasks=(), unchanged_count=unchanged)
        with self.uow_factory() as uow:
            versions = uow.connection.execute(select(schedule_versions).where(
                schedule_versions.c.id.in_((base_version_id, candidate_version_id)),
                schedule_versions.c.schedule_id == schedule_id,
                schedule_versions.c.scope_id == actor.scope_id)).mappings().all()
            if len(versions) != 2:
                raise ServiceError(ErrorCode.NOT_FOUND, "one or both versions were not found")
            by_id = {row["id"]: row for row in versions}
            task_rows = uow.connection.execute(select(schedule_tasks).where(
                schedule_tasks.c.version_id.in_((base_version_id, candidate_version_id)),
                schedule_tasks.c.scope_id == actor.scope_id)).mappings().all()
        before = {row["task_id"]: row for row in task_rows
                  if row["version_id"] == base_version_id}
        after = {row["task_id"]: row for row in task_rows
                 if row["version_id"] == candidate_version_id}
        added = tuple(sorted(set(after) - set(before), key=str))
        removed = tuple(sorted(set(before) - set(after), key=str))
        changed = []
        unchanged = 0
        for task_id in sorted(set(before) & set(after), key=str):
            left, right = before[task_id], after[task_id]
            left_resources = tuple(UUID(value) for value in
                left["payload"].get("assigned_resource_ids", ()))
            right_resources = tuple(UUID(value) for value in
                right["payload"].get("assigned_resource_ids", ()))
            if (left["planned_start_s"] != right["planned_start_s"]
                    or left["planned_end_s"] != right["planned_end_s"]
                    or left_resources != right_resources):
                changed.append(ScheduleTaskChange(task_id=task_id,
                    before_start_s=left["planned_start_s"], before_end_s=left["planned_end_s"],
                    after_start_s=right["planned_start_s"], after_end_s=right["planned_end_s"],
                    before_resource_ids=left_resources,
                    after_resource_ids=right_resources))
            else:
                unchanged += 1
        return ScheduleDiffView(schedule_id=schedule_id,
            base_version_id=base_version_id, candidate_version_id=candidate_version_id,
            base_hash=by_id[base_version_id]["content_hash"],
            candidate_hash=by_id[candidate_version_id]["content_hash"],
            added_task_ids=added, removed_task_ids=removed,
            changed_tasks=tuple(changed), unchanged_count=unchanged)

    def _require_schedule(self, schedule_id: UUID, actor):
        with self.uow_factory() as uow:
            row = uow.connection.execute(select(schedules).where(
                schedules.c.id == schedule_id,
                schedules.c.scope_id == actor.scope_id)).mappings().first()
        if row is None:
            raise ServiceError(ErrorCode.NOT_FOUND, "schedule not found")
        return row

    @staticmethod
    def _version_view(row) -> ScheduleVersionView:
        return ScheduleVersionView(version_id=row["id"], schedule_id=row["schedule_id"],
            version_no=row["version_no"], status=row["status"],
            content_hash=row["content_hash"], parent_version_id=row["parent_version_id"],
            snapshot_id=row["snapshot_id"],
            validation_report_ref=row["validation_report_ref"],
            committed_at=row["created_at"])

    @staticmethod
    def _view(schedule_id, name, status, epoch_utc, horizon_s, active_version_id):
        return ScheduleView(schedule_id=schedule_id, name=name, status=status,
            epoch_utc=epoch_utc, horizon_s=horizon_s, active_version_id=active_version_id)
