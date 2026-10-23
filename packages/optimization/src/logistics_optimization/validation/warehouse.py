"""Independent warehouse validation (P10-02 subset)."""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

from logistics_domain.planning import Severity, ValidationReport, Violation, content_hash
from logistics_domain.warehouse import WarehouseProblem, WarehouseSolution


def validate_warehouse(problem: WarehouseProblem,
                       solution: WarehouseSolution) -> ValidationReport:
    violations: list[Violation] = []
    tasks = {task.id: task for task in problem.tasks}
    assigned: dict = {}
    by_resource: dict = {}
    for assignment in solution.assignments:
        task = tasks.get(assignment.task_id)
        if task is None:
            violations.append(Violation(code="unknown_task", severity=Severity.HARD,
                entity_refs=(), field_path="assignment.task_id",
                actual=str(assignment.task_id), expected="task in problem",
                message="assignment references an unknown warehouse task"))
            continue
        if assignment.task_id in assigned:
            violations.append(Violation(code="task_twice", severity=Severity.HARD,
                entity_refs=(), field_path="assignment.task_id",
                actual=str(assignment.task_id), expected="one assignment per task",
                message="a warehouse task is assigned more than once"))
        assigned[assignment.task_id] = assignment
        eligible = {resource_id for requirement in task.requirements
                    for resource_id in requirement.eligible_ids}
        if eligible and assignment.resource_id not in eligible:
            violations.append(Violation(code="ineligible_resource", severity=Severity.HARD,
                entity_refs=(), field_path="assignment.resource_id",
                actual=str(assignment.resource_id), expected="eligible resource",
                message="assignment uses a resource outside the task requirements"))
        if assignment.start_s < task.window.earliest_s or assignment.end_s > task.window.latest_s:
            violations.append(Violation(code="time_window", severity=Severity.HARD,
                entity_refs=(), field_path="assignment.start_s",
                actual=f"{assignment.start_s}..{assignment.end_s}",
                expected=f"[{task.window.earliest_s},{task.window.latest_s}]",
                message="assignment lies outside the task start window"))
        if assignment.end_s - assignment.start_s != task.duration_s:
            violations.append(Violation(code="duration", severity=Severity.HARD,
                entity_refs=(), field_path="assignment.end_s",
                actual=str(assignment.end_s - assignment.start_s),
                expected=str(task.duration_s), message="assignment duration differs from task"))
        by_resource.setdefault(assignment.resource_id, []).append(assignment)
    missing = set(tasks) - set(assigned)
    if solution.assignments and missing:
        violations.append(Violation(code="task_coverage", severity=Severity.HARD,
            entity_refs=(), field_path="solution.assignments",
            actual=str(len(missing)) + " missing", expected="every task assigned",
            message="not every warehouse task has an assignment"))
    for resource_id, assignments in by_resource.items():
        assignments.sort(key=lambda item: item.start_s)
        for left, right in zip(assignments, assignments[1:]):
            if left.end_s > right.start_s:
                violations.append(Violation(code="resource_overlap", severity=Severity.HARD,
                    entity_refs=(), field_path="assignment.resource_id",
                    actual=str(resource_id), expected="no overlap",
                    message="two warehouse assignments overlap on the same resource"))
    for task in problem.tasks:
        assignment = assigned.get(task.id)
        if assignment is None:
            continue
        for predecessor_id in task.predecessor_ids:
            predecessor = assigned.get(predecessor_id)
            if predecessor is not None and predecessor.end_s > assignment.start_s:
                violations.append(Violation(code="precedence", severity=Severity.HARD,
                    entity_refs=(), field_path="assignment.start_s",
                    actual=str(assignment.start_s), expected=f">= {predecessor.end_s}",
                    message="task starts before its predecessor finishes"))
    cost = solution.objective.business_cost_cents if solution.objective is not None else None
    if cost is not None and cost < 0:
        violations.append(Violation(code="negative_cost", severity=Severity.HARD,
            entity_refs=(), field_path="objective.business_cost_cents", actual=str(cost),
            expected=">= 0", message="objective cost is negative"))
    valid = not any(violation.severity == Severity.HARD for violation in violations)
    return ValidationReport(id=uuid4(),
        candidate_hash=content_hash({"assignments": solution.assignments}),
        snapshot_hash=problem.snapshot.hash, rules_version="1.0.0", valid=valid,
        required_codes=(), checked_codes=(), unsupported_codes=(),
        violations=tuple(violations),
        validated_at=datetime.now(timezone.utc).replace(microsecond=0))


__all__ = ["validate_warehouse"]
