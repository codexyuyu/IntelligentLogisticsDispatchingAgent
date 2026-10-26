"""CP-SAT warehouse scheduler.

A warehouse task may require several resource kinds at the same time (dock, worker,
equipment). Each requirement gets its own exactly-one resource choice; all choices share
the task start/end. Docks and workers are exclusive, equipment is cumulative against its
quantity capacity. Sequence-dependent setup/changeover gaps are enforced on the primary
(first) requirement when the problem defines a matching transition.
"""

from __future__ import annotations

import time
from datetime import UTC, datetime
from itertools import pairwise
from uuid import uuid4

from ortools.sat.python import cp_model

from logistics_domain.planning import (
    CostBreakdown,
    EngineMetadata,
    ObjectiveBreakdown,
    OperationAssignment,
    ResourceKind,
    SetupOperation,
    SolverEvidence,
    SolveStatus,
    content_hash,
)
from logistics_domain.warehouse import Diagnostic, WarehouseProblem, WarehouseSolution
from logistics_optimization.warehouse.coldchain_model import add_coldchain, phased_capacity

SYSTEM_ACTOR = __import__("uuid").UUID(int=0)


def _now():
    return datetime.now(UTC).replace(microsecond=0)


class CpSatWarehouseScheduler:
    def solve(self, problem: WarehouseProblem, budget) -> WarehouseSolution:
        started = time.monotonic()
        model = cp_model.CpModel()
        resources_by_kind = {
            ResourceKind.DOCK: tuple(item.id for item in problem.snapshot.resources.docks),
            ResourceKind.WORKER: tuple(item.id for item in problem.snapshot.resources.workers),
            ResourceKind.EQUIPMENT: tuple(item.id for item in problem.snapshot.resources.equipment),
        }
        equipment = {item.id: item for item in problem.snapshot.resources.equipment}
        resources = {item.id: item for item in (*problem.snapshot.resources.docks,
                     *problem.snapshot.resources.workers, *problem.snapshot.resources.equipment)}
        warehouses = {item.id: item for item in problem.snapshot.resources.warehouses}
        horizon = problem.snapshot.scope.horizon_s
        eligible: dict[tuple, tuple] = {}
        for task in problem.tasks:
            for index, requirement in enumerate(task.requirements):
                allowed = tuple(sorted(
                    (resource_id for resource_id in requirement.eligible_ids
                     if resource_id in resources_by_kind.get(requirement.resource_kind, ())),
                    key=str,
                ))
                if not allowed:
                    return self._failed(problem, SolveStatus.INFEASIBLE,
                        "a task requirement has no eligible resource in the snapshot",
                        int((time.monotonic() - started) * 1000))
                eligible[(task.id, index)] = allowed

        starts, ends, use, intervals = {}, {}, {}, {}
        for task in problem.tasks:
            start = model.NewIntVar(task.window.earliest_s, task.window.latest_s,
                                    f"start_{task.id}")
            end = model.NewIntVar(task.window.earliest_s + task.duration_s,
                                  task.window.latest_s + task.duration_s, f"end_{task.id}")
            model.Add(end == start + task.duration_s)
            model.Add(end <= min(task.window.latest_s, horizon))
            starts[task.id], ends[task.id] = start, end
            warehouse = warehouses.get(task.warehouse_id)
            if warehouse is None or warehouse.calendar.epoch_utc != problem.snapshot.scope.epoch_utc:
                return self._failed(problem, SolveStatus.UNKNOWN, 'warehouse calendar missing or epoch mismatch', 0)
            task_interval = model.NewIntervalVar(start, task.duration_s, end, f'task_{task.id}')
            phased_capacity(model, [task_interval], [1], horizon,
                [p for iv in warehouse.calendar.intervals for p in (iv.start_s, iv.end_s)],
                lambda t, warehouse=warehouse: int(warehouse.calendar.available_units_at(t) > 0), f'warehouse_{task.id}')
            for index, _ in enumerate(task.requirements):
                choices = []
                for resource_id in eligible[(task.id, index)]:
                    flag = model.NewBoolVar(f"use_{task.id}_{index}_{resource_id}")
                    interval = model.NewOptionalIntervalVar(
                        start, task.duration_s, end, flag,
                        f"iv_{task.id}_{index}_{resource_id}")
                    use[(task.id, index, resource_id)] = flag
                    intervals.setdefault(resource_id, []).append(interval)
                    choices.append(flag)
                model.AddExactlyOne(choices)

        for resource_id, values in intervals.items():
            item = equipment.get(resource_id)
            resource = resources[resource_id]
            if resource.calendar.epoch_utc != problem.snapshot.scope.epoch_utc:
                return self._failed(problem, SolveStatus.UNKNOWN, 'resource calendar epoch mismatch', 0)
            capacity = item.quantity_capacity if item else 1
            demands = [req.units for task in problem.tasks for index, req in enumerate(task.requirements)
                       if (task.id, index, resource_id) in use]
            phased_capacity(model, values, demands, horizon,
                [p for iv in resource.calendar.intervals for p in (iv.start_s, iv.end_s)],
                lambda t, capacity=capacity, resource=resource: min(capacity, resource.calendar.available_units_at(t)), f'resource_{resource_id}')
            if item is not None and item.quantity_capacity > 1:
                demands = []
                for task in problem.tasks:
                    for index, requirement in enumerate(task.requirements):
                        flag = use.get((task.id, index, resource_id))
                        if flag is not None:
                            demands.append((flag, requirement.units))
                if demands:
                    model.AddCumulative(values,
                        [units for _, units in demands], item.quantity_capacity)
            else:
                model.AddNoOverlap(values)

        task_ids = {task.id for task in problem.tasks}
        for task in problem.tasks:
            for predecessor_id in task.predecessor_ids:
                if predecessor_id in task_ids:
                    model.Add(starts[task.id] >= ends[predecessor_id])

        coldchain = problem.snapshot.coldchain
        try:
            add_coldchain(model, problem, starts, ends, use)
        except ValueError as exc:
            return self._failed(problem, SolveStatus.UNKNOWN, str(exc), int((time.monotonic()-started)*1000))
        if coldchain is not None:
            task_by_id = {task.id: task for task in problem.tasks}
            for requirement in coldchain.precool_requirements:
                precool = task_by_id.get(requirement.precool_operation_id)
                if precool is None:
                    # The operation is outside this request scope; do not invent a time.
                    continue
                if precool.duration_s < requirement.min_duration_s:
                    return self._failed(problem, SolveStatus.INFEASIBLE,
                        "pre-cooling task is shorter than its declared minimum",
                        int((time.monotonic() - started) * 1000))
                for loading_id in requirement.loading_operation_ids:
                    if loading_id in task_ids:
                        model.Add(starts[loading_id] >= ends[requirement.precool_operation_id])

        # Sequence-dependent setup on the primary requirement. The gap is enforced only
        # when both tasks actually choose the same primary resource.
        for left_index, left in enumerate(problem.tasks):
            for right in problem.tasks[left_index + 1:]:
                if left.setup_class == right.setup_class:
                    continue
                for resource_id in set(eligible[(left.id, 0)]) & set(eligible[(right.id, 0)]):
                    gap_lr = self._setup_duration(problem, resource_id,
                                                  left.setup_class, right.setup_class)
                    gap_rl = self._setup_duration(problem, resource_id,
                                                  right.setup_class, left.setup_class)
                    if gap_lr <= 0 and gap_rl <= 0:
                        continue
                    left_use = use[(left.id, 0, resource_id)]
                    right_use = use[(right.id, 0, resource_id)]
                    same = model.NewBoolVar(f"same_{left.id}_{right.id}_{resource_id}")
                    model.Add(same <= left_use)
                    model.Add(same <= right_use)
                    model.Add(same >= left_use + right_use - 1)
                    left_before = model.NewBoolVar(f"ord_{left.id}_{right.id}_{resource_id}")
                    if gap_lr >= 0:
                        model.Add(starts[right.id] >= ends[left.id] + gap_lr).OnlyEnforceIf(
                            [same, left_before])
                    if gap_rl >= 0:
                        model.Add(starts[left.id] >= ends[right.id] + gap_rl).OnlyEnforceIf(
                            [same, left_before.Not()])

        horizon = max(task.window.latest_s + task.duration_s for task in problem.tasks)
        makespan = model.NewIntVar(0, horizon, "makespan")
        model.AddMaxEquality(makespan, list(ends.values()))
        model.Minimize(makespan)
        solver = cp_model.CpSolver()
        solver.parameters.max_time_in_seconds = max(
            0.1, min(budget.wall_time_ms, 60000) / 1000)
        solver.parameters.num_search_workers = max(1, budget.worker_count)
        solver.parameters.random_seed = budget.seed
        build_ms = int((time.monotonic() - started) * 1000)
        engine_started = time.monotonic()
        status_code = solver.Solve(model)
        solve_ms = int((time.monotonic() - engine_started) * 1000)
        status = {cp_model.OPTIMAL: SolveStatus.OPTIMAL,
                  cp_model.FEASIBLE: SolveStatus.FEASIBLE,
                  cp_model.INFEASIBLE: SolveStatus.INFEASIBLE}.get(
                      status_code, SolveStatus.UNKNOWN)
        if status not in (SolveStatus.OPTIMAL, SolveStatus.FEASIBLE):
            return self._failed(problem, status,
                                "warehouse model has no feasible assignment", solve_ms)

        assignments = []
        for task in problem.tasks:
            start = solver.Value(starts[task.id])
            for index, requirement in enumerate(task.requirements):
                chosen = next(
                    resource_id for resource_id in eligible[(task.id, index)]
                    if solver.Value(use[(task.id, index, resource_id)]) == 1)
                assignments.append(OperationAssignment(
                    task_id=task.id, resource_id=chosen, start_s=start,
                    end_s=start + task.duration_s, units=requirement.units))
        setup_operations = self._setups(problem, assignments, eligible)
        service_cents = len(problem.tasks) * 100
        setup_cents = sum(item.cost_cents for item in setup_operations)
        cost = CostBreakdown(0, 0, service_cents, 0, setup_cents,
                             service_cents + setup_cents)
        objective = ObjectiveBreakdown(cost.total_cents, 0, 0, 0, 0, cost.total_cents)
        metadata = EngineMetadata(name="ortools_cp_sat", version="9",
            configuration_hash=content_hash(
                {"workers": solver.parameters.num_search_workers}),
            seed=budget.seed, workers=solver.parameters.num_search_workers,
            input_hash=content_hash(problem), solve_ms=solve_ms, build_ms=build_ms,
            engine_status=status.value, incumbent_exists=True,
            best_bound=int(solver.BestObjectiveBound())
            if solver.BestObjectiveBound() >= 0 else None,
            optimality_gap=None)
        evidence = SolverEvidence(id=uuid4(), engine_name="cp_sat", engine_version="9",
            input_hash=content_hash(problem),
            assignment_hash=content_hash(tuple(assignments)),
            configuration_hash=content_hash(
                {"workers": solver.parameters.num_search_workers}),
            solve_status=status, trusted_job_id=None)
        result = WarehouseSolution(status=status, engine_metadata=metadata,
            assignments=tuple(assignments), storage_allocations=(),
            setup_operations=tuple(setup_operations), objective=objective,
            validation=None, diagnostics=(), solver_evidence=(evidence,))
        from dataclasses import replace

        from logistics_optimization.validation.warehouse import validate_warehouse
        return replace(result, validation=validate_warehouse(problem, result))

    def _setup_duration(self, problem, resource_id, from_class, to_class):
        for transition in problem.setup_policy.transitions:
            if (transition.resource_id == resource_id
                    and transition.from_class == from_class
                    and transition.to_class == to_class):
                return transition.duration_s
        if problem.snapshot.coldchain is not None:
            for policy in problem.snapshot.coldchain.setup_policies:
                for rule in policy.rules:
                    if rule.from_class == from_class and rule.to_class == to_class:
                        return rule.duration_s
                if policy.default_duration_s is not None and from_class != to_class:
                    return policy.default_duration_s
        return 0

    def _setups(self, problem, assignments, eligible):
        task_by_id = {task.id: task for task in problem.tasks}
        primary = {task.id: set(eligible[(task.id, 0)]) for task in problem.tasks}
        by_resource = {}
        for assignment in assignments:
            if assignment.resource_id in primary[assignment.task_id]:
                by_resource.setdefault(assignment.resource_id, []).append(assignment)
        setups = []
        for resource_id, values in by_resource.items():
            values.sort(key=lambda item: item.start_s)
            for left, right in pairwise(values):
                left_task = task_by_id[left.task_id]
                right_task = task_by_id[right.task_id]
                if left_task.setup_class == right_task.setup_class:
                    continue
                transition = next((item for item in problem.setup_policy.transitions
                    if item.resource_id == resource_id
                    and item.from_class == left_task.setup_class
                    and item.to_class == right_task.setup_class), None)
                duration = self._setup_duration(problem, resource_id, left_task.setup_class, right_task.setup_class)
                if duration <= 0:
                    continue
                start = left.end_s
                end = start + duration
                if end > right.start_s:
                    continue
                setups.append(SetupOperation(resource_id=resource_id,
                    from_class=left_task.setup_class,
                    to_class=right_task.setup_class, start_s=start, end_s=end,
                    cost_cents=transition.cost_cents if transition else 0))
        return setups

    def _failed(self, problem, status, message, solve_ms):
        metadata = EngineMetadata(name="ortools_cp_sat", version="9",
            configuration_hash=content_hash({"workers": 1}), seed=0, workers=1,
            input_hash=content_hash(problem), solve_ms=solve_ms, build_ms=0,
            engine_status=status.value, incumbent_exists=False, best_bound=None,
            optimality_gap=None)
        evidence = SolverEvidence(id=uuid4(), engine_name="cp_sat", engine_version="9",
            input_hash=content_hash(problem), assignment_hash=content_hash(()),
            configuration_hash=content_hash({"workers": 1}), solve_status=status,
            trusted_job_id=None)
        return WarehouseSolution(status=status, engine_metadata=metadata, assignments=(),
            storage_allocations=(), setup_operations=(), objective=None, validation=None,
            diagnostics=(Diagnostic("warehouse_infeasible", message, "error"),),
            solver_evidence=(evidence,))

