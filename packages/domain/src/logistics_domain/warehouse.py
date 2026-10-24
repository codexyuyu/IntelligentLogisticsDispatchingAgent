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
    ResourceRequirement,
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
class SetupTransition:
    resource_id: UUID
    from_class: str
    to_class: str
    duration_s: int
    cost_cents: int = 0
    requirements: tuple[ResourceRequirement, ...] = ()

    def __post_init__(self):
        require_uuid(self.resource_id, field="setup.resource_id")
        if not self.from_class or not self.to_class or self.from_class == self.to_class:
            raise InvalidInputError("setup must name two different classes")
        require_non_negative_int(self.duration_s, field="setup.duration_s")
        require_non_negative_int(self.cost_cents, field="setup.cost_cents")
        if self.duration_s > 604800 or self.cost_cents > 10**9:
            raise InvalidInputError("setup duration/cost exceeds supported bounds")
        if self.duration_s == 0 and (self.cost_cents or self.requirements):
            raise InvalidInputError("zero-time setup cannot consume resources or cost")
        _requirements(self.requirements)
        if any(self.resource_id in r.eligible_ids for r in self.requirements):
            raise InvalidInputError("setup support cannot repeat its primary resource")


@dataclass(frozen=True, slots=True)
class InitialSetupState:
    resource_id: UUID
    setup_class: str

    def __post_init__(self):
        require_uuid(self.resource_id, field="initial_setup.resource_id")
        if not self.setup_class:
            raise InvalidInputError("initial setup class required")


@dataclass(frozen=True, slots=True)
class SetupPolicy:
    version: str = "1.0.0"
    transitions: tuple[SetupTransition, ...] = ()
    initial_states: tuple[InitialSetupState, ...] = ()

    def __post_init__(self):
        if not isinstance(self.version, str) or not self.version.strip():
            raise InvalidInputError("setup policy version required")
        for values, kind in ((self.transitions, SetupTransition), (self.initial_states, InitialSetupState)):
            if not isinstance(values, tuple) or any(not isinstance(v, kind) for v in values):
                raise InvalidInputError("setup policy values must be typed tuples")
        keys = [(t.resource_id, t.from_class, t.to_class) for t in self.transitions]
        ids = [s.resource_id for s in self.initial_states]
        if len(set(keys)) != len(keys) or len(set(ids)) != len(ids):
            raise InvalidInputError("duplicate setup rule/initial resource")


def _requirements(requirements):
    if not isinstance(requirements, tuple) or any(not isinstance(r, ResourceRequirement) for r in requirements):
        raise InvalidInputError("requirements must be a typed tuple")
    seen = set()
    for requirement in requirements:
        if seen.intersection(requirement.eligible_ids):
            raise InvalidInputError("resource candidates overlap between requirements")
        seen.update(requirement.eligible_ids)


@dataclass(frozen=True, slots=True)
class WarehouseProblem:
    snapshot: PlanningSnapshot
    tasks: tuple[WarehouseTask, ...]
    policy: ObjectivePolicy
    budget: SolveBudget
    setup_policy: SetupPolicy = SetupPolicy()

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
        if not isinstance(self.setup_policy, SetupPolicy):
            raise InvalidInputError("WarehouseProblem setup policy must be typed")
        for task in self.tasks:
            _requirements(task.requirements)
            if task.duration_s <= 0 or not task.requirements:
                raise InvalidInputError("warehouse tasks require positive duration and resources")
            if any(p not in ids for p in task.predecessor_ids):
                raise InvalidInputError("warehouse predecessor outside problem")


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
