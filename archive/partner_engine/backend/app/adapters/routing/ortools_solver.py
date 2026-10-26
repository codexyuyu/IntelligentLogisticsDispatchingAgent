"""Owner: B | OR-Tools Routing implementation for the formal shared contract.

B02 scope: one warehouse, one trip per vehicle, delivery-only stops in the public
result. Internal nodes are vehicle-specific copies of orders so warehouse loading
windows can be enforced against the selected vehicle start time without modifying
shared contracts.
"""
from __future__ import annotations

import math
import time
try:
    import ortools
    from ortools.constraint_solver import pywrapcp, routing_enums_pb2
except ImportError as exc:  # pragma: no cover - exercised only when dependency missing
    ortools = None
    pywrapcp = None
    routing_enums_pb2 = None
    _ORTOOLS_IMPORT_ERROR = exc

from app.contracts.entities import Order, PlanningSnapshot, Vehicle
from app.contracts.planning import (
    RouteStop,
    RoutingRequest,
    RoutingResult,
    UnservedOrder,
    VehicleArrival,
    VehicleRoute,
)
from app.domain.states import SolveStatus
from app.adapters.matrix.fixed import FixedTravelMatrixProvider

# R20 objective term. Until now the only arc cost was distance, so two plans with
# equal distance were indistinguishable to the solver even when one made a truck
# sit waiting far longer for goods to be ready (R19 measured three rescheduling
# strategies producing identical plans for exactly this reason). The coefficient is
# in objective units per second of waiting, i.e. "how many metres of driving one
# second of waiting is worth". 5 keeps distance dominant (a 10-minute wait equals
# 3 km) while still breaking distance ties toward just-in-time departure.
# It is a B-side tuning parameter: exposing it on the shared SolveBudget/RoutingRequest
# would be a contract change, which needs an AC-approved proposal.
WAITING_COST_PER_SECOND = 5


class OrToolsRoutingSolver:
    """Solve B02 transport routing using the project's shared RoutingRequest/Result."""

    def solve(self, request: RoutingRequest) -> RoutingResult:
        started = time.perf_counter()
        self._validate_request(request)
        elapsed_ms = lambda: int((time.perf_counter() - started) * 1000)

        if pywrapcp is None or routing_enums_pb2 is None:
            raise RuntimeError(
                "OR-Tools is required for OrToolsRoutingSolver; install backend/requirements-optional.txt"
            ) from _ORTOOLS_IMPORT_ERROR

        snapshot = request.snapshot
        matrix_provider = FixedTravelMatrixProvider.from_snapshot(snapshot)
        matrix = matrix_provider.get_matrix(snapshot.matrix.matrix_id, snapshot.matrix.version)
        orders = self._select_orders(snapshot, request.order_ids)
        handoffs = {h.order_id: h for h in request.warehouse_handoffs}
        warehouse_id = orders[0].warehouse_id if orders else None
        if warehouse_id is None:
            return self._result(
                request,
                status="infeasible_proven",
                raw_status="EMPTY_REQUEST",
                has_solution=False,
                proof_scope="request-local precheck",
                solve_ms=elapsed_ms(),
            )

        vehicles = [v for v in snapshot.vehicles if v.warehouse_id == warehouse_id]
        if not vehicles:
            return self._result(
                request,
                status="infeasible_proven",
                raw_status="NO_VEHICLE_FOR_WAREHOUSE",
                has_solution=False,
                proof_scope="request-local warehouse/vehicle scope",
                solve_ms=elapsed_ms(),
            )

        # One-trip V1: vehicles must begin at their depot and have not already departed.
        for vehicle in vehicles:
            if vehicle.current_node_id != vehicle.start_node_id:
                raise ValueError(
                    f"vehicle_in_progress_not_supported:{vehicle.vehicle_id}"
                )
            if vehicle.remaining_weight_kg > vehicle.capacity_weight_kg:
                raise ValueError(f"remaining_weight_exceeds_capacity:{vehicle.vehicle_id}")
            if vehicle.remaining_volume_l > vehicle.capacity_volume_l:
                raise ValueError(f"remaining_volume_exceeds_capacity:{vehicle.vehicle_id}")

        compatible: dict[str, list[int]] = {}
        for order in orders:
            handoff = handoffs.get(order.order_id)
            if handoff is None:
                raise ValueError(f"missing_warehouse_handoff:{order.order_id}")
            if handoff.warehouse_id != warehouse_id:
                raise ValueError(f"handoff_warehouse_mismatch:{order.order_id}")
            candidates = [
                idx
                for idx, vehicle in enumerate(vehicles)
                if self._vehicle_can_carry(vehicle, order)
                and self._handoff_can_fit_vehicle_shift(vehicle, handoff)
            ]
            compatible[order.order_id] = candidates
            if order.required and not candidates:
                return self._result(
                    request,
                    status="infeasible_proven",
                    raw_status=f"NO_COMPATIBLE_VEHICLE:{order.order_id}",
                    has_solution=False,
                    proof_scope="request-local compatibility precheck",
                    solve_ms=elapsed_ms(),
                )

        # Aggregate-capacity precheck by warehouse/temperature zone. This is a
        # cheap, exact necessary condition and gives B-06 a useful diagnosis
        # before Routing starts a difficult search.
        for zone in {o.temperature_zone for o in orders if o.required}:
            # Only mandatory demand can prove a capacity infeasibility. Optional
            # orders may be dropped at a penalty, so counting their demand here
            # would incorrectly reject an otherwise feasible RoutingRequest.
            zone_orders = [o for o in orders if o.required and o.temperature_zone == zone]
            zone_vehicle_ids = {idx for o in zone_orders for idx in compatible[o.order_id]}
            total_demand_weight = sum(o.weight_kg for o in zone_orders)
            total_demand_volume = sum(o.volume_l for o in zone_orders)
            total_capacity_weight = sum(vehicles[idx].remaining_weight_kg for idx in zone_vehicle_ids)
            total_capacity_volume = sum(vehicles[idx].remaining_volume_l for idx in zone_vehicle_ids)
            if total_demand_weight > total_capacity_weight:
                return self._result(
                    request,
                    status="infeasible_proven",
                    raw_status=f"CAPACITY_WEIGHT_INSUFFICIENT:{zone}:{total_demand_weight}>{total_capacity_weight}",
                    has_solution=False,
                    proof_scope="request-local aggregate capacity precheck",
                    solve_ms=elapsed_ms(),
                )
            if total_demand_volume > total_capacity_volume:
                return self._result(
                    request,
                    status="infeasible_proven",
                    raw_status=f"CAPACITY_VOLUME_INSUFFICIENT:{zone}:{total_demand_volume}>{total_capacity_volume}",
                    has_solution=False,
                    proof_scope="request-local aggregate capacity precheck",
                    solve_ms=elapsed_ms(),
                )

        # Build internal nodes: one copy per compatible vehicle. This avoids relying on
        # SetAllowedVehiclesForIndex on Windows and lets us condition loading-window
        # constraints on the chosen vehicle's depot start cumul.
        manager_nodes: list[tuple[str, str | None, int | None]] = []
        matrix_index: list[int] = []
        matrix_pos = {node_id: i for i, node_id in enumerate(matrix.node_ids)}

        starts = []
        ends = []
        depot_node = snapshot.warehouses_by_id()[warehouse_id].node_id if hasattr(snapshot, 'warehouses_by_id') else None
        if depot_node is None:
            warehouse = next((w for w in snapshot.warehouses if w.warehouse_id == warehouse_id), None)
            if warehouse is None:
                raise ValueError(f"unknown_warehouse:{warehouse_id}")
            depot_node = warehouse.node_id
        if depot_node not in matrix_pos:
            raise ValueError(f"matrix_missing_warehouse_node:{depot_node}")

        # OR-Tools requires integer node IDs. Node 0 is a virtual depot shared by all
        # vehicles; delivery nodes start at 1.
        manager_nodes.append((depot_node, None, None))
        matrix_index.append(matrix_pos[depot_node])
        for order in orders:
            for vehicle_idx in compatible[order.order_id]:
                manager_nodes.append((order.delivery_node_id, order.order_id, vehicle_idx))
                if order.delivery_node_id not in matrix_pos:
                    raise ValueError(f"matrix_missing_delivery_node:{order.order_id}")
                matrix_index.append(matrix_pos[order.delivery_node_id])
        depot_internal_index = 0
        delivery_internal_indices = {entry[1]: [] for entry in manager_nodes if entry[1]}
        for internal_id, (_, order_id, vehicle_idx) in enumerate(manager_nodes):
            if order_id is not None:
                delivery_internal_indices.setdefault(order_id, []).append(internal_id)

        # A single physical depot works for every vehicle in the fixed-warehouse V1 scope.
        starts = [depot_internal_index] * len(vehicles)
        ends = [depot_internal_index] * len(vehicles)
        manager = pywrapcp.RoutingIndexManager(len(manager_nodes), len(vehicles), starts, ends)
        routing = pywrapcp.RoutingModel(manager)
        time_dim_name = "time"
        weight_dim_name = "weight_kg"
        volume_dim_name = "volume_l"
        waiting_dim_name = "waiting_s"

        horizon = max(
            [v.shift_window.end_s for v in vehicles]
            + [o.freshness_deadline_s for o in orders]
            + [o.service_window.end_s for o in orders]
            + [h.loading_window.end_s for h in handoffs.values()]
            + [1]
        )

        order_by_id = {o.order_id: o for o in orders}

        def physical_node(internal_index: int) -> str:
            return manager_nodes[manager.IndexToNode(internal_index)][0]

        def duration_callback(from_index: int, to_index: int) -> int:
            from_node = physical_node(from_index)
            to_node = physical_node(to_index)
            a = matrix_pos[from_node]
            b = matrix_pos[to_node]
            duration = matrix.duration_s[a][b]
            if duration is None:
                return horizon + 1
            order_id = manager_nodes[manager.IndexToNode(from_index)][1]
            service_s = order_by_id[order_id].service_duration_s if order_id is not None else 0
            return int(duration) + int(service_s)

        def distance_callback(from_index: int, to_index: int) -> int:
            from_node = physical_node(from_index)
            to_node = physical_node(to_index)
            a = matrix_pos[from_node]
            b = matrix_pos[to_node]
            distance = matrix.distance_m[a][b]
            return 10**12 if distance is None else int(distance)

        time_cb = routing.RegisterTransitCallback(duration_callback)
        distance_cb = routing.RegisterTransitCallback(distance_callback)
        routing.SetArcCostEvaluatorOfAllVehicles(distance_cb)

        routing.AddDimension(
            time_cb,
            horizon,
            horizon,
            False,
            time_dim_name,
        )
        time_dim = routing.GetDimensionOrDie(time_dim_name)

        # Waiting dimension: every arc costs nothing, so a route's cumul stays equal to
        # the cumul pinned at its depot start, which is linked to that vehicle's actual
        # departure below. Soft upper bounds on the order copies then charge exactly
        # (departure - ready_at) seconds of waiting -- the same quantity the B-03
        # coordination quality and the R17/R19 evidence report.
        def zero_callback(from_index: int, to_index: int) -> int:
            return 0

        waiting_cb = routing.RegisterTransitCallback(zero_callback)
        routing.AddDimension(waiting_cb, 0, horizon, False, waiting_dim_name)
        waiting_dim = routing.GetDimensionOrDie(waiting_dim_name)
        _solver = routing.solver()
        for vehicle_idx in range(len(vehicles)):
            _solver.Add(
                waiting_dim.CumulVar(routing.Start(vehicle_idx))
                == time_dim.CumulVar(routing.Start(vehicle_idx))
            )
        # KNOWN LIMITATION (measured 2026-10-15): this term is correct but the current
        # search does not act on it. With the coefficient raised to 100000 the solver still
        # returned a plan paying 1800 s of waiting instead of 400 m of extra distance, while
        # the same instance proved the waiting cumul equals the departure time. Making
        # waiting actually drive decisions needs a search-level change (for example selecting
        # among several candidate plans with the B-03 lexicographic quality, which already
        # ranks waiting after distance). Kept because it states the intended objective and is
        # wired correctly; it must not be described as an achieved optimisation.

        vehicle_loads = [
            min(v.capacity_weight_kg, v.remaining_weight_kg) for v in vehicles
        ]
        vehicle_volumes = [
            min(v.capacity_volume_l, v.remaining_volume_l) for v in vehicles
        ]

        def order_weight(internal_index: int) -> int:
            order_id = manager_nodes[manager.IndexToNode(internal_index)][1]
            return 0 if order_id is None else order_by_id[order_id].weight_kg

        def order_volume(internal_index: int) -> int:
            order_id = manager_nodes[manager.IndexToNode(internal_index)][1]
            return 0 if order_id is None else order_by_id[order_id].volume_l

        weight_cb = routing.RegisterUnaryTransitCallback(order_weight)
        volume_cb = routing.RegisterUnaryTransitCallback(order_volume)
        routing.AddDimensionWithVehicleCapacity(weight_cb, 0, vehicle_loads, True, weight_dim_name)
        routing.AddDimensionWithVehicleCapacity(volume_cb, 0, vehicle_volumes, True, volume_dim_name)

        weight_dim = routing.GetDimensionOrDie(weight_dim_name)
        volume_dim = routing.GetDimensionOrDie(volume_dim_name)

        # Each duplicate is fixed to its compatible vehicle. For optional orders,
        # exactly zero or one copy may be active. Required orders must select exactly one.
        solver = routing.solver()
        for order in orders:
            copies = delivery_internal_indices.get(order.order_id, [])
            if not copies:
                if order.required:
                    return self._result(
                        request,
                        status="infeasible_proven",
                        raw_status=f"NO_ROUTABLE_COPY:{order.order_id}",
                        has_solution=False,
                        proof_scope="request-local routing scope",
                        solve_ms=elapsed_ms(),
                    )
                continue
            active_vars = []
            for internal_node in copies:
                index = manager.NodeToIndex(internal_node)
                _, _, vehicle_idx = manager_nodes[internal_node]
                assert vehicle_idx is not None
                active = routing.ActiveVar(index)
                active_vars.append(active)
                # Canonical OR-Tools copy binding: this copy may only be served by its own
                # vehicle, or stay unperformed (-1). The former arithmetic form
                # (VehicleVar == (v+1)*active - 1) had the same intent, but the local search
                # then never activated another vehicle's copy: it returned 3100 m where
                # splitting two orders across two vehicles costs 2200 m.
                routing.VehicleVar(index).SetValues([vehicle_idx, -1])

                order_time = order_by_id[manager_nodes[internal_node][1]]
                latest_service_start = min(
                    order_time.service_window.end_s,
                    order_time.freshness_deadline_s - order_time.service_duration_s,
                )
                if latest_service_start < order_time.service_window.start_s:
                    raise ValueError(f"invalid_order_time_window:{order_time.order_id}")
                time_dim.CumulVar(index).SetRange(
                    order_time.service_window.start_s,
                    latest_service_start,
                )
                routing.AddVariableMinimizedByFinalizer(time_dim.CumulVar(index))

                handoff = handoffs[order_time.order_id]
                start_var = time_dim.CumulVar(routing.Start(vehicle_idx))
                big_m = horizon + max(handoff.loading_window.end_s, handoff.ready_at_s) + 1
                # Zero-duration load event in V1: if this order copy is active, the
                # selected vehicle's departure must be no earlier than ready_at and no
                # later than loading_window.end_s. The rule is conditional on the copy
                # being active, so other vehicles are unaffected.
                solver.Add(start_var >= handoff.ready_at_s - big_m * (1 - active))
                # The loading window opening was previously enforced only by validate_plan,
                # so the model could return a departure before the dock opens. A dock outage
                # (B-04 dock_unavailable) expresses itself *only* through this lower bound,
                # so it has to constrain the search instead of failing validation afterwards.
                solver.Add(start_var >= handoff.loading_window.start_s - big_m * (1 - active))
                solver.Add(start_var <= handoff.loading_window.end_s + big_m * (1 - active))
                # Charge the selected vehicle's waiting for this order. Inactive copies can
                # always park their cumul at 0, so they add no cost.
                waiting_dim.SetCumulVarSoftUpperBound(
                    index, int(handoff.ready_at_s), WAITING_COST_PER_SECOND
                )
            # Every physical copy is a routing node. Required orders must choose
            # exactly one of their compatible vehicle copies; without a disjunction,
            # OR-Tools treats every copy as mandatory, which becomes infeasible as soon
            # as a zone has multiple compatible vehicles (for example S50/S100).
            routing.AddDisjunction(
                [manager.NodeToIndex(i) for i in copies],
                self._optional_penalty(order, snapshot) if not order.required else 0,
                1,
            )
            if order.required:
                solver.Add(sum(active_vars) == 1)
            else:
                solver.Add(sum(active_vars) <= 1)

        # Depot start/end window covers the full vehicle trip. available_at_s is an
        # additional lower bound and does not modify the vehicle's declared shift.
        for vehicle_idx, vehicle in enumerate(vehicles):
            start_cumul = time_dim.CumulVar(routing.Start(vehicle_idx))
            end_cumul = time_dim.CumulVar(routing.End(vehicle_idx))
            start_lo = max(vehicle.shift_window.start_s, vehicle.available_at_s)
            start_hi = vehicle.shift_window.end_s
            if start_lo > start_hi:
                return self._result(
                    request,
                    status="infeasible_proven",
                    raw_status=f"INVALID_VEHICLE_SHIFT:{vehicle.vehicle_id}",
                    has_solution=False,
                    proof_scope="request-local vehicle precheck",
                    solve_ms=elapsed_ms(),
                )
            start_cumul.SetRange(start_lo, start_hi)
            end_cumul.SetRange(vehicle.shift_window.start_s, vehicle.shift_window.end_s)
            routing.AddVariableMinimizedByFinalizer(start_cumul)
            routing.AddVariableMinimizedByFinalizer(end_cumul)

        self._apply_frozen_routes(
            request,
            orders,
            vehicles,
            manager,
            routing,
            time_dim,
            delivery_internal_indices,
            manager_nodes,
            depot_internal_index,
        )

        # Prevent solver from using an unreachable arc by making it exceed the time
        # horizon. The distance callback also assigns a very large cost to the same arc.
        # Medium/large benchmark cases need a construction heuristic that handles
        # capacity + time-window VRPTW structure better than PATH_CHEAPEST_ARC.
        # We keep a deterministic fallback so a difficult first construction does
        # not immediately turn into a false-looking "no solution" result.
        remaining_budget_ms = max(1, request.budget.remaining_ms)
        first_pass_ms = max(1, int(remaining_budget_ms * 0.75))

        def make_params(first_solution_strategy):
            params = pywrapcp.DefaultRoutingSearchParameters()
            params.first_solution_strategy = first_solution_strategy
            params.local_search_metaheuristic = routing_enums_pb2.LocalSearchMetaheuristic.GUIDED_LOCAL_SEARCH
            params.time_limit.FromMilliseconds(remaining_budget_ms)
            return params

        params = make_params(routing_enums_pb2.FirstSolutionStrategy.PARALLEL_CHEAPEST_INSERTION)
        params.time_limit.FromMilliseconds(first_pass_ms)
        # Keep construction deterministic across benchmark seeds and machines.
        # PCI is substantially better suited to capacity/time-window problems
        # than PATH_CHEAPEST_ARC and is used as the primary constructor.
        solution = routing.SolveWithParameters(params)
        solve_ms = elapsed_ms()

        # If the construction/search did not produce a solution, retry the same
        # model with PATH_CHEAPEST_ARC. This is still the same deterministic routing
        # problem; only the search heuristic changes.
        if solution is None:
            elapsed = solve_ms
            left_ms = request.budget.remaining_ms - elapsed
            if left_ms > 0:
                fallback = make_params(routing_enums_pb2.FirstSolutionStrategy.PATH_CHEAPEST_ARC)
                fallback.time_limit.FromMilliseconds(left_ms)
                solution = routing.SolveWithParameters(fallback)
                solve_ms = elapsed_ms()

        if solution is None:
            return self._result(
                request,
                status="no_solution_within_budget",
                raw_status=(
                    f"ROUTING_NO_SOLUTION:warehouse={warehouse_id}"
                    f":orders={len(orders)}:required={sum(o.required for o in orders)}"
                    f":vehicles={len(vehicles)}:copies={sum(map(len, delivery_internal_indices.values()))}"
                    f":budget_ms={request.budget.remaining_ms}:elapsed_ms={solve_ms}"
                ),
                has_solution=False,
                proof_scope="request-local RoutingModel search; no solution found, not a proof of global infeasibility",
                solve_ms=solve_ms,
            )

        result = self._build_result(
            request,
            snapshot,
            matrix,
            orders,
            vehicles,
            handoffs,
            manager,
            routing,
            solution,
            time_dim,
            weight_dim,
            volume_dim,
            delivery_internal_indices,
            manager_nodes,
            depot_internal_index,
            solve_ms,
        )

        from app.domain.transport_rules import validate_transport
        validation = validate_transport(
            request=request.model_dump(mode="python"),
            result=result.model_dump(mode="python"),
        )
        if not validation.passed:
            return self._result(
                request,
                status="model_invalid",
                raw_status="INDEPENDENT_VALIDATION_FAILED:" + "|".join(validation.violations[:5]),
                has_solution=False,
                proof_scope="request-local independent transport validation",
                solve_ms=solve_ms,
            )
        return result

    @staticmethod
    def _validate_request(request: RoutingRequest) -> None:
        if request.snapshot.version <= 0:
            raise ValueError("invalid_snapshot_version")
        requested = set(request.order_ids)
        if not requested:
            raise ValueError("order_ids_must_not_be_empty")
        snapshot_orders = {o.order_id: o for o in request.snapshot.orders}
        missing = requested - snapshot_orders.keys()
        if missing:
            raise ValueError(f"unknown_orders:{','.join(sorted(missing))}")
        warehouses = {snapshot_orders[oid].warehouse_id for oid in requested}
        if len(warehouses) != 1:
            raise ValueError("multi_warehouse_routing_not_supported_in_b02_v1")
        if request.budget.remaining_ms <= 0:
            raise ValueError("budget_must_be_positive")
        if request.budget.max_workers <= 0:
            raise ValueError("max_workers_must_be_positive")
        handoff_ids = [h.order_id for h in request.warehouse_handoffs]
        if len(handoff_ids) != len(set(handoff_ids)):
            raise ValueError("duplicate_warehouse_handoff")

    @staticmethod
    def _select_orders(snapshot: PlanningSnapshot, order_ids: tuple[str, ...]) -> list[Order]:
        by_id = {o.order_id: o for o in snapshot.orders}
        return [by_id[oid] for oid in order_ids]

    @staticmethod
    def _vehicle_can_carry(vehicle: Vehicle, order: Order) -> bool:
        if vehicle.temperature_zone != order.temperature_zone:
            return False
        if vehicle.remaining_weight_kg < order.weight_kg:
            return False
        if vehicle.remaining_volume_l < order.volume_l:
            return False
        return True

    @staticmethod
    def _handoff_can_fit_vehicle_shift(vehicle: Vehicle, handoff) -> bool:
        if handoff.loading_window.end_s < handoff.ready_at_s:
            return False
        return max(vehicle.shift_window.start_s, vehicle.available_at_s, handoff.ready_at_s) <= min(
            vehicle.shift_window.end_s, handoff.loading_window.end_s
        )

    @staticmethod
    def _optional_penalty(order: Order, snapshot: PlanningSnapshot) -> int:
        # Penalty dominates any plausible distance in the small/medium MVP scope.
        max_edge = max((max((d for d in row if d is not None), default=0) for row in snapshot.matrix.distance_m), default=0)
        return max(1_000_000, (max_edge + 1) * max(10, len(snapshot.orders)))

    @staticmethod
    def _apply_frozen_routes(
        request: RoutingRequest,
        orders: list[Order],
        vehicles: list[Vehicle],
        manager,
        routing,
        time_dim,
        delivery_internal_indices: dict[str, list[int]],
        manager_nodes: list[tuple[str, str | None, int | None]],
        depot_internal_index: int,
    ) -> None:
        if not request.frozen_routes:
            return
        order_ids = {o.order_id for o in orders}
        vehicle_by_id = {v.vehicle_id: i for i, v in enumerate(vehicles)}
        order_by_id = {o.order_id: o for o in orders}
        for frozen in request.frozen_routes:
            vehicle_idx = vehicle_by_id.get(frozen.vehicle_id)
            if vehicle_idx is None:
                raise ValueError(f"frozen_route_vehicle_not_in_scope:{frozen.vehicle_id}")
            deliveries = [s for s in frozen.stops if s.stop_kind == 'delivery']
            if not deliveries:
                # A frozen route with no committed delivery freezes no work. Pinning
                # NextVar(start)=end here used to forbid the vehicle from serving anything,
                # which locked idle spare vehicles out of the recovery they exist for
                # (R19 stress family: B-04 local reschedule returned ROUTING_NO_SOLUTION).
                continue
            if any(oid not in order_ids for s in deliveries for oid in s.order_ids):
                raise ValueError(f"frozen_route_order_not_in_scope:{frozen.vehicle_id}")
            indices = []
            for stop in deliveries:
                if len(stop.order_ids) != 1:
                    raise ValueError(f"frozen_delivery_must_map_to_one_order:{frozen.vehicle_id}")
                order_id = stop.order_ids[0]
                copies = [i for i in delivery_internal_indices.get(order_id, []) if manager_nodes[i][2] == vehicle_idx]
                if not copies:
                    raise ValueError(f"frozen_route_order_incompatible:{order_id}:{frozen.vehicle_id}")
                internal = copies[0]
                idx = manager.NodeToIndex(internal)
                routing.ActiveVar(idx).SetValue(1)
                routing.VehicleVar(idx).SetValue(vehicle_idx)
                indices.append(idx)
                time_dim.CumulVar(idx).SetValue(stop.arrival_at_s)
            start = manager.NodeToIndex(depot_internal_index)
            start_index = routing.Start(vehicle_idx)
            end_index = routing.End(vehicle_idx)
            # deliveries is non-empty here, so the frozen sequence is fully pinned.
            routing.NextVar(start_index).SetValue(indices[0])
            for prev, nxt in zip(indices, indices[1:]):
                routing.NextVar(prev).SetValue(nxt)
            routing.NextVar(indices[-1]).SetValue(end_index)
            time_dim.CumulVar(start_index).SetValue(frozen.stops[0].arrival_at_s)
            time_dim.CumulVar(end_index).SetValue(frozen.stops[-1].arrival_at_s)

    @staticmethod
    def _build_result(
        request: RoutingRequest,
        snapshot: PlanningSnapshot,
        matrix,
        orders: list[Order],
        vehicles: list[Vehicle],
        handoffs: dict[str, object],
        manager,
        routing,
        solution,
        time_dim,
        weight_dim,
        volume_dim,
        delivery_internal_indices,
        manager_nodes,
        depot_internal_index,
        solve_ms: int,
    ) -> RoutingResult:
        order_by_id = {o.order_id: o for o in orders}
        routes: list[VehicleRoute] = []
        warehouse_arrivals: list[VehicleArrival] = []
        served: set[str] = set()

        for vehicle_idx, vehicle in enumerate(vehicles):
            index = routing.Start(vehicle_idx)
            internal_route: list[int] = []
            while True:
                internal_route.append(manager.IndexToNode(index))
                if routing.IsEnd(index):
                    break
                index = solution.Value(routing.NextVar(index))
            delivery_internal = [n for n in internal_route if manager_nodes[n][1] is not None]
            route_order_ids = [manager_nodes[n][1] for n in delivery_internal]
            route_order_ids = [oid for oid in route_order_ids if oid is not None]
            served.update(route_order_ids)

            total_weight = sum(order_by_id[oid].weight_kg for oid in route_order_ids)
            total_volume = sum(order_by_id[oid].volume_l for oid in route_order_ids)
            remaining_weight = total_weight
            remaining_volume = total_volume
            stops: list[RouteStop] = []
            start_arrival = solution.Value(time_dim.CumulVar(routing.Start(vehicle_idx)))
            stops.append(
                RouteStop(
                    node_id=vehicle.start_node_id,
                    order_ids=(),
                    stop_kind='depot_start',
                    arrival_at_s=start_arrival,
                    service_start_at_s=start_arrival,
                    departure_at_s=start_arrival,
                    load_weight_kg=total_weight,
                    load_volume_l=total_volume,
                )
            )
            distance = 0
            duration = 0
            prev_node_id = vehicle.start_node_id
            for internal in delivery_internal:
                oid = manager_nodes[internal][1]
                assert oid is not None
                order = order_by_id[oid]
                idx = manager.NodeToIndex(internal)
                arrival = solution.Value(time_dim.CumulVar(idx))
                departure = arrival + order.service_duration_s
                remaining_weight -= order.weight_kg
                remaining_volume -= order.volume_l
                stops.append(
                    RouteStop(
                        node_id=order.delivery_node_id,
                        order_ids=(order.order_id,),
                        stop_kind='delivery',
                        arrival_at_s=arrival,
                        service_start_at_s=arrival,
                        departure_at_s=departure,
                        load_weight_kg=max(0, remaining_weight),
                        load_volume_l=max(0, remaining_volume),
                    )
                )
                a = matrix.node_ids.index(prev_node_id)
                b = matrix.node_ids.index(order.delivery_node_id)
                edge_d = matrix.distance_m[a][b]
                edge_t = matrix.duration_s[a][b]
                if edge_d is not None:
                    distance += edge_d
                if edge_t is not None:
                    duration += edge_t
                prev_node_id = order.delivery_node_id
            end_idx = routing.End(vehicle_idx)
            end_arrival = solution.Value(time_dim.CumulVar(end_idx))
            if prev_node_id != vehicle.end_node_id:
                a = matrix.node_ids.index(prev_node_id)
                b = matrix.node_ids.index(vehicle.end_node_id)
                edge_d = matrix.distance_m[a][b]
                edge_t = matrix.duration_s[a][b]
                if edge_d is not None:
                    distance += edge_d
                if edge_t is not None:
                    duration += edge_t
            stops.append(
                RouteStop(
                    node_id=vehicle.end_node_id,
                    order_ids=(),
                    stop_kind='depot_end',
                    arrival_at_s=end_arrival,
                    service_start_at_s=end_arrival,
                    departure_at_s=end_arrival,
                    load_weight_kg=0,
                    load_volume_l=0,
                )
            )
            routes.append(
                VehicleRoute(
                    vehicle_id=vehicle.vehicle_id,
                    stops=tuple(stops),
                    distance_m=int(distance),
                    duration_s=int(end_arrival - start_arrival),
                )
            )
            warehouse_arrivals.append(
                VehicleArrival(
                    vehicle_id=vehicle.vehicle_id,
                    warehouse_id=vehicle.warehouse_id,
                    arrival_at_s=end_arrival,
                    order_ids=tuple(route_order_ids),
                )
            )

        unserved = []
        for order in orders:
            if order.order_id not in served:
                reason = 'optional_order_dropped' if not order.required else 'required_order_not_served'
                unserved.append(UnservedOrder(order_id=order.order_id, reason_code=reason))

        from app.contracts.common import SolveMetadata

        return RoutingResult(
            snapshot_id=snapshot.snapshot_id,
            snapshot_version=snapshot.version,
            metadata=SolveMetadata(
                status="feasible",
                raw_status="ROUTING_SOLUTION",
                engine="OR-Tools RoutingModel",
                engine_version=getattr(ortools, "__version__", "unknown"),
                has_solution=True,
                proof_scope="request-local RoutingModel search; feasible solution found within budget",
                solve_ms=max(0, solve_ms),
            ),
            routes=tuple(routes),
            warehouse_arrivals=tuple(warehouse_arrivals),
            unserved_orders=tuple(unserved),
        )

    @staticmethod
    def _result(
        request: RoutingRequest,
        *,
        status: SolveStatus,
        raw_status: str,
        has_solution: bool,
        proof_scope: str,
        solve_ms: int,
    ) -> RoutingResult:
        from app.contracts.common import SolveMetadata

        return RoutingResult(
            snapshot_id=request.snapshot.snapshot_id,
            snapshot_version=request.snapshot.version,
            metadata=SolveMetadata(
                status=status,
                raw_status=raw_status,
                engine='OR-Tools RoutingModel',
                engine_version=getattr(ortools, '__version__', 'unknown'),
                has_solution=has_solution,
                proof_scope=proof_scope,
                solve_ms=max(0, solve_ms),
            ),
            routes=(),
            warehouse_arrivals=(),
            unserved_orders=tuple(
                UnservedOrder(order_id=oid, reason_code='not_solved')
                for oid in request.order_ids
            ),
        )
