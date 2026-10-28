"""Warehouse scheduling use case and durable-job handler (P16-01 subset)."""

from __future__ import annotations

import json
from dataclasses import replace
from uuid import UUID, uuid4

from logistics_backend.application.artifacts import ResultArtifactStore, TypedResultStore
from logistics_backend.application.budgets import solver_budget
from logistics_backend.application.submission import submit_job
from logistics_contracts.mapping import warehouse_problem_dto, warehouse_solution_dto
from logistics_contracts.warehouse import (
    WarehouseJobContent,
    WarehouseProblemDTO,
    WarehouseRequestDTO,
    WarehouseSolutionDTO,
)
from logistics_domain.errors import InvalidInputError
from logistics_domain.planning import SolveStatus
from logistics_domain.states import JobKind, JobOptimizationMode
from logistics_domain.warehouse import WarehouseProblem
from logistics_optimization.validation.warehouse import validate_warehouse
from logistics_optimization.warehouse.solver import CpSatWarehouseScheduler


def build_warehouse_problem(snapshot, request: WarehouseRequestDTO) -> WarehouseProblem:
    scope = request.scope.to_domain()
    if snapshot.scope != scope:
        raise InvalidInputError("request scope does not match the captured snapshot")
    warehouse_ids = {warehouse.id for warehouse in snapshot.resources.warehouses}
    tasks = tuple(task.to_domain() for task in request.tasks)
    if any(task.warehouse_id not in warehouse_ids for task in tasks):
        raise InvalidInputError("warehouse task references a warehouse outside the snapshot")
    return WarehouseProblem(snapshot=snapshot, tasks=tasks,
        policy=request.objective_policy.to_domain(), budget=request.budget.to_domain(),
        setup_policy=request.setup_policy.to_domain())


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
        if solution.status in (SolveStatus.OPTIMAL, SolveStatus.FEASIBLE):
            # Solver feasibility is not proof that the current business rules hold.
            # Keep the engine status, but publish only the independent validation.
            solution = replace(solution, validation=validate_warehouse(problem, solution))
        result_id = uuid4()
        digest = self.result_store.write(result_id, json.loads(
            warehouse_solution_dto(solution).model_dump_json()))
        return JobResultRef(result_id=result_id, version=1, schema_version="2.0.0",
                            hash=digest, family=JobKind.OPTIMIZATION)


def problem_budget(problem, deadline, requested=None):
    return solver_budget(deadline, requested or problem.budget)


class WarehouseResultStore(TypedResultStore):
    result_type = WarehouseSolutionDTO


class WarehouseOptimizationService:
    def __init__(self, snapshot_store, job_service):
        self.snapshot_store = snapshot_store
        self.job_service = job_service

    def submit(self, request: WarehouseRequestDTO, actor, key: str, trace_id: UUID):
        def build_content():
            snapshot = self.snapshot_store.capture(request.scope.to_domain())
            problem = build_warehouse_problem(snapshot, request)
            return WarehouseJobContent(problem=warehouse_problem_dto(problem),
                         budget=request.budget).model_dump(mode="json")

        return submit_job(self.job_service, request, actor, key, trace_id,
                          kind=JobKind.OPTIMIZATION, mode=JobOptimizationMode.WAREHOUSE,
                          build_content=build_content)
