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
        routes, cost, unserved, all_stops, soft_late = self._extract(problem, manager, routing, assignment, data)
        times = routing.GetDimensionOrDie("time")
        active = [i for i in range(len(problem.vehicles)) if routing.IsVehicleUsed(assignment, i)]
        makespan_s = (max(assignment.Value(times.CumulVar(routing.End(i))) for i in active)
                      - min(assignment.Value(times.CumulVar(routing.Start(i))) for i in active)) if active else 0
        plan = TransportPlan(routes=tuple(routes), unserved_order_ids=tuple(unserved), cost=cost)
        status = (SolveStatus.OPTIMAL
                  if routing.status() == routing_enums_pb2.RoutingSearchStatus.ROUTING_OPTIMAL
                  else SolveStatus.FEASIBLE)
        objective = self._objective(problem, cost, len(unserved), soft_late, makespan_s)
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

        # Search the same monetary model reported in CostBreakdown.  A zero
        # distance rate keeps distance as a deterministic tie-breaker.
        prices = {v.id: v for v in problem.snapshot.vehicles}
        for i, vehicle in enumerate(problem.vehicles):
            commercial = prices.get(vehicle.vehicle_id)
            rate = commercial.rate_cents_per_km if commercial else 0
            fixed = commercial.fixed_cost_cents if commercial else 0
            def arc_cost(from_index, to_index, *, unit_rate=rate):
                distance = distance_cb(from_index, to_index)
                if distance >= LARGE:
                    return LARGE
                return max(0, (distance * unit_rate + 500) // 1000) if unit_rate else distance
            idx = routing.RegisterTransitCallback(arc_cost)
            routing.SetArcCostEvaluatorOfVehicle(idx, i)
            if fixed:
                routing.SetFixedCostOfVehicle(fixed, i)
        travel_index = routing.RegisterTransitCallback(travel_cb)

        def weight_demand(from_index):
            node = manager.IndexToNode(from_index)
            return nodes[node].load_delta.weight_g if node < len(nodes) else 0

        def volume_demand(from_index):
            node = manager.IndexToNode(from_index)
            return nodes[node].load_delta.volume_cm3 if node < len(nodes) else 0

        weight_index = routing.RegisterUnaryTransitCallback(weight_demand)
        volume_index = routing.RegisterUnaryTransitCallback(volume_demand)
        # Actual onboard loads matter during a mid-route continuation.
        routing.AddDimensionWithVehicleCapacity(weight_index, 0,
            [v.capacity_weight_g for v in problem.vehicles], False, "weight")
        routing.AddDimensionWithVehicleCapacity(volume_index, 0,
            [v.capacity_volume_cm3 for v in problem.vehicles], False, "volume")
        for i, vehicle in enumerate(problem.vehicles):
            for dimension_name, start_load in (("weight", vehicle.start_load.weight_g),
                                               ("volume", vehicle.start_load.volume_cm3)):
                dim = routing.GetDimensionOrDie(dimension_name)
                if start_load > (vehicle.capacity_weight_g if dimension_name == "weight" else vehicle.capacity_volume_cm3):
                    raise InvalidInputError("initial vehicle load exceeds capacity")
                dim.CumulVar(routing.Start(i)).SetRange(start_load, start_load)

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

            if node.kind == RoutingNodeKind.DELIVERY and node.soft_due_at_s is not None:
                rate = max(0, problem.policy.soft_late_cents_per_s)
                if rate:
                    time_dimension.SetCumulVarSoftUpperBound(index, node.soft_due_at_s, rate)
        if problem.policy.makespan_cents_per_s > 0:
            time_dimension.SetGlobalSpanCostCoefficient(problem.policy.makespan_cents_per_s)

        # Pin cargo/temperature compatibility INSIDE the solver, not only in
        # post-validation. Empty allowed_cargo_types means no restricted list.
        cargo_by_order = {}
        for cargo in problem.snapshot.cargo:
            cargo_by_order.setdefault(cargo.order_id, []).append(cargo)
        for node_index, node in enumerate(nodes):
            if node.order_id is None:
                continue
            cargo = cargo_by_order.get(node.order_id, ())
            allowed = [i for i, vehicle in enumerate(problem.vehicles) if all(
                item.min_temp_decic <= vehicle.setpoint_decic <= item.max_temp_decic and
                (not vehicle.allowed_cargo_types or item.cargo_type in vehicle.allowed_cargo_types)
                for item in cargo)]
            idx = manager.NodeToIndex(node_index)
            # NOTE: this OR-Tools build does not expose a usable
            # `SetAllowedVehiclesForIndex` binding (it raises TypeError on any
            # list), so the same restriction is expressed with per-vehicle
            # inequalities. Semantics are identical: the node can only be served
            # by vehicles whose setpoint/cargo types are compatible, and an empty
            # allowed set makes the node unservable (hence infeasible unless a
            # disjunction deliberately drops it).
            allowed_set = set(allowed)
            for vehicle_index in range(len(problem.vehicles)):
                if vehicle_index not in allowed_set:
                    routing.solver().Add(routing.VehicleVar(idx) != vehicle_index)
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
            # A delivery without its pickup is legal in a continuation only:
            # cargo is already onboard and its start_load is pinned above.
            if "delivery" in pair and "pickup" not in pair:
                continue
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
        total_soft_late = 0
        now = _now()
        candidate_id = uuid4()
        for vehicle_index, vehicle in enumerate(problem.vehicles):
            route_id = uuid4()
            index = routing.Start(vehicle_index)
            stops: list[RouteStop] = []
            seq_nodes: list[int] = []
            route_distance = 0
            current_weight = vehicle.start_load.weight_g
            current_volume = vehicle.start_load.volume_cm3
            while not routing.IsEnd(index):
                node_index = manager.IndexToNode(index)
                next_index = assignment.Value(routing.NextVar(index))
                from_location = locations[manager.IndexToNode(index)]
                to_location = locations[manager.IndexToNode(next_index)]
                route_distance += _matrix_cell(problem.matrix, from_location, to_location, "distance")
                if node_index < len(nodes):
                    node = nodes[node_index]
                    seq_nodes.append(node_index)
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
            if stops:
                # The routing solution fixes the visit order; re-assign the times
                # as early as the real hard windows allow. OR-Tools may leave a
                # service exactly on its hard deadline (zero slack) when arc cost
                # dominates the objective, and such a plan turns every later
                # delay into a hard-window violation. This forward pass never
                # relaxes a window: it only picks the earliest legal times.
                start_location = locations[manager.IndexToNode(routing.Start(vehicle_index))]
                first_node = nodes[seq_nodes[0]]
                first_travel = _matrix_cell(problem.matrix, start_location,
                                            locations[seq_nodes[0]], "travel")
                depart = max(vehicle.available_window.earliest_s,
                             first_node.hard_window.earliest_s - first_travel)
                prev_location = start_location
                rebuilt: list[RouteStop] = []
                soft_late = 0
                for stop, nidx in zip(stops, seq_nodes):
                    node = nodes[nidx]
                    travel = _matrix_cell(problem.matrix, prev_location, locations[nidx], "travel")
                    arrival = depart + travel
                    service = max(arrival, node.hard_window.earliest_s)
                    if service > node.hard_window.latest_s:
                        # Cannot happen for a solution that passed validation; keep
                        # the solver value rather than inventing an infeasible time.
                        rebuilt.append(stop)
                    else:
                        rebuilt.append(replace(stop, arrival_s=arrival,
                                               service_start_s=service,
                                               departure_s=service + node.service_s))
                    if node.order_id is not None and node.kind == RoutingNodeKind.DELIVERY \
                            and node.soft_due_at_s is not None:
                        soft_late += max(0, service - node.soft_due_at_s) * max(
                            0, problem.policy.soft_late_cents_per_s)
                    depart = rebuilt[-1].departure_s
                    prev_location = locations[nidx]
                stops = rebuilt
                total_soft_late += soft_late
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
        return routes, cost, unserved, tuple(all_stops), total_soft_late

    def _objective(self, problem, cost, unserved, soft_late, makespan_s=0):
        penalty = unserved * problem.policy.optional_unserved_penalty_cents
        makespan = makespan_s * max(0, problem.policy.makespan_cents_per_s)
        total = cost.total_cents + penalty + soft_late + makespan
        return ObjectiveBreakdown(business_cost_cents=cost.total_cents,
            optional_unserved_penalty=penalty, soft_late_penalty=soft_late,
            disturbance_penalty=0, makespan_penalty=makespan, objective_total=total)

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
