"""Joint transport/warehouse validation (P10-02 subset)."""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

from logistics_domain.planning import (
    RouteStop,
    Severity,
    TransportPlan,
    ValidationReport,
    Violation,
    content_hash,
)
from logistics_domain.transport import TransportProblem
from logistics_domain.warehouse import WarehouseProblem, WarehouseSolution
from logistics_optimization.validation.transport import validate_transport
from logistics_optimization.validation.warehouse import validate_warehouse


def validate_joint(transport_plan: TransportPlan, transport_problem: TransportProblem,
                   stops: tuple[RouteStop, ...], warehouse_problem: WarehouseProblem,
                   warehouse_solution: WarehouseSolution) -> ValidationReport:
    transport = validate_transport(transport_plan, transport_problem, stops)
    warehouse = validate_warehouse(warehouse_problem, warehouse_solution)
    violations = list(transport.violations) + list(warehouse.violations)
    if transport_problem.snapshot.hash != warehouse_problem.snapshot.hash:
        violations.append(Violation(code="snapshot_mismatch", severity=Severity.HARD,
            entity_refs=(), field_path="snapshot.hash",
            actual=warehouse_problem.snapshot.hash[:12],
            expected=transport_problem.snapshot.hash[:12],
            message="transport and warehouse validators received different snapshots"))
    transport_orders = {node.order_id for node in transport_problem.nodes
                        if node.order_id is not None}
    warehouse_orders = {task.order_id for task in warehouse_problem.tasks
                        if task.order_id is not None}
    missing = transport_orders - warehouse_orders
    if missing:
        violations.append(Violation(code="handoff_order_missing", severity=Severity.HARD,
            entity_refs=(), field_path="warehouse.tasks.order_id",
            actual=str(len(missing)) + " missing", expected="every transported order",
            message="a transported order has no warehouse task"))
    valid = not any(violation.severity == Severity.HARD for violation in violations)
    return ValidationReport(id=uuid4(), candidate_hash=content_hash({
        "transport": transport_plan, "stops": stops,
        "warehouse": warehouse_solution.assignments}),
        snapshot_hash=transport_problem.snapshot.hash, rules_version="1.0.0", valid=valid,
        required_codes=(), checked_codes=(), unsupported_codes=(),
        violations=tuple(violations),
        validated_at=datetime.now(timezone.utc).replace(microsecond=0))


__all__ = ["validate_joint"]
