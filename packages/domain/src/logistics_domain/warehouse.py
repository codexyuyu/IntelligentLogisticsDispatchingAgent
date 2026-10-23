"""Warehouse scheduling problem/result values (P08-01)."""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from logistics_domain.errors import InvalidInputError
from logistics_domain.planning import (
    EngineMetadata,
    ObjectiveBreakdown,
    ObjectivePolicy,
    OperationAssignment,
    PlanningSnapshot,
    SetupOperation,
    SolveBudget,
    SolveStatus,
    SolverEvidence,
    StorageInterval,
    ValidationReport,
    WarehouseTask,
)
from logistics_domain.primitives import require_non_negative_int, require_uuid

__all__ = ["Diagnostic", "WarehouseProblem", "WarehouseSolution"]


@dataclass(frozen=True, slots=True)
class Diagnostic:
    code: str
    message: str
    severity: str = "error"

    def __post_init__(self) -> None:
        if not self.code or not self.message:
            raise InvalidInputError("warehouse diagnostic needs code and message")


@dataclass(frozen=True, slots=True)
class WarehouseProblem:
    snapshot: PlanningSnapshot
    tasks: tuple[WarehouseTask, ...]
    policy: ObjectivePolicy
    budget: SolveBudget

    def __post_init__(self) -> None:
        if not isinstance(self.snapshot, PlanningSnapshot):
            raise InvalidInputError("WarehouseProblem.snapshot must be a PlanningSnapshot")
        if not isinstance(self.tasks, tuple) or not self.tasks:
            raise InvalidInputError("WarehouseProblem requires at least one task")
        ids = [task.id for task in self.tasks]
        if len(set(ids)) != len(ids):
            raise InvalidInputError("WarehouseProblem repeats a task id")
        if not isinstance(self.policy, ObjectivePolicy) or not isinstance(self.budget, SolveBudget):
            raise InvalidInputError("WarehouseProblem policy/budget are invalid")


@dataclass(frozen=True, slots=True)
class WarehouseSolution:
    status: SolveStatus
    engine_metadata: EngineMetadata
    assignments: tuple[OperationAssignment, ...]
    storage_allocations: tuple[StorageInterval, ...]
    setup_operations: tuple[SetupOperation, ...]
    objective: ObjectiveBreakdown | None
    validation: ValidationReport | None
    diagnostics: tuple[Diagnostic, ...]
    solver_evidence: tuple[SolverEvidence, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.status, SolveStatus):
            raise InvalidInputError("WarehouseSolution.status must be SolveStatus")
        if self.status in (SolveStatus.OPTIMAL, SolveStatus.FEASIBLE) and not self.assignments:
            raise InvalidInputError("feasible warehouse solution requires assignments")
        if self.status not in (SolveStatus.OPTIMAL, SolveStatus.FEASIBLE) and self.assignments:
            raise InvalidInputError("failed warehouse solution cannot carry assignments")
