"""OR-Tools transport solver (P07-01/P07-07).

The adapter owns OR-Tools objects internally. Pure domain values (`TransportProblem`,
`TransportSolution`) cross the boundary in both directions; no routing index or OR-Tools
object is returned to callers. One model covers all vehicles with capacity, pickup/delivery
pairing, hard service windows, driver duration and the vehicle temperature envelope.
"""

from __future__ import annotations

import time
from dataclasses import replace
from datetime import datetime, timezone
from uuid import UUID, uuid4

from ortools.constraint_solver import pywrapcp, routing_enums_pb2

from logistics_domain.errors import InvalidInputError
from logistics_domain.planning import (
    CostBreakdown,
    EngineMetadata,
    MatrixRef,
    ObjectiveBreakdown,
    Route,
    RouteStop,
    SolverEvidence,
    TransportPlan,
    content_hash,
)
from logistics_domain.primitives import Load
from logistics_domain.states import EntityState
from logistics_domain.planning import SolveStatus
from logistics_domain.transport import (
    Diagnostic,
    DiagnosticSeverity,
    RoutingNodeKind,
    TransportProblem,
    TransportSolution,
)

SYSTEM_ACTOR = UUID(int=0)
LARGE = 10**9


def _now() -> datetime:
    return datetime.now(timezone.utc).replace(microsecond=0)


def _matrix_cell(matrix, left: UUID, right: UUID, field: str) -> int:
    try:
        i = matrix.node_ids.index(left)
        j = matrix.node_ids.index(right)
    except ValueError as exc:
        raise InvalidInputError("matrix does not contain both node ids") from exc
    values = matrix.distance_m if field == "distance" else matrix.travel_s
    value = values[i][j]
    return LARGE if value is None else int(value)


class OrToolsTransportSolver:
    """Concrete ``TransportSolver`` protocol implementation."""

    def solve(self, problem: TransportProblem, budget) -> TransportSolution:
        started = time.monotonic()
        build_started = time.monotonic()
        manager, routing, data = self._build(problem)
        build_ms = int((time.monotonic() - build_started) * 1000)
        search = pywrapcp.DefaultRoutingSearchParameters()
        search.first_solution_strategy = routing_enums_pb2.FirstSolutionStrategy.PATH_CHEAPEST_ARC
        search.local_search_metaheuristic = routing_enums_pb2.LocalSearchMetaheuristic.GUIDED_LOCAL_SEARCH
        search.time_limit.FromMilliseconds(max(1, min(budget.wall_time_ms, 60_000)))
        assignment = routing.SolveWithParameters(search)
        solve_ms = int((time.monotonic() - started) * 1000)
        if assignment is None:
            timed_out = solve_ms >= min(budget.wall_time_ms, 60_000) - 50
            status = SolveStatus.TIMEOUT if timed_out else SolveStatus.INFEASIBLE
            return TransportSolution(
                status=status,
                engine_metadata=self._metadata(problem, status, solve_ms, build_ms, False),
                candidate=None, optional_unserved_order_ids=tuple(), objective=None,
                validation=None,
                diagnostics=(Diagnostic("transport_infeasible", DiagnosticSeverity.ERROR,
                                        "no feasible vehicle assignment was found"),),
                solver_evidence=(self._evidence(problem, status, ()),))
        routes, cost, unserved, all_stops = self._extract(problem, manager, routing, assignment, data)
        plan = TransportPlan(routes=tuple(routes), unserved_order_ids=tuple(unserved), cost=cost)
        status = (SolveStatus.OPTIMAL
                  if routing.status() == routing_enums_pb2.RoutingSearchStatus.ROUTING_OPTIMAL
                  else SolveStatus.FEASIBLE)
        objective = self._objective(problem, cost, len(unserved), 0)
        validation = self._validate(problem, plan, all_stops)
        metadata = self._metadata(problem, status, solve_ms, build_ms, True)
        return TransportSolution(status=status, engine_metadata=metadata, candidate=plan,
            optional_unserved_order_ids=tuple(unserved), objective=objective,
            validation=validation, diagnostics=(),
            solver_evidence=(self._evidence(problem, status, routes),), stops=all_stops)

    # ------------------------------------------------------------------ model

    def _build(self, problem: TransportProblem):
        matrix = problem.matrix
        nodes = list(problem.nodes)
        locations = [node.location_id for node in nodes]
        starts, ends = [], []
        for vehicle in problem.vehicles:
            starts.append(len(locations))
            locations.append(_location_for(problem, vehicle.start_node_id))
            ends.append(len(locations))
            locations.append(_location_for(problem, vehicle.end_node_id))
        manager = pywrapcp.RoutingIndexManager(len(locations), len(problem.vehicles), starts, ends)
        routing = pywrapcp.RoutingModel(manager)

        def distance_cb(from_index, to_index):
            from_node = manager.IndexToNode(from_index)
            to_node = manager.IndexToNode(to_index)
            return _matrix_cell(matrix, locations[from_node], locations[to_node], "distance")

        def travel_cb(from_index, to_index):
            from_node = manager.IndexToNode(from_index)
            to_node = manager.IndexToNode(to_index)
            return _matrix_cell(matrix, locations[from_node], locations[to_node], "travel")

        distance_index = routing.RegisterTransitCallback(distance_cb)
        routing.SetArcCostEvaluatorOfAllVehicles(distance_index)
        travel_index = routing.RegisterTransitCallback(travel_cb)

        def weight_demand(from_index):
            node = manager.IndexToNode(from_index)
            return nodes[node].load_delta.weight_g if node < len(nodes) else 0

        def volume_demand(from_index):
            node = manager.IndexToNode(from_index)
            return nodes[node].load_delta.volume_cm3 if node < len(nodes) else 0

        weight_index = routing.RegisterUnaryTransitCallback(weight_demand)
        volume_index = routing.RegisterUnaryTransitCallback(volume_demand)
        routing.AddDimensionWithVehicleCapacity(weight_index, 0,
            [max(0, vehicle.capacity_weight_g - vehicle.start_load.weight_g)
             for vehicle in problem.vehicles], True, "weight")
        routing.AddDimensionWithVehicleCapacity(volume_index, 0,
            [max(0, vehicle.capacity_volume_cm3 - vehicle.start_load.volume_cm3)
             for vehicle in problem.vehicles], True, "volume")

        def service_time_cb(from_index, to_index):
            from_node = manager.IndexToNode(from_index)
            to_node = manager.IndexToNode(to_index)
            service = nodes[from_node].service_s if from_node < len(nodes) else 0
            return _matrix_cell(matrix, locations[from_node], locations[to_node], "travel") + service

        time_index = routing.RegisterTransitCallback(service_time_cb)
        routing.AddDimension(time_index, 3600, 7 * 24 * 3600, False, "time")
        time_dimension = routing.GetDimensionOrDie("time")
        for node_index, node in enumerate(nodes):
            index = manager.NodeToIndex(node_index)
            time_dimension.CumulVar(index).SetRange(node.hard_window.earliest_s,
                                                    node.hard_window.latest_s)
        for vehicle_index, vehicle in enumerate(problem.vehicles):
            start_index = routing.Start(vehicle_index)
            end_index = routing.End(vehicle_index)
            time_dimension.CumulVar(start_index).SetRange(
                vehicle.available_window.earliest_s, vehicle.available_window.latest_s)
            time_dimension.CumulVar(end_index).SetRange(
                vehicle.available_window.earliest_s, vehicle.available_window.latest_s)
        routing.AddDimensionWithVehicleCapacity(travel_index, 0,
            [vehicle.max_drive_s for vehicle in problem.vehicles], True, "drive")

        pairs: dict[UUID, dict[str, int]] = {}
        for node_index, node in enumerate(nodes):
            if node.kind in (RoutingNodeKind.PICKUP, RoutingNodeKind.DELIVERY):
                pairs.setdefault(node.pair_id, {})[node.kind.value] = node_index
        for pair in pairs.values():
            if "pickup" not in pair or "delivery" not in pair:
                raise InvalidInputError("pickup/delivery pair is incomplete")
            pickup = manager.NodeToIndex(pair["pickup"])
            delivery = manager.NodeToIndex(pair["delivery"])
            routing.AddPickupAndDelivery(pickup, delivery)
            routing.solver().Add(routing.VehicleVar(pickup) == routing.VehicleVar(delivery))
            routing.solver().Add(time_dimension.CumulVar(pickup) <= time_dimension.CumulVar(delivery))
        return manager, routing, {"locations": locations, "nodes": nodes}

    def _extract(self, problem, manager, routing, assignment, data):
        nodes = data["nodes"]
        locations = data["locations"]
        time_dimension = routing.GetDimensionOrDie("time")
        weight_dimension = routing.GetDimensionOrDie("weight")
        vehicles = {vehicle.vehicle_id: vehicle for vehicle in problem.vehicles}
        snapshot_vehicles = {vehicle.id: vehicle for vehicle in problem.snapshot.vehicles}
        routes: list[Route] = []
        all_stops: list[RouteStop] = []
        visited_orders: set[UUID] = set()
        now = _now()
        candidate_id = uuid4()
        for vehicle_index, vehicle in enumerate(problem.vehicles):
            route_id = uuid4()
            index = routing.Start(vehicle_index)
            stops: list[RouteStop] = []
            route_distance = 0
            current_weight = vehicle.start_load.weight_g
            current_volume = vehicle.start_load.volume_cm3
            while not routing.IsEnd(index):
                node_index = manager.IndexToNode(index)
                next_index = assignment.Value(routing.NextVar(index))
                route_distance += routing.GetArcCostForVehicle(index, next_index, vehicle_index)
                if node_index < len(nodes):
                    node = nodes[node_index]
                    arrival = assignment.Value(time_dimension.CumulVar(index))
                    if node.order_id is not None and node.kind == RoutingNodeKind.DELIVERY:
                        visited_orders.add(node.order_id)
                    load_before = Load(current_weight, current_volume)
                    current_weight = max(0, current_weight + node.load_delta.weight_g)
                    current_volume = max(0, current_volume + node.load_delta.volume_cm3)
                    stops.append(RouteStop(
                        id=uuid4(), status=EntityState.PLANNED, created_at=now, updated_at=now,
                        row_version=0, schema_version="2.0.0", created_by=SYSTEM_ACTOR,
                        route_id=route_id, sequence=len(stops), node_id=node.id,
                        task_ids=(node.order_id or node.id,), arrival_s=arrival,
                        service_start_s=arrival, departure_s=arrival + node.service_s,
                        load_before=load_before,
                        load_after=Load(current_weight, current_volume)))
                index = next_index
            if not stops:
                continue
            all_stops.extend(stops)
            commercial = snapshot_vehicles.get(vehicle.vehicle_id)
            rate = commercial.rate_cents_per_km if commercial is not None else 0
            fixed = commercial.fixed_cost_cents if commercial is not None else 0
            distance_cents = (route_distance * rate + 500) // 1000
            service_cents = len(stops) * 100
            total = distance_cents + fixed + service_cents
            cost = CostBreakdown(distance_cents=distance_cents, fixed_vehicle_cents=fixed,
                service_cents=service_cents, overtime_cents=0, setup_cents=0, total_cents=total)
            routes.append(Route(
                id=route_id, status=EntityState.CANDIDATE, created_at=now, updated_at=now,
                row_version=0, schema_version="2.0.0", created_by=SYSTEM_ACTOR,
                version_id=candidate_id, vehicle_id=vehicle.vehicle_id,
                driver_id=vehicle.driver_id or vehicle.vehicle_id,
                start_node_id=vehicle.start_node_id, end_node_id=vehicle.end_node_id,
                total_distance_m=route_distance, cost=cost,
                matrix_ref=MatrixRef(matrix_id=problem.matrix.id,
                                     version=problem.matrix.version,
                                     hash=problem.matrix.hash)))
        order_ids = {node.order_id for node in problem.nodes
                     if node.order_id is not None and node.kind == RoutingNodeKind.PICKUP}
        unserved = tuple(sorted(order_ids - visited_orders, key=str))
        cost = CostBreakdown(
            distance_cents=sum(route.cost.distance_cents for route in routes),
            fixed_vehicle_cents=sum(route.cost.fixed_vehicle_cents for route in routes),
            service_cents=sum(route.cost.service_cents for route in routes),
            overtime_cents=0, setup_cents=0,
            total_cents=sum(route.cost.total_cents for route in routes))
        return routes, cost, unserved, tuple(all_stops)

    def _objective(self, problem, cost, unserved, soft_late):
        penalty = unserved * problem.policy.optional_unserved_penalty_cents
        total = cost.total_cents + penalty + soft_late
        return ObjectiveBreakdown(business_cost_cents=cost.total_cents,
            optional_unserved_penalty=penalty, soft_late_penalty=soft_late,
            disturbance_penalty=0, makespan_penalty=0, objective_total=total)

    def _validate(self, problem, plan, stops=()):
        from logistics_optimization.validation.transport import validate_transport

        return validate_transport(plan, problem, tuple(stops))

    def _metadata(self, problem, status, solve_ms, build_ms, incumbent):
        return EngineMetadata(name="ortools_routing", version="9",
            configuration_hash=content_hash({"strategy": "path_cheapest_arc+guided_local_search",
                                             "workers": 1}),
            seed=0, workers=1, input_hash=content_hash(problem), solve_ms=solve_ms,
            build_ms=build_ms, engine_status=status.value, incumbent_exists=incumbent,
            best_bound=None, optimality_gap=None)

    def _evidence(self, problem, status, routes):
        return SolverEvidence(id=uuid4(), engine_name="routing", engine_version="9",
            input_hash=content_hash(problem), assignment_hash=content_hash(tuple(routes)),
            configuration_hash=content_hash({"strategy": "path_cheapest_arc+guided_local_search"}),
            solve_status=status, trusted_job_id=None)


def _location_for(problem: TransportProblem, node_id: UUID) -> UUID:
    for node in problem.nodes:
        if node.id == node_id:
            return node.location_id
    return node_id
