"""Warehouse scheduling boundary projections (P08-01)."""

from __future__ import annotations

from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, StrictInt

from logistics_contracts.planning import (
    EngineMetadataDTO,
    ObjectiveBreakdownDTO,
    ObjectivePolicyDTO,
    OperationAssignmentDTO,
    PlanningSnapshotDTO,
    Record,
    ResourceRequirementDTO,
    SetupOperationDTO,
    SolveBudgetDTO,
    SolverEvidenceDTO,
    StorageIntervalDTO,
    ValidationReportDTO,
    WarehouseTaskDTO,
)
from logistics_domain import warehouse as domain
from logistics_domain.planning import SolveStatus


class DiagnosticDTO(Record):
    domain_type = domain.Diagnostic
    code: str
    message: str
    severity: Literal["error", "warning", "info"] = "error"


class SetupTransitionDTO(Record):
    domain_type = domain.SetupTransition
    resource_id: UUID
    from_class: str
    to_class: str
    duration_s: StrictInt
    cost_cents: StrictInt = 0
    requirements: tuple[ResourceRequirementDTO, ...] = ()


class InitialSetupStateDTO(Record):
    domain_type = domain.InitialSetupState
    resource_id: UUID
    setup_class: str


class SetupPolicyDTO(Record):
    domain_type = domain.SetupPolicy
    version: str = "1.0.0"
    transitions: tuple[SetupTransitionDTO, ...] = ()
    initial_states: tuple[InitialSetupStateDTO, ...] = ()


class WarehouseProblemDTO(Record):
    domain_type = domain.WarehouseProblem
    snapshot: PlanningSnapshotDTO
    tasks: tuple[WarehouseTaskDTO, ...]
    policy: ObjectivePolicyDTO
    budget: SolveBudgetDTO
    setup_policy: SetupPolicyDTO = SetupPolicyDTO()


class WarehouseSolutionDTO(Record):
    domain_type = domain.WarehouseSolution
    status: SolveStatus
    engine_metadata: EngineMetadataDTO
    assignments: tuple[OperationAssignmentDTO, ...]
    storage_allocations: tuple[StorageIntervalDTO, ...]
    setup_operations: tuple[SetupOperationDTO, ...]
    objective: ObjectiveBreakdownDTO | None
    validation: ValidationReportDTO | None
    diagnostics: tuple[DiagnosticDTO, ...]
    solver_evidence: tuple[SolverEvidenceDTO, ...]


class WarehouseRequestDTO(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    schema_version: Literal["2.0.0"] = "2.0.0"
    scope: "PlanningScopeDTO"
    tasks: tuple[WarehouseTaskDTO, ...]
    budget: SolveBudgetDTO
    objective_policy: ObjectivePolicyDTO
    setup_policy: SetupPolicyDTO = SetupPolicyDTO()


class WarehouseJobContent(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    schema_version: Literal["2.0.0"] = "2.0.0"
    problem: WarehouseProblemDTO
    budget: SolveBudgetDTO


from logistics_contracts.planning import PlanningScopeDTO  # noqa: E402

WarehouseRequestDTO.model_rebuild()
