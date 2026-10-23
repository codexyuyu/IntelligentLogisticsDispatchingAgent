"""Warehouse scheduling use case and durable-job handler (P16-01 subset)."""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from uuid import UUID, uuid4

from logistics_backend.application.artifacts import ResultArtifactStore, canonical_bytes
from logistics_contracts.mapping import warehouse_problem_dto, warehouse_solution_dto
from logistics_contracts.runtime import (
    JobRequest,
    OptimizationJobPayload,
    RequestRef as RequestRefDTO,
)
from logistics_contracts.warehouse import (
    WarehouseJobContent,
    WarehouseProblemDTO,
    WarehouseRequestDTO,
    WarehouseSolutionDTO,
)
from logistics_domain.errors import InvalidInputError
from logistics_domain.runtime import RequestRef
from logistics_domain.states import JobKind, JobOptimizationMode
from logistics_domain.warehouse import WarehouseProblem
from logistics_optimization.warehouse.solver import CpSatWarehouseScheduler


def _now() -> datetime:
    return datetime.now(timezone.utc).replace(microsecond=0)


def build_warehouse_problem(snapshot, request: WarehouseRequestDTO) -> WarehouseProblem:
    scope = request.scope.to_domain()
    if snapshot.scope != scope:
        raise InvalidInputError("request scope does not match the captured snapshot")
    warehouse_ids = {warehouse.id for warehouse in snapshot.resources.warehouses}
    tasks = tuple(task.to_domain() for task in request.tasks)
    if any(task.warehouse_id not in warehouse_ids for task in tasks):
        raise InvalidInputError("warehouse task references a warehouse outside the snapshot")
    return WarehouseProblem(snapshot=snapshot, tasks=tasks,
        policy=request.objective_policy.to_domain(), budget=request.budget.to_domain())


class WarehouseJobHandler:
    family = JobKind.OPTIMIZATION
    mode = JobOptimizationMode.WAREHOUSE

    def __init__(self, result_store: ResultArtifactStore | None = None):
        self.result_store = result_store or ResultArtifactStore()

    def validate(self, content: bytes) -> None:
        try:
            try:
                WarehouseJobContent.model_validate_json(content).problem.to_domain()
            except Exception:
                WarehouseProblemDTO.model_validate_json(content).to_domain()
        except Exception as exc:
            raise InvalidInputError("warehouse job content is not a valid pinned problem") from exc

    def execute(self, content: bytes, deadline):
        from logistics_contracts.runtime import JobResultRef

        try:
            payload = WarehouseJobContent.model_validate_json(content)
            problem = payload.problem.to_domain()
            requested = payload.budget.to_domain()
        except Exception:
            problem = WarehouseProblemDTO.model_validate_json(content).to_domain()
            requested = None
        solution = CpSatWarehouseScheduler().solve(problem,
            problem_budget(problem, deadline, requested))
        result_id = uuid4()
        digest = self.result_store.write(result_id, json.loads(
            warehouse_solution_dto(solution).model_dump_json()))
        return JobResultRef(result_id=result_id, version=1, schema_version="2.0.0",
                            hash=digest, family=JobKind.OPTIMIZATION)


def problem_budget(problem: WarehouseProblem, deadline, requested=None):
    from logistics_domain.planning import SolveBudget

    cap = requested.wall_time_ms if requested is not None else problem.budget.wall_time_ms
    remaining = max(1, min(5_000, int((deadline.expires_at_utc - _now()).total_seconds() * 1000)))
    wall_time_ms = max(1, min(cap, remaining, 5_000))
    return SolveBudget(wall_time_ms=wall_time_ms, deadline_utc=deadline.expires_at_utc,
        max_candidates=1, seed=requested.seed if requested is not None else problem.budget.seed,
        worker_count=1, deterministic_test_mode=False)


class WarehouseResultStore:
    def __init__(self, result_store: ResultArtifactStore | None = None):
        self.result_store = result_store or ResultArtifactStore()

    def read(self, job) -> WarehouseSolutionDTO:
        from logistics_backend.errors import ServiceError
        from logistics_domain.states import ErrorCode, JobStatus

        if job.status != JobStatus.COMPLETED or job.result_ref is None:
            raise ServiceError(ErrorCode.RESULT_NOT_READY, "job result is not ready")
        payload = self.result_store.read(job.result_ref.result_id, job.result_ref.hash)
        return WarehouseSolutionDTO.model_validate_json(payload)


class WarehouseOptimizationService:
    def __init__(self, snapshot_store, job_service):
        self.snapshot_store = snapshot_store
        self.job_service = job_service

    def submit(self, request: WarehouseRequestDTO, actor, key: str, trace_id: UUID):
        snapshot = self.snapshot_store.capture(request.scope.to_domain())
        problem = build_warehouse_problem(snapshot, request)
        content = canonical_bytes(json.loads(WarehouseJobContent(
            problem=warehouse_problem_dto(problem), budget=request.budget).model_dump_json()))
        request_id, version = uuid4(), 1
        digest = hashlib.sha256(content).hexdigest()
        reference = RequestRef(request_id=request_id, version=version, schema_version="2.0.0",
                               hash=digest, family=JobKind.OPTIMIZATION)
        self.job_service.store_request(reference, content, actor)
        command = JobRequest(schema_version="2.0.0", kind=JobKind.OPTIMIZATION,
            payload=OptimizationJobPayload(family="optimization",
                request_ref=RequestRefDTO(request_id=request_id, version=version,
                    schema_version="2.0.0", hash=digest, family=JobKind.OPTIMIZATION),
                mode=JobOptimizationMode.WAREHOUSE),
            deadline_utc=_now() + timedelta(seconds=55))
        return self.job_service.submit(command, actor, key, trace_id)
