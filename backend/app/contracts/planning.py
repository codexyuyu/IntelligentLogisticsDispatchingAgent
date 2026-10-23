"""SHARED: B and AC must import these types rather than defining aliases."""
from typing import Literal
from pydantic import StrictStr
from app.contracts.common import ContractModel, Id, NonNegativeInt, PositiveInt, SolveBudget, SolveMetadata, ValidationReport, Hash, TimeWindow, Source
from app.contracts.coldchain import ColdChainPlan
from app.contracts.entities import PlanningSnapshot, ScheduledOperation

class WarehouseHandoff(ContractModel):
    order_id: Id
    warehouse_id: Id
    ready_at_s: NonNegativeInt
    loading_window: TimeWindow

class WarehouseDepartureTarget(ContractModel):
    """Soft just-in-time feedback: the time a vehicle intends to leave the depot."""
    order_id: Id
    warehouse_id: Id
    departure_at_s: NonNegativeInt
    vehicle_id: Id | None = None

class VehicleArrival(ContractModel):
    vehicle_id: Id
    warehouse_id: Id
    arrival_at_s: NonNegativeInt
    order_ids: tuple[Id, ...]

class RouteStop(ContractModel):
    node_id: Id
    order_ids: tuple[Id, ...]
    stop_kind: Literal['depot_start', 'delivery', 'depot_end']
    arrival_at_s: NonNegativeInt
    service_start_at_s: NonNegativeInt
    departure_at_s: NonNegativeInt
    load_weight_kg: NonNegativeInt
    load_volume_l: NonNegativeInt

class VehicleRoute(ContractModel):
    vehicle_id: Id
    stops: tuple[RouteStop, ...]
    distance_m: NonNegativeInt
    duration_s: NonNegativeInt

class UnservedOrder(ContractModel):
    order_id: Id
    reason_code: StrictStr

class RoutingRequest(ContractModel):
    snapshot: PlanningSnapshot
    order_ids: tuple[Id, ...]
    warehouse_handoffs: tuple[WarehouseHandoff, ...]
    frozen_routes: tuple[VehicleRoute, ...] = ()
    budget: SolveBudget

class RoutingResult(ContractModel):
    snapshot_id: Id
    snapshot_version: PositiveInt
    metadata: SolveMetadata
    routes: tuple[VehicleRoute, ...]
    warehouse_arrivals: tuple[VehicleArrival, ...]
    unserved_orders: tuple[UnservedOrder, ...]

class WarehouseScheduleRequest(ContractModel):
    snapshot: PlanningSnapshot
    order_ids: tuple[Id, ...]
    vehicle_arrivals: tuple[VehicleArrival, ...] = ()
    departure_targets: tuple[WarehouseDepartureTarget, ...] = ()
    budget: SolveBudget

class WarehouseScheduleResult(ContractModel):
    snapshot_id: Id
    snapshot_version: PositiveInt
    metadata: SolveMetadata
    operations: tuple[ScheduledOperation, ...]
    warehouse_handoffs: tuple[WarehouseHandoff, ...]
    #: R05 scheduling evidence; None means the schedule makes no R05 claim.
    coldchain: ColdChainPlan | None = None

class ColdChainValidationRequest(ContractModel):
    """Frozen input of an independent R05 check.

    The validator must see the request, the complete candidate result, the rule
    version and the data source; it must never infer any of them.
    """

    request: WarehouseScheduleRequest
    result: WarehouseScheduleResult
    rule_version: StrictStr
    source: Source

    def horizon_s(self) -> int:
        """Effective planning horizon of the underlying snapshot."""
        coldchain = self.request.snapshot.coldchain
        return coldchain.horizon_s if coldchain is not None else self.request.snapshot.simulation_time_s

class CoordinationRound(ContractModel):
    round_number: PositiveInt
    stage: Literal['initial', 'feedback']
    accepted: bool
    reason: StrictStr
    distance_m: NonNegativeInt | None = None
    unserved_count: NonNegativeInt | None = None
    total_handoff_wait_s: NonNegativeInt | None = None
    warehouse_makespan_s: NonNegativeInt | None = None
    warehouse_solve_ms: NonNegativeInt | None = None
    routing_solve_ms: NonNegativeInt | None = None

class CoordinationReport(ContractModel):
    mode: Literal['sequential', 'deep']
    requested_rounds: PositiveInt
    attempted_rounds: PositiveInt
    selected_round: PositiveInt
    baseline_distance_m: NonNegativeInt
    selected_distance_m: NonNegativeInt
    baseline_handoff_wait_s: NonNegativeInt
    selected_handoff_wait_s: NonNegativeInt
    rounds: tuple[CoordinationRound, ...]
    objective: StrictStr

class DispatchRequest(ContractModel):
    snapshot_id: Id
    expected_snapshot_version: PositiveInt
    order_ids: tuple[Id, ...]
    budget_ms: PositiveInt = 10000
    max_coordination_rounds: Literal[1, 2, 3] = 3
    coordination_mode: Literal['sequential', 'deep'] = 'sequential'

class CandidatePlan(ContractModel):
    plan_id: Id
    snapshot_id: Id
    snapshot_version: PositiveInt
    version: PositiveInt
    plan_hash: Hash
    routing: RoutingResult
    warehouse: WarehouseScheduleResult
    validation: ValidationReport
    coordination: CoordinationReport | None = None
