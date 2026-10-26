"""Joint transport/warehouse validation (P10-02 subset)."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

from logistics_domain.planning import (
    RouteStop,
    Severity,
    TransportPlan,
    ValidationReport,
    Violation,
    content_hash,
)
from logistics_domain.transport import RoutingNodeKind, TransportProblem
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
    nodes = {n.id: n for n in transport_problem.nodes}
    warehouses = {w.id: w for w in warehouse_problem.snapshot.resources.warehouses}
    for task in warehouse_problem.tasks:
        if task.order_id is None or task.order_id in transport_plan.unserved_order_ids:
            continue
        assignments = [a for a in warehouse_solution.assignments if a.task_id == task.id]
        pickups = [s for s in stops if s.node_id in nodes and nodes[s.node_id].order_id == task.order_id
                   and nodes[s.node_id].kind == RoutingNodeKind.PICKUP]
        warehouse_entry = warehouses.get(task.warehouse_id)
        if len(pickups) != 1 or not assignments or warehouse_entry is None:
            violations.append(Violation('handoff_evidence_missing', Severity.HARD, (), 'handoff',
                str(task.id), 'one pickup and completed warehouse task', 'handoff cannot be established'))
            continue
        pickup = pickups[0]
        ready = max(a.end_s for a in assignments)
        if nodes[pickup.node_id].location_id != warehouse_entry.node_id or pickup.service_start_s < ready:
            violations.append(Violation('handoff_sequence', Severity.HARD, (), 'handoff',
                str(pickup.service_start_s), f'>= {ready} at assigned warehouse',
                'pickup precedes warehouse completion or uses another warehouse'))
    valid = transport.valid and warehouse.valid and not any(v.severity == Severity.HARD for v in violations)
    return ValidationReport(id=uuid4(), candidate_hash=content_hash({
        "transport": transport_plan, "stops": stops,
        "warehouse": warehouse_solution.assignments}),
        snapshot_hash=transport_problem.snapshot.hash, rules_version="1.0.0", valid=valid,
        required_codes=('joint.handoff',), checked_codes=('joint.handoff', *warehouse.checked_codes),
        unsupported_codes=warehouse.unsupported_codes,
        violations=tuple(violations),
        validated_at=datetime.now(UTC).replace(microsecond=0))


__all__ = ["validate_joint"]
