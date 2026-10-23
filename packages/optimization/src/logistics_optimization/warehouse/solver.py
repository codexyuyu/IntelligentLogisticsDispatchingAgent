"""CP-SAT warehouse scheduler (P09-05 subset).

One optional interval per eligible resource, exactly-one assignment, no-overlap per resource
and explicit predecessor constraints. OR-Tools objects stay inside this adapter.
"""

from __future__ import annotations

import time
from datetime import datetime, timezone
from uuid import uuid4

from ortools.sat.python import cp_model

from logistics_domain.planning import (
    CostBreakdown,
    EngineMetadata,
    ObjectiveBreakdown,
    OperationAssignment,
    SolveStatus,
    SolverEvidence,
    ValidationReport,
    content_hash,
    Severity,
    Violation,
)
from logistics_domain.transport import Diagnostic, DiagnosticSeverity
from logistics_domain.warehouse import WarehouseProblem, WarehouseSolution

SYSTEM_ACTOR = __import__("uuid").UUID(int=0)


def _now():
    return datetime.now(timezone.utc).replace(microsecond=0)


class CpSatWarehouseScheduler:
    def solve(self, problem: WarehouseProblem, budget) -> WarehouseSolution:
        started = time.monotonic()
        model = cp_model.CpModel()
        resources = self._resources(problem)
        eligible_by_task = {task.id: self._eligible(task, resources) for task in problem.tasks}
        if any(not ids for ids in eligible_by_task.values()):
            status = SolveStatus.INFEASIBLE
            return self._failed(problem, status, "a task has no eligible warehouse resource",
                                int((time.monotonic() - started) * 1000))
        starts, ends, intervals, presence = {}, {}, {}, {}
        horizon = max(task.window.latest_s + task.duration_s for task in problem.tasks)
        for task in problem.tasks:
            start = model.NewIntVar(task.window.earliest_s, task.window.latest_s, f"start_{task.id}")
            end = model.NewIntVar(task.window.earliest_s + task.duration_s,
                                  task.window.latest_s + task.duration_s, f"end_{task.id}")
            model.Add(end == start + task.duration_s)
            starts[task.id], ends[task.id] = start, end
            presences = []
            for resource_id in eligible_by_task[task.id]:
                flag = model.NewBoolVar(f"use_{task.id}_{resource_id}")
                interval = model.NewOptionalIntervalVar(start, task.duration_s, end, flag,
                                                        f"iv_{task.id}_{resource_id}")
                intervals.setdefault(resource_id, []).append(interval)
                presence[(task.id, resource_id)] = flag
                presences.append(flag)
            model.AddExactlyOne(presences)
        for resource_id, values in intervals.items():
            model.AddNoOverlap(values)
        task_ids = {task.id for task in problem.tasks}
        for task in problem.tasks:
            for predecessor_id in task.predecessor_ids:
                if predecessor_id in task_ids:
                    model.Add(starts[task.id] >= ends[predecessor_id])
        makespan = model.NewIntVar(0, horizon, "makespan")
        model.AddMaxEquality(makespan, list(ends.values()))
        model.Minimize(makespan)
        solver = cp_model.CpSolver()
        solver.parameters.max_time_in_seconds = max(0.1, min(budget.wall_time_ms, 60000) / 1000)
        solver.parameters.num_search_workers = max(1, budget.worker_count)
        status_code = solver.Solve(model)
        solve_ms = int((time.monotonic() - started) * 1000)
        status = {cp_model.OPTIMAL: SolveStatus.OPTIMAL,
                  cp_model.FEASIBLE: SolveStatus.FEASIBLE,
                  cp_model.INFEASIBLE: SolveStatus.INFEASIBLE}.get(status_code, SolveStatus.UNKNOWN)
        if status not in (SolveStatus.OPTIMAL, SolveStatus.FEASIBLE):
            return self._failed(problem, status, "warehouse model has no feasible assignment", solve_ms)
        assignments = []
        for task in problem.tasks:
            chosen = next(resource_id for resource_id in eligible_by_task[task.id]
                          if solver.Value(presence[(task.id, resource_id)]) == 1)
            start = solver.Value(starts[task.id])
            assignments.append(OperationAssignment(task_id=task.id, resource_id=chosen,
                start_s=start, end_s=start + task.duration_s, units=1))
        service_cents = len(assignments) * 100
        cost = CostBreakdown(0, 0, service_cents, 0, 0, service_cents)
        objective = ObjectiveBreakdown(cost.total_cents, 0, 0, 0, 0, cost.total_cents)
        validation = self._validate(problem, assignments)
        metadata = EngineMetadata(name="ortools_cp_sat", version="9",
            configuration_hash=content_hash({"workers": solver.parameters.num_search_workers}),
            seed=budget.seed, workers=solver.parameters.num_search_workers,
            input_hash=content_hash(problem), solve_ms=solve_ms, build_ms=0,
            engine_status=status.value, incumbent_exists=True,
            best_bound=int(solver.BestObjectiveBound()) if solver.BestObjectiveBound() >= 0 else None,
            optimality_gap=None)
        evidence = SolverEvidence(id=uuid4(), engine_name="cp_sat", engine_version="9",
            input_hash=content_hash(problem), assignment_hash=content_hash(tuple(assignments)),
            configuration_hash=content_hash({"workers": solver.parameters.num_search_workers}),
            solve_status=status, trusted_job_id=None)
        return WarehouseSolution(status=status, engine_metadata=metadata,
            assignments=tuple(assignments), storage_allocations=(), setup_operations=(),
            objective=objective, validation=validation, diagnostics=(),
            solver_evidence=(evidence,))

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

    def _resources(self, problem):
        ids = set()
        for task in problem.tasks:
            for requirement in task.requirements:
                ids.update(requirement.eligible_ids)
        if not ids:
            for bundle in (problem.snapshot.resources.docks, problem.snapshot.resources.workers,
                           problem.snapshot.resources.equipment):
                ids.update(item.id for item in bundle)
        return ids

    def _eligible(self, task, resources):
        eligible = set()
        for requirement in task.requirements:
            eligible.update(requirement.eligible_ids)
        if not eligible:
            return tuple(sorted(resources, key=str))
        return tuple(sorted(eligible & resources, key=str))

    def _validate(self, problem, assignments):
        violations = []
        task_by_id = {task.id: task for task in problem.tasks}
        by_resource = {}
        for assignment in assignments:
            task = task_by_id.get(assignment.task_id)
            if task is None:
                violations.append(Violation("unknown_task", Severity.HARD, (), "task_id",
                    str(assignment.task_id), "known task", "assignment references unknown task"))
                continue
            if not task.window.contains_start(assignment.start_s):
                violations.append(Violation("time_window", Severity.HARD, (), "start_s",
                    str(assignment.start_s), f"[{task.window.earliest_s},{task.window.latest_s}]",
                    "assignment starts outside the task window"))
            by_resource.setdefault(assignment.resource_id, []).append(assignment)
        for resource_id, values in by_resource.items():
            values.sort(key=lambda item: item.start_s)
            for left, right in zip(values, values[1:]):
                if left.end_s > right.start_s:
                    violations.append(Violation("overlap", Severity.HARD, (), "resource_id",
                        str(resource_id), "no overlap", "resource assignments overlap"))
        valid = not any(v.severity == Severity.HARD for v in violations)
        return ValidationReport(id=uuid4(), candidate_hash=content_hash(tuple(assignments)),
            snapshot_hash=problem.snapshot.hash, rules_version="1.0.0", valid=valid,
            required_codes=(), checked_codes=(), unsupported_codes=(),
            violations=tuple(violations), validated_at=_now())
