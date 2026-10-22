"""OR-Tools CP-SAT warehouse scheduler migrated from legacy B-01.

The current team contract models warehouse work as Operations assigned to
WarehouseResource instances. This adapter therefore keeps the proven CP-SAT
pattern from the legacy algorithm-service while obeying the new contract
semantics: release/deadline windows, precedence, resource availability,
frozen facts and non-overlap. Temperature/quantity-specific rules that are not
represented by the shared contract are intentionally not guessed here.
"""
from __future__ import annotations

import time
from importlib.metadata import PackageNotFoundError, version as package_version

try:
    from ortools.sat.python import cp_model
except ImportError as exc:  # pragma: no cover
    cp_model = None
    _ORTOOLS_IMPORT_ERROR = exc

from app.contracts.planning import WarehouseScheduleRequest, WarehouseScheduleResult, WarehouseHandoff, VehicleArrival
from app.contracts.common import SolveMetadata, TimeWindow
from app.contracts.entities import ScheduledOperation
from app.domain.states import SolveStatus
from app.adapters.warehouse.validator import WarehouseScheduleValidator


def _ortools_version() -> str:
    try:
        return package_version("ortools")
    except PackageNotFoundError:
        return "unknown"


def _metadata(*, status: SolveStatus, raw_status: str, has_solution: bool,
              proof_scope: str, solve_ms: int) -> SolveMetadata:
    return SolveMetadata(
        status=status,
        raw_status=raw_status,
        engine="OR-Tools CP-SAT",
        engine_version=_ortools_version(),
        has_solution=has_solution,
        proof_scope=proof_scope,
        solve_ms=max(0, int(solve_ms)),
    )


class CpSatWarehouseScheduler:
    """Formal WarehouseScheduler implementation using OR-Tools CP-SAT."""

    def schedule(self, request: WarehouseScheduleRequest) -> WarehouseScheduleResult:
        started = time.perf_counter()
        self._validate_request(request)

        if cp_model is None:
            raise RuntimeError(
                "OR-Tools is required for CpSatWarehouseScheduler; "
                "install backend/requirements-optional.txt"
            ) from _ORTOOLS_IMPORT_ERROR

        snapshot = request.snapshot
        selected_orders = {oid for oid in request.order_ids}
        orders = [o for o in snapshot.orders if o.order_id in selected_orders]
        operations = [
            op for op in snapshot.operations
            if not op.order_ids or any(order_id in selected_orders for order_id in op.order_ids)
        ]
        resources = list(snapshot.resources)

        if not operations:
            return WarehouseScheduleResult(
                snapshot_id=snapshot.snapshot_id,
                snapshot_version=snapshot.version,
                metadata=_metadata(
                    status="optimal",
                    raw_status="EMPTY_OPERATION_SET",
                    has_solution=True,
                    proof_scope="request-local empty operation set",
                    solve_ms=_elapsed_ms(started),
                ),
                operations=(),
                warehouse_handoffs=self._build_handoffs(orders, (), {}),
            )

        if not resources:
            return WarehouseScheduleResult(
                snapshot_id=snapshot.snapshot_id,
                snapshot_version=snapshot.version,
                metadata=_metadata(
                    status="infeasible_proven",
                    raw_status="NO_WAREHOUSE_RESOURCE",
                    has_solution=False,
                    proof_scope="request-local resource precheck",
                    solve_ms=_elapsed_ms(started),
                ),
                operations=(),
                warehouse_handoffs=(),
            )

        resource_by_id = {r.resource_id: r for r in resources}
        resources_by_warehouse: dict[str, list] = {}
        for resource in resources:
            resources_by_warehouse.setdefault(resource.warehouse_id, []).append(resource)

        # Fixed facts from the snapshot must never be re-planned.
        frozen_by_op = {op.operation_id: op for op in snapshot.frozen_operations}
        frozen_intervals: dict[str, list[tuple[int, int, str]]] = {}
        for frozen in snapshot.frozen_operations:
            if frozen.resource_id not in resource_by_id:
                return self._infeasible(request, started, f"UNKNOWN_FROZEN_RESOURCE:{frozen.resource_id}")
            frozen_intervals.setdefault(frozen.resource_id, []).append(
                (frozen.start_s, frozen.end_s, frozen.operation_id)
            )

        model = cp_model.CpModel()
        horizon = max(
            [op.deadline_at_s for op in operations]
            + [tw.end_s for r in resources for tw in r.available_windows]
            + [tw.end_s for r in resources for tw in r.unavailable_windows]
            + [s.end_s for s in snapshot.frozen_operations]
            + [request.budget.remaining_ms // 1000 + snapshot.simulation_time_s + 1]
            + [1]
        )

        start_vars: dict[str, object] = {}
        end_vars: dict[str, object] = {}
        assignments: dict[str, dict[str, object]] = {}
        intervals_by_resource: dict[str, list[object]] = {r.resource_id: [] for r in resources}
        op_duration: dict[str, int] = {}

        for op in operations:
            if op.operation_id in frozen_by_op:
                frozen = frozen_by_op[op.operation_id]
                if frozen.end_s <= frozen.start_s:
                    return self._infeasible(request, started, f"INVALID_FROZEN_OPERATION:{op.operation_id}")
                start_vars[op.operation_id] = None
                end_vars[op.operation_id] = None
                op_duration[op.operation_id] = frozen.end_s - frozen.start_s
                continue

            duration = int(op.duration_s)
            op_duration[op.operation_id] = duration
            if op.release_at_s + duration > op.deadline_at_s:
                return self._infeasible(request, started, f"OPERATION_WINDOW_TOO_TIGHT:{op.operation_id}")

            candidate_resources = resources_by_warehouse.get(op.warehouse_id, [])
            if not candidate_resources:
                return self._infeasible(request, started, f"NO_RESOURCE_FOR_WAREHOUSE:{op.operation_id}")

            # Domain contracts only expose generic resource capacity, not per-operation
            # demand. We therefore treat capacity as a resource eligibility signal (>0)
            # and leave quantity/temperature matching to domain validation upstream.
            candidate_resources = [r for r in candidate_resources if r.capacity_units > 0]
            # R27 business operation standards name an explicit physical resource.
            # Earlier synthetic snapshots intentionally retain flexible assignment.
            if snapshot.rule_version == 'pg-r27-verified':
                candidate_resources = [r for r in candidate_resources if r.resource_id == op.resource_id]
            if not candidate_resources:
                return self._infeasible(request, started, f"NO_CAPABLE_RESOURCE:{op.operation_id}")

            upper = min(op.deadline_at_s - duration, horizon - duration)
            start = model.NewIntVar(op.release_at_s, upper, f"start_{op.operation_id}")
            end = model.NewIntVar(op.release_at_s + duration, horizon, f"end_{op.operation_id}")
            model.Add(end == start + duration)
            start_vars[op.operation_id] = start
            end_vars[op.operation_id] = end

            present_vars: dict[str, object] = {}
            for resource in candidate_resources:
                present = model.NewBoolVar(f"assign_{op.operation_id}_{resource.resource_id}")
                interval = model.NewOptionalIntervalVar(
                    start, duration, end, present, f"interval_{op.operation_id}_{resource.resource_id}"
                )
                present_vars[resource.resource_id] = present
                intervals_by_resource[resource.resource_id].append(interval)

                # Assignment implies the operation is fully contained in at least one
                # available resource window.
                if len(resource.available_windows) > 1:
                    window_literals = []
                    for window_idx, window in enumerate(resource.available_windows):
                        lit = model.NewBoolVar(
                            f"{op.operation_id}_{resource.resource_id}_window_{window_idx}"
                        )
                        model.Add(start >= window.start_s).OnlyEnforceIf(lit)
                        model.Add(end <= window.end_s).OnlyEnforceIf(lit)
                        model.AddImplication(lit, present)
                        window_literals.append(lit)
                    model.AddBoolOr(window_literals).OnlyEnforceIf(present)
                elif len(resource.available_windows) == 1:
                    window = resource.available_windows[0]
                    model.Add(start >= window.start_s).OnlyEnforceIf(present)
                    model.Add(end <= window.end_s).OnlyEnforceIf(present)
                else:
                    model.Add(present == 0)

                for unavailable in resource.unavailable_windows:
                    before = model.NewBoolVar(
                        f"{op.operation_id}_{resource.resource_id}_before_unavail_{unavailable.start_s}"
                    )
                    after = model.NewBoolVar(
                        f"{op.operation_id}_{resource.resource_id}_after_unavail_{unavailable.end_s}"
                    )
                    model.Add(end <= unavailable.start_s).OnlyEnforceIf(before)
                    model.Add(start >= unavailable.end_s).OnlyEnforceIf(after)
                    model.AddBoolOr([before, after]).OnlyEnforceIf(present)

            model.AddExactlyOne(present_vars.values())
            assignments[op.operation_id] = present_vars

        # Non-overlap for both planned and frozen operations on each resource.
        for resource_id, intervals in intervals_by_resource.items():
            if intervals:
                model.AddNoOverlap(intervals)
            for start, end, frozen_id in frozen_intervals.get(resource_id, []):
                for op in operations:
                    if op.operation_id in frozen_by_op:
                        continue
                    if op.operation_id not in assignments:
                        continue
                    guard = assignments[op.operation_id].get(resource_id)
                    if guard is None:
                        continue
                    before = model.NewBoolVar(f"{op.operation_id}_{resource_id}_before_{frozen_id}")
                    after = model.NewBoolVar(f"{op.operation_id}_{resource_id}_after_{frozen_id}")
                    model.Add(end_vars[op.operation_id] <= start).OnlyEnforceIf(before)
                    model.Add(start_vars[op.operation_id] >= end).OnlyEnforceIf(after)
                    model.AddBoolOr([before, after]).OnlyEnforceIf(guard)

        # Precedence inside warehouse work.
        op_map = {op.operation_id: op for op in operations}
        for op in operations:
            current_start = start_vars[op.operation_id]
            if current_start is None:
                current_start_value = frozen_by_op[op.operation_id].start_s
                for predecessor_id in op.predecessor_ids:
                    if predecessor_id in frozen_by_op:
                        pred_end = frozen_by_op[predecessor_id].end_s
                    elif predecessor_id in end_vars and end_vars[predecessor_id] is not None:
                        pred_end = end_vars[predecessor_id]
                    else:
                        return self._infeasible(request, started, f"UNKNOWN_PREDECESSOR:{op.operation_id}:{predecessor_id}")
                    if isinstance(pred_end, int):
                        if pred_end > current_start_value:
                            return self._infeasible(request, started, f"FROZEN_PRECEDENCE_CONFLICT:{op.operation_id}:{predecessor_id}")
                    else:
                        model.Add(pred_end <= current_start_value)
            else:
                for predecessor_id in op.predecessor_ids:
                    if predecessor_id in frozen_by_op:
                        model.Add(current_start >= frozen_by_op[predecessor_id].end_s)
                    elif predecessor_id in end_vars and end_vars[predecessor_id] is not None:
                        model.Add(current_start >= end_vars[predecessor_id])
                    else:
                        return self._infeasible(request, started, f"UNKNOWN_PREDECESSOR:{op.operation_id}:{predecessor_id}")

        # R17 feedback round: actual transport departure times are soft targets,
        # NEVER substitute vehicle return arrivals (different contract semantics).
        # First minimize loading misses strongly, then just-in-time holding.  The
        # warehouse schedule remains subject to all hard CP-SAT constraints.
        # No target => preserve the original feasibility-first R16 behavior.
        if request.departure_targets:
            if len({t.order_id for t in request.departure_targets}) != len(request.departure_targets):
                raise ValueError("duplicate_warehouse_departure_targets")
            end_by_order = {}
            for op in operations:
                end = (frozen_by_op[op.operation_id].end_s
                       if op.operation_id in frozen_by_op else end_vars[op.operation_id])
                for oid in op.order_ids:
                    if oid in selected_orders:
                        end_by_order.setdefault(oid, []).append(end)
            terms = []
            targets_by_vehicle = {}
            ready_by_order = {}
            for target in request.departure_targets:
                order = next((o for o in orders if o.order_id == target.order_id), None)
                if order is None or order.warehouse_id != target.warehouse_id:
                    raise ValueError(f"invalid_warehouse_departure_target:{target.order_id}")
                if target.vehicle_id is not None:
                    vehicle = next((v for v in snapshot.vehicles if v.vehicle_id == target.vehicle_id), None)
                    if vehicle is None or vehicle.warehouse_id != target.warehouse_id:
                        raise ValueError(f"invalid_warehouse_departure_vehicle:{target.vehicle_id}")
                ends = end_by_order.get(target.order_id, ())
                if not ends:
                    continue
                ready = model.NewIntVar(0, horizon, f"joint_ready_{target.order_id}")
                model.AddMaxEquality(ready, ends)
                ready_by_order[target.order_id] = ready
                late = model.NewIntVar(0, horizon, f"joint_late_{target.order_id}")
                early = model.NewIntVar(0, horizon, f"joint_early_{target.order_id}")
                model.Add(late >= ready - target.departure_at_s)
                model.Add(early >= target.departure_at_s - ready)
                # Departure misses dominate group-completion improvements.
                terms.append(10000 * late + early)
                if target.vehicle_id is not None:
                    targets_by_vehicle.setdefault(target.vehicle_id, []).append(ready)
            # Crucial B-03 coupling: orders belonging to the SAME transport
            # vehicle are a packing/dispatch cohort. Minimize the maximum
            # warehouse-ready time for each cohort, so one truck may leave
            # earlier instead of waiting for another truck's orders to finish.
            # The next Routing round is free to use the actual earlier ready_at.
            for vehicle_id, readiness_vars in sorted(targets_by_vehicle.items()):
                group_ready = model.NewIntVar(0, horizon, f"joint_vehicle_ready_{vehicle_id}")
                model.AddMaxEquality(group_ready, readiness_vars)
                terms.append(10 * group_ready)
            if terms:
                model.Minimize(sum(terms))

        # Feasibility-first baseline: keep every constraint above hard, but do not
        # force CP-SAT to spend the whole request budget proving an optimum. This
        # is important for larger B-06 baselines where a valid schedule is useful
        # for downstream Routing and simulation even when global optimality is not
        # reached quickly. Later optimization can be introduced as a separate
        # experimental phase without changing the contract or hard constraints.

        solver = cp_model.CpSolver()
        solver.parameters.max_time_in_seconds = max(0.001, request.budget.remaining_ms / 1000.0)
        solver.parameters.num_search_workers = max(1, request.budget.max_workers)
        solver.parameters.random_seed = request.budget.random_seed
        status = solver.Solve(model)
        raw = solver.StatusName(status)
        solve_ms = _elapsed_ms(started)

        if status not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
            mapped: SolveStatus = "infeasible_proven" if status == cp_model.INFEASIBLE else "no_solution_within_budget"
            return WarehouseScheduleResult(
                snapshot_id=snapshot.snapshot_id,
                snapshot_version=snapshot.version,
                metadata=_metadata(
                    status=mapped,
                    raw_status=raw,
                    has_solution=False,
                    proof_scope="request-local CP-SAT model",
                    solve_ms=solve_ms,
                ),
                operations=(),
                warehouse_handoffs=(),
            )

        scheduled: list[ScheduledOperation] = []
        for op in operations:
            if op.operation_id in frozen_by_op:
                frozen = frozen_by_op[op.operation_id]
                scheduled.append(frozen)
                continue
            selected_resource = next(
                rid for rid, lit in assignments[op.operation_id].items() if solver.Value(lit) == 1
            )
            scheduled.append(
                ScheduledOperation(
                    operation_id=op.operation_id,
                    resource_id=selected_resource,
                    start_s=int(solver.Value(start_vars[op.operation_id])),
                    end_s=int(solver.Value(end_vars[op.operation_id])),
                )
            )

        scheduled.sort(key=lambda x: (x.start_s, x.end_s, x.operation_id))
        scheduled_tuple = tuple(scheduled)
        handoffs = self._build_handoffs(orders, scheduled_tuple, {op.operation_id: op for op in operations})

        candidate = WarehouseScheduleResult(
            snapshot_id=snapshot.snapshot_id,
            snapshot_version=snapshot.version,
            metadata=_metadata(
                status="optimal" if status == cp_model.OPTIMAL else "feasible",
                raw_status=raw,
                has_solution=True,
                proof_scope="request-local CP-SAT model",
                solve_ms=solve_ms,
            ),
            operations=scheduled_tuple,
            warehouse_handoffs=handoffs,
        )
        report = WarehouseScheduleValidator().validate(request, candidate)
        if report.status == "failed":
            raise RuntimeError(
                "independent_warehouse_validation_failed:"
                + ";".join(v.rule_id + ":" + v.message for v in report.violations)
            )
        return candidate

    def _validate_request(self, request: WarehouseScheduleRequest) -> None:
        order_ids = set(request.order_ids)
        snapshot_ids = {o.order_id for o in request.snapshot.orders}
        unknown = sorted(order_ids - snapshot_ids)
        if unknown:
            raise ValueError(f"unknown_order_ids:{','.join(unknown)}")
        if request.snapshot.version <= 0:
            raise ValueError("snapshot_version_must_be_positive")

    @staticmethod
    def _build_handoffs(orders, scheduled: tuple[ScheduledOperation, ...],
                        source_ops: dict[str, object]) -> tuple[WarehouseHandoff, ...]:
        if not orders:
            return ()
        end_by_order: dict[str, int] = {}
        for scheduled_op in scheduled:
            source_op = source_ops.get(scheduled_op.operation_id)
            if source_op is None:
                continue
            for order_id in source_op.order_ids:
                end_by_order[order_id] = max(end_by_order.get(order_id, 0), scheduled_op.end_s)

        return tuple(
            WarehouseHandoff(
                order_id=order.order_id,
                warehouse_id=order.warehouse_id,
                ready_at_s=end_by_order.get(order.order_id, 0),
                loading_window=TimeWindow(
                    start_s=end_by_order.get(order.order_id, 0),
                    end_s=max(end_by_order.get(order.order_id, 0), order.freshness_deadline_s),
                ),
            )
            for order in orders
        )

    def _infeasible(self, request: WarehouseScheduleRequest, started: float, raw: str) -> WarehouseScheduleResult:
        return WarehouseScheduleResult(
            snapshot_id=request.snapshot.snapshot_id,
            snapshot_version=request.snapshot.version,
            metadata=_metadata(
                status="infeasible_proven",
                raw_status=raw,
                has_solution=False,
                proof_scope="request-local precheck",
                solve_ms=_elapsed_ms(started),
            ),
            operations=(),
            warehouse_handoffs=(),
        )


def _elapsed_ms(started: float) -> int:
    return int((time.perf_counter() - started) * 1000)
