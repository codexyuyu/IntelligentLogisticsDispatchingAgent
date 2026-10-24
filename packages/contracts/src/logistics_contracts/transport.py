"""HTTP/solver boundary projections for transport optimization (P06-01)."""

from __future__ import annotations

from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, StrictInt

from logistics_contracts.planning import (
    LoadDTO,
    MatrixRefDTO,
    ObjectiveBreakdownDTO,
    ObjectivePolicyDTO,
    PlanningSnapshotDTO,
    Record,
    RouteStopDTO,
    SolveBudgetDTO,
    SolverEvidenceDTO,
    TransportPlanDTO,
    TravelMatrixDTO,
    ValidationReportDTO,
)
from logistics_domain import transport as domain
from logistics_domain.orders import CargoType
from logistics_domain.planning import SolveStatus



class RoutingNodeDTO(Record):
    domain_type = domain.RoutingNode
    id: UUID
    kind: domain.RoutingNodeKind
    order_id: UUID | None
    location_id: UUID
    service_s: StrictInt
    hard_window: "TimeWindowDTO"
    soft_due_at_s: StrictInt | None
    load_delta: "SignedLoadDTO"
    pair_id: UUID | None


class SignedLoadDTO(Record):
    domain_type = domain.SignedLoad
    weight_g: StrictInt
    volume_cm3: StrictInt


class VehicleStateDTO(Record):
    domain_type = domain.VehicleState
    vehicle_id: UUID
    driver_id: UUID | None
    start_node_id: UUID
    end_node_id: UUID
    start_load: LoadDTO
    capacity_weight_g: StrictInt
    capacity_volume_cm3: StrictInt
    setpoint_decic: StrictInt
    available_window: "TimeWindowDTO"
    max_drive_s: StrictInt
    allowed_cargo_types: tuple[CargoType, ...]


class ConstraintSpecDTO(Record):
    domain_type = domain.ConstraintSpec
    code: str
    enabled: bool = True
    severity: Literal["hard", "soft"] = "hard"


class DiagnosticDTO(Record):
    domain_type = domain.Diagnostic
    code: str
    severity: domain.DiagnosticSeverity
    message: str
    entity_refs: tuple["EntityRefDTO", ...] = ()


class TransportProblemDTO(Record):
    domain_type = domain.TransportProblem
    snapshot: PlanningSnapshotDTO
    nodes: tuple[RoutingNodeDTO, ...]
    vehicles: tuple[VehicleStateDTO, ...]
    matrix: TravelMatrixDTO
    constraints: tuple[ConstraintSpecDTO, ...]
    policy: ObjectivePolicyDTO


class TransportSolutionDTO(Record):
    domain_type = domain.TransportSolution
    status: SolveStatus
    engine_metadata: "EngineMetadataDTO"
    candidate: TransportPlanDTO | None
    optional_unserved_order_ids: tuple[UUID, ...]
    objective: ObjectiveBreakdownDTO | None
    validation: ValidationReportDTO | None
    diagnostics: tuple[DiagnosticDTO, ...]
    solver_evidence: tuple[SolverEvidenceDTO, ...]
    stops: tuple[RouteStopDTO, ...] = ()


class TransportRequestDTO(BaseModel):
    """API request: selects a snapshot scope, vehicles, matrix and solver policy."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal["2.0.0"] = "2.0.0"
    scope: "PlanningScopeDTO"
    order_ids: tuple[UUID, ...]
    vehicle_ids: tuple[UUID, ...]
    matrix_ref: MatrixRefDTO
    budget: SolveBudgetDTO
    objective_policy: ObjectivePolicyDTO


class TransportResultView(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    schema_version: Literal["2.0.0"] = "2.0.0"
    solution: TransportSolutionDTO


class TransportJobContent(BaseModel):
    """Pinned problem plus the caller's solve budget, never trusted from the child clock."""

    model_config = ConfigDict(extra="forbid", frozen=True)
    schema_version: Literal["2.0.0"] = "2.0.0"
    problem: TransportProblemDTO
    budget: SolveBudgetDTO


from logistics_contracts.common import EntityRefDTO  # noqa: E402
from logistics_contracts.entities import TimeWindowDTO  # noqa: E402
from logistics_contracts.planning import (  # noqa: E402
    EngineMetadataDTO,
    PlanningScopeDTO,
)

RoutingNodeDTO.model_rebuild()
VehicleStateDTO.model_rebuild()
DiagnosticDTO.model_rebuild()
TransportSolutionDTO.model_rebuild()
TransportRequestDTO.model_rebuild()
