"""Transport problem/result values shared by solver, validator and API (P06-01)."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from uuid import UUID

from logistics_domain.errors import InvalidInputError
from logistics_domain.planning import (
    EngineMetadata,
    ObjectiveBreakdown,
    ObjectivePolicy,
    PlanningSnapshot,
    SolveStatus,
    SolverEvidence,
    TransportPlan,
    TravelMatrix,
    ValidationReport,
)
from logistics_domain.primitives import EntityRef, Load, TimeWindow, require_int, require_non_negative_int, require_positive_int, require_uuid
from logistics_domain.orders import CargoType

__all__ = [
    "ConstraintSpec",
    "Diagnostic",
    "DiagnosticSeverity",
    "RoutingNode",
    "RoutingNodeKind",
    "SignedLoad",
    "TransportProblem",
    "TransportSolution",
    "VehicleState",
]


class RoutingNodeKind(StrEnum):
    DEPOT = "depot"
    PICKUP = "pickup"
    DELIVERY = "delivery"
    VIRTUAL_START = "virtual_start"


class DiagnosticSeverity(StrEnum):
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"


@dataclass(frozen=True, slots=True)
class SignedLoad:
    """Load delta; delivery nodes carry a negative delta, pickups a positive one."""

    weight_g: int
    volume_cm3: int

    def __post_init__(self) -> None:
        require_int(self.weight_g, field="SignedLoad.weight_g")
        require_int(self.volume_cm3, field="SignedLoad.volume_cm3")


@dataclass(frozen=True, slots=True)
class ConstraintSpec:
    """Named hard-constraint switch carried into the solver; parameters are added by P10."""

    code: str
    enabled: bool = True
    severity: str = "hard"

    def __post_init__(self) -> None:
        if not isinstance(self.code, str) or not self.code:
            raise InvalidInputError("ConstraintSpec.code must be nonempty")
        if not isinstance(self.enabled, bool):
            raise InvalidInputError("ConstraintSpec.enabled must be bool")
        if self.severity not in ("hard", "soft"):
            raise InvalidInputError("ConstraintSpec.severity must be hard or soft")


@dataclass(frozen=True, slots=True)
class RoutingNode:
    """One visitable business node with load delta and service start window."""

    id: UUID
    kind: RoutingNodeKind
    order_id: UUID | None
    location_id: UUID
    service_s: int
    hard_window: TimeWindow
    soft_due_at_s: int | None
    load_delta: SignedLoad
    pair_id: UUID | None

    def __post_init__(self) -> None:
        require_uuid(self.id, field="RoutingNode.id")
        if not isinstance(self.kind, RoutingNodeKind):
            raise InvalidInputError("RoutingNode.kind must be RoutingNodeKind")
        if self.order_id is not None:
            require_uuid(self.order_id, field="RoutingNode.order_id")
        require_uuid(self.location_id, field="RoutingNode.location_id")
        require_non_negative_int(self.service_s, field="RoutingNode.service_s")
        if not isinstance(self.hard_window, TimeWindow):
            raise InvalidInputError("RoutingNode.hard_window must be TimeWindow")
        if self.soft_due_at_s is not None:
            require_non_negative_int(self.soft_due_at_s, field="RoutingNode.soft_due_at_s")
        if not isinstance(self.load_delta, SignedLoad):
            raise InvalidInputError("RoutingNode.load_delta must be SignedLoad")
        if self.pair_id is not None:
            require_uuid(self.pair_id, field="RoutingNode.pair_id")
        if self.kind in (RoutingNodeKind.PICKUP, RoutingNodeKind.DELIVERY) and self.pair_id is None:
            raise InvalidInputError("pickup/delivery nodes require a pair id")
        if self.kind == RoutingNodeKind.PICKUP and self.load_delta.weight_g < 0:
            raise InvalidInputError("pickup load delta must be non-negative")
        if self.kind == RoutingNodeKind.DELIVERY and self.load_delta.weight_g > 0:
            raise InvalidInputError("delivery load delta must be non-positive")


@dataclass(frozen=True, slots=True)
class VehicleState:
    """One vehicle's start/end depots, capacity, temperature and availability."""

    vehicle_id: UUID
    driver_id: UUID | None
    start_node_id: UUID
    end_node_id: UUID
    start_load: Load
    capacity_weight_g: int
    capacity_volume_cm3: int
    setpoint_decic: int
    available_window: TimeWindow
    max_drive_s: int
    allowed_cargo_types: tuple[CargoType, ...]

    def __post_init__(self) -> None:
        require_uuid(self.vehicle_id, field="VehicleState.vehicle_id")
        if self.driver_id is not None:
            require_uuid(self.driver_id, field="VehicleState.driver_id")
        require_uuid(self.start_node_id, field="VehicleState.start_node_id")
        require_uuid(self.end_node_id, field="VehicleState.end_node_id")
        if not isinstance(self.start_load, Load):
            raise InvalidInputError("VehicleState.start_load must be Load")
        require_positive_int(self.capacity_weight_g, field="VehicleState.capacity_weight_g")
        require_positive_int(self.capacity_volume_cm3, field="VehicleState.capacity_volume_cm3")
        if not isinstance(self.available_window, TimeWindow):
            raise InvalidInputError("VehicleState.available_window must be TimeWindow")
        require_positive_int(self.max_drive_s, field="VehicleState.max_drive_s")
        if not isinstance(self.allowed_cargo_types, tuple):
            raise InvalidInputError("VehicleState.allowed_cargo_types must be a tuple")


@dataclass(frozen=True, slots=True)
class TransportProblem:
    """Pure solver input; the snapshot is the read-only fact set this problem belongs to."""

    snapshot: PlanningSnapshot
    nodes: tuple[RoutingNode, ...]
    vehicles: tuple[VehicleState, ...]
    matrix: TravelMatrix
    constraints: tuple[ConstraintSpec, ...]
    policy: ObjectivePolicy

    def __post_init__(self) -> None:
        if not isinstance(self.snapshot, PlanningSnapshot):
            raise InvalidInputError("TransportProblem.snapshot must be a PlanningSnapshot")
        if not isinstance(self.nodes, tuple) or not isinstance(self.vehicles, tuple):
            raise InvalidInputError("TransportProblem nodes/vehicles must be tuples")
        if not self.vehicles:
            raise InvalidInputError("TransportProblem requires at least one vehicle")
        if not isinstance(self.matrix, TravelMatrix):
            raise InvalidInputError("TransportProblem.matrix must be TravelMatrix")
        if not isinstance(self.policy, ObjectivePolicy):
            raise InvalidInputError("TransportProblem.policy must be ObjectivePolicy")
        node_ids = [node.id for node in self.nodes]
        if len(set(node_ids)) != len(node_ids):
            raise InvalidInputError("TransportProblem repeats a node id")
        vehicle_ids = [vehicle.vehicle_id for vehicle in self.vehicles]
        if len(set(vehicle_ids)) != len(vehicle_ids):
            raise InvalidInputError("TransportProblem repeats a vehicle id")
        matrix_nodes = set(self.matrix.node_ids)
        for node in self.nodes:
            if node.location_id not in matrix_nodes:
                raise InvalidInputError("RoutingNode.location_id is missing from the matrix")


@dataclass(frozen=True, slots=True)
class Diagnostic:
    code: str
    severity: DiagnosticSeverity
    message: str
    entity_refs: tuple[EntityRef, ...] = ()

    def __post_init__(self) -> None:
        if not isinstance(self.code, str) or not self.code:
            raise InvalidInputError("Diagnostic.code must be nonempty")
        if not isinstance(self.severity, DiagnosticSeverity):
            raise InvalidInputError("Diagnostic.severity must be DiagnosticSeverity")
        if not isinstance(self.message, str) or not 1 <= len(self.message) <= 512:
            raise InvalidInputError("Diagnostic.message must be 1..512 characters")


@dataclass(frozen=True, slots=True)
class TransportSolution:
    """Typed solver result; absent candidate is never turned into a fake success route."""

    status: SolveStatus
    engine_metadata: EngineMetadata
    candidate: TransportPlan | None
    optional_unserved_order_ids: tuple[UUID, ...]
    objective: ObjectiveBreakdown | None
    validation: ValidationReport | None
    diagnostics: tuple[Diagnostic, ...]
    solver_evidence: tuple[SolverEvidence, ...]
    stops: tuple[RouteStop, ...] = ()

    def __post_init__(self) -> None:
        if not isinstance(self.status, SolveStatus):
            raise InvalidInputError("TransportSolution.status must be SolveStatus")
        if not isinstance(self.engine_metadata, EngineMetadata):
            raise InvalidInputError("TransportSolution.engine_metadata must be EngineMetadata")
        if self.candidate is None and self.objective is not None:
            raise InvalidInputError("a solution without candidate has no objective")
        if self.candidate is not None and self.objective is None:
            raise InvalidInputError("a candidate solution requires an objective")
        if self.status in (SolveStatus.OPTIMAL, SolveStatus.FEASIBLE) and self.candidate is None:
            raise InvalidInputError("feasible/optimal status requires a candidate")
        if not isinstance(self.solver_evidence, tuple):
            raise InvalidInputError("solver_evidence must be a tuple")
        if not isinstance(self.stops, tuple):
            raise InvalidInputError("TransportSolution.stops must be a tuple")
        for index, stop in enumerate(self.stops):
            if not isinstance(stop, RouteStop):
                raise InvalidInputError(f"TransportSolution.stops[{index}] must be RouteStop")
