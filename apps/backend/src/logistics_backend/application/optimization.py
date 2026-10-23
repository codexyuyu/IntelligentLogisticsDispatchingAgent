"""Transport optimization use case and durable-job handler (P16-01/P05-03).

Coupling is deliberate and one-way:

* HTTP -> this application service -> ``PlanningSnapshotStore`` (port) -> pure problem;
* worker -> ``TransportJobHandler`` -> pure solver -> result artifact;
* API result query reads the artifact through ``TransportResultStore``.

No OR-Tools type, SQLAlchemy row or FastAPI request crosses these boundaries.
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timedelta, timezone
from uuid import UUID, uuid4, uuid5

from logistics_backend.application.artifacts import ResultArtifactStore, canonical_bytes
from logistics_contracts.mapping import problem_dto, solution_dto
from logistics_contracts.runtime import (
    JobRequest,
    OptimizationJobPayload,
    RequestRef as RequestRefDTO,
)
from logistics_contracts.transport import (
    TransportJobContent,
    TransportProblemDTO,
    TransportRequestDTO,
    TransportSolutionDTO,
)
from logistics_domain.errors import InvalidInputError
from logistics_domain.planning import MatrixRef, SolveBudget
from logistics_domain.primitives import Load, TimeWindow
from logistics_domain.runtime import RequestRef
from logistics_domain.states import JobKind, JobOptimizationMode
from logistics_domain.transport import (
    RoutingNode,
    RoutingNodeKind,
    SignedLoad,
    TransportProblem,
    VehicleState,
)
from logistics_optimization.transport.solver import OrToolsTransportSolver

NODE_NAMESPACE = UUID("6a6c6e4e-0e7a-5b8f-9f0d-7c5b8a1d2e3f")


def _now() -> datetime:
    return datetime.now(timezone.utc).replace(microsecond=0)


def _matrix_for(snapshot, reference: MatrixRef):
    for matrix in snapshot.matrices:
        if (matrix.id == reference.matrix_id and matrix.version == reference.version
                and matrix.hash == reference.hash):
            return matrix
    raise InvalidInputError("requested travel matrix version is not in the snapshot")


def build_transport_problem(snapshot, request: TransportRequestDTO) -> TransportProblem:
    """Map one HTTP request plus a pinned snapshot into the pure solver problem."""
    from logistics_contracts.mapping import budget_dto, policy_dto

    scope = request.scope.to_domain()
    if snapshot.scope != scope:
        raise InvalidInputError("request scope does not match the captured snapshot")
    orders = {order.id: order for order in snapshot.orders}
    vehicles = {vehicle.id: vehicle for vehicle in snapshot.vehicles}
    selected_orders = [orders[order_id] for order_id in request.order_ids if order_id in orders]
    if len(selected_orders) != len(set(request.order_ids)):
        raise InvalidInputError("request references an order outside the snapshot")
    selected_vehicles = [vehicles[vehicle_id] for vehicle_id in request.vehicle_ids
                         if vehicle_id in vehicles]
    if len(selected_vehicles) != len(set(request.vehicle_ids)):
        raise InvalidInputError("request references a vehicle outside the snapshot")
    matrix = _matrix_for(snapshot, request.matrix_ref.to_domain())
    matrix_nodes = set(matrix.node_ids)
    cargo_by_order: dict[UUID, list] = {}
    for cargo in snapshot.cargo:
        cargo_by_order.setdefault(cargo.order_id, []).append(cargo)
    drivers = {driver.id: driver for driver in snapshot.drivers}
    nodes: list[RoutingNode] = []
    for order in selected_orders:
        cargo = cargo_by_order.get(order.id, [])
        weight = sum(item.weight_g for item in cargo)
        volume = sum(item.volume_cm3 for item in cargo)
        for kind, location, window, delta in (
            (RoutingNodeKind.PICKUP, order.pickup_node_id, order.pickup_window,
             SignedLoad(weight_g=weight, volume_cm3=volume)),
            (RoutingNodeKind.DELIVERY, order.delivery_node_id, order.delivery_window,
             SignedLoad(weight_g=-weight, volume_cm3=-volume)),
        ):
            if location not in matrix_nodes:
                raise InvalidInputError("order node is missing from the selected matrix")
            nodes.append(RoutingNode(
                id=uuid5(NODE_NAMESPACE, f"{order.id}:{kind.value}"), kind=kind,
                order_id=order.id, location_id=location,
                service_s=order.service_s if kind == RoutingNodeKind.PICKUP else 0,
                hard_window=window, soft_due_at_s=order.soft_due_at_s if kind == RoutingNodeKind.DELIVERY else None,
                load_delta=delta, pair_id=order.id))
    vehicle_states: list[VehicleState] = []
    horizon = snapshot.scope.horizon_s
    for vehicle in selected_vehicles:
        driver = drivers.get(vehicle.driver_id) if vehicle.driver_id else None
        if vehicle.start_node_id not in matrix_nodes:
            raise InvalidInputError("vehicle start node is missing from the selected matrix")
        if vehicle.end_node_id not in matrix_nodes:
            raise InvalidInputError("vehicle end node is missing from the selected matrix")
        vehicle_states.append(VehicleState(
            vehicle_id=vehicle.id, driver_id=vehicle.driver_id,
            start_node_id=vehicle.start_node_id, end_node_id=vehicle.end_node_id,
            start_load=Load(0, 0),
            capacity_weight_g=vehicle.capacity_weight_g,
            capacity_volume_cm3=vehicle.capacity_volume_cm3,
            setpoint_decic=vehicle.setpoint_decic,
            available_window=TimeWindow(0, horizon),
            max_drive_s=min(horizon, driver.max_drive_s) if driver else horizon,
            allowed_cargo_types=vehicle.allowed_cargo_types))
    return TransportProblem(snapshot=snapshot, nodes=tuple(nodes), vehicles=tuple(vehicle_states),
        matrix=matrix, constraints=(), policy=request.objective_policy.to_domain())


class TransportJobHandler:
    """Durable-job handler; validates the pinned problem then runs the real solver."""

    family = JobKind.OPTIMIZATION
    mode = JobOptimizationMode.TRANSPORT

    def __init__(self, result_store: ResultArtifactStore | None = None):
        self.result_store = result_store or ResultArtifactStore()

    def validate(self, content: bytes) -> None:
        try:
            try:
                TransportJobContent.model_validate_json(content).problem.to_domain()
            except Exception:
                TransportProblemDTO.model_validate_json(content).to_domain()
        except Exception as exc:  # boundary converts every parse failure to a typed input error
            raise InvalidInputError("transport job content is not a valid pinned problem") from exc

    def execute(self, content: bytes, deadline):
        from logistics_contracts.runtime import JobResultRef

        try:
            payload = TransportJobContent.model_validate_json(content)
            problem = payload.problem.to_domain()
            requested = payload.budget.to_domain()
        except Exception:
            problem = TransportProblemDTO.model_validate_json(content).to_domain()
            requested = None
        solution = OrToolsTransportSolver().solve(problem,
            problem_budget(problem, deadline, requested))
        result_id = uuid4()
        digest = self.result_store.write(result_id, json.loads(
            solution_dto(solution).model_dump_json()))
        return JobResultRef(result_id=result_id, version=1, schema_version="2.0.0",
                            hash=digest, family=JobKind.OPTIMIZATION)


def problem_budget(problem: TransportProblem, deadline, requested=None) -> SolveBudget:
    """Use the request budget, capped by the deadline and a 5s server limit."""
    cap = requested.wall_time_ms if requested is not None else 5_000
    remaining = max(1, min(5_000, int((deadline.expires_at_utc - _now()).total_seconds() * 1000)))
    wall_time_ms = max(1, min(cap, remaining, 5_000))
    return SolveBudget(wall_time_ms=wall_time_ms, deadline_utc=deadline.expires_at_utc,
        max_candidates=1, seed=requested.seed if requested is not None else 0,
        worker_count=1, deterministic_test_mode=False)


class TransportResultStore:
    """Read immutable result artifacts; hash is verified against the job reference."""

    def __init__(self, result_store: ResultArtifactStore | None = None):
        self.result_store = result_store or ResultArtifactStore()

    def read(self, job) -> TransportSolutionDTO:
        from logistics_backend.errors import ServiceError
        from logistics_domain.states import ErrorCode, JobStatus

        if job.status != JobStatus.COMPLETED or job.result_ref is None:
            raise ServiceError(ErrorCode.RESULT_NOT_READY, "job result is not ready")
        payload = self.result_store.read(job.result_ref.result_id, job.result_ref.hash)
        return TransportSolutionDTO.model_validate_json(payload)


class TransportOptimizationService:
    def __init__(self, snapshot_store, job_service):
        self.snapshot_store = snapshot_store
        self.job_service = job_service

    def submit(self, request: TransportRequestDTO, actor, key: str, trace_id: UUID):
        snapshot = self.snapshot_store.capture(request.scope.to_domain())
        problem = build_transport_problem(snapshot, request)
        content = canonical_bytes(json.loads(TransportJobContent(
            problem=problem_dto(problem), budget=request.budget).model_dump_json()))
        request_id, version = uuid4(), 1
        digest = hashlib.sha256(content).hexdigest()
        reference = RequestRef(request_id=request_id, version=version, schema_version="2.0.0",
                               hash=digest, family=JobKind.OPTIMIZATION)
        self.job_service.store_request(reference, content, actor)
        deadline = _now() + timedelta(seconds=55)
        command = JobRequest(schema_version="2.0.0", kind=JobKind.OPTIMIZATION,
            payload=OptimizationJobPayload(family="optimization",
                request_ref=RequestRefDTO(request_id=request_id, version=version,
                    schema_version="2.0.0", hash=digest, family=JobKind.OPTIMIZATION),
                mode=JobOptimizationMode.TRANSPORT),
            deadline_utc=deadline)
        return self.job_service.submit(command, actor, key, trace_id)
