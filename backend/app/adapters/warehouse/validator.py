"""Independent post-solve validation for warehouse schedules.

This validator deliberately does not reuse the CP-SAT model-building helpers.
It checks the shared-contract semantics independently so a solver bug cannot
silently turn an invalid plan into a valid result.
"""
from __future__ import annotations

from app.contracts.common import ValidationReport, Violation
from app.contracts.planning import WarehouseScheduleRequest, WarehouseScheduleResult

VALIDATOR_VERSION = "warehouse-validator-0.1"


class WarehouseScheduleValidator:
    def validate(
        self,
        request: WarehouseScheduleRequest,
        result: WarehouseScheduleResult,
    ) -> ValidationReport:
        from app.domain.cold_chain_rules import RULES as COLD_CHAIN_RULES
        rules = (
            "warehouse.release_deadline",
            "warehouse.resource_availability",
            "warehouse.resource_non_overlap",
            "warehouse.precedence",
            "warehouse.frozen_facts",
            "warehouse.scope",
            "warehouse.handoff_operation_ready",
        ) + (("warehouse.verified_resource_binding",) if request.snapshot.rule_version == 'pg-r27-verified' else ()) + COLD_CHAIN_RULES
        violations: list[Violation] = []
        snapshot = request.snapshot
        operations = {op.operation_id: op for op in snapshot.operations}
        resources = {r.resource_id: r for r in snapshot.resources}
        frozen = {op.operation_id: op for op in snapshot.frozen_operations}
        scheduled = {op.operation_id: op for op in result.operations}
        requested_order_ids = set(request.order_ids)

        # Scope: no planned operation may be outside the requested order scope when
        # it carries explicit order references.
        for op_id, sop in scheduled.items():
            source = operations.get(op_id)
            if source is None and op_id not in frozen:
                violations.append(Violation(
                    rule_id="warehouse.scope",
                    object_ids=(op_id,),
                    message="scheduled operation is not present in snapshot operations",
                ))
            elif source is not None and source.order_ids and not any(
                oid in requested_order_ids for oid in source.order_ids
            ):
                violations.append(Violation(
                    rule_id="warehouse.scope",
                    object_ids=(op_id,),
                    message="scheduled operation is outside requested order scope",
                ))

        # Every requested operation in scope must be scheduled unless it is explicitly
        # absent from the snapshot's operation set. The current contract expects the
        # scheduler to solve snapshot operations, not invent missing work.
        for op in snapshot.operations:
            if op.order_ids and not any(oid in requested_order_ids for oid in op.order_ids):
                continue
            if op.operation_id not in scheduled and op.operation_id not in frozen:
                violations.append(Violation(
                    rule_id="warehouse.scope",
                    object_ids=(op.operation_id,),
                    message="in-scope operation is missing from result",
                ))

        # Independent proof that every selected order handoff is derived from
        # its real scheduled warehouse work, not a fabricated ready_at time.
        handoffs_by_order = {}
        for handoff in result.warehouse_handoffs:
            if handoff.order_id in handoffs_by_order:
                violations.append(Violation(
                    rule_id='warehouse.handoff_operation_ready',
                    object_ids=(handoff.order_id,), message='duplicate warehouse handoff'))
            handoffs_by_order[handoff.order_id] = handoff
        for oid in requested_order_ids:
            handoff = handoffs_by_order.get(oid)
            if handoff is None:
                violations.append(Violation(rule_id='warehouse.handoff_operation_ready',
                    object_ids=(oid,), message='requested order missing handoff'))
                continue
            relevant_ids = [op.operation_id for op in snapshot.operations if oid in op.order_ids]
            relevant = [(scheduled[op_id].end_s if op_id in scheduled else frozen[op_id].end_s)
                        for op_id in relevant_ids if op_id in scheduled or op_id in frozen]
            missing = [op_id for op_id in relevant_ids if op_id not in scheduled and op_id not in frozen]
            if missing:
                violations.append(Violation(rule_id='warehouse.handoff_operation_ready',
                    object_ids=(oid,) + tuple(missing), message='handoff references unfinished warehouse work'))
            if relevant and handoff.ready_at_s != max(relevant):
                violations.append(Violation(rule_id='warehouse.handoff_operation_ready',
                    object_ids=(oid,), message='handoff time must equal last warehouse operation completion'))
            if handoff.loading_window.start_s > handoff.ready_at_s or handoff.loading_window.end_s < handoff.ready_at_s:
                violations.append(Violation(rule_id='warehouse.handoff_operation_ready',
                    object_ids=(oid,), message='handoff ready time is outside loading window'))

        # Time/resource checks.
        for op_id, sop in scheduled.items():
            source = operations.get(op_id)
            if snapshot.rule_version == 'pg-r27-verified' and source is not None and source.resource_id != sop.resource_id:
                violations.append(Violation(rule_id='warehouse.verified_resource_binding',
                    object_ids=(op_id, sop.resource_id),
                    message='verified PostgreSQL operation assigned to a different physical resource'))
            resource = resources.get(sop.resource_id)
            if resource is None:
                violations.append(Violation(
                    rule_id="warehouse.resource_availability",
                    object_ids=(op_id, sop.resource_id),
                    message="scheduled resource does not exist in snapshot",
                ))
                continue
            if sop.end_s <= sop.start_s:
                violations.append(Violation(
                    rule_id="warehouse.release_deadline",
                    object_ids=(op_id,),
                    message="operation end must be after start",
                ))
            if source is not None:
                if sop.start_s < source.release_at_s:
                    violations.append(Violation(
                        rule_id="warehouse.release_deadline",
                        object_ids=(op_id,),
                        message="operation starts before release_at_s",
                    ))
                if sop.end_s > source.deadline_at_s:
                    violations.append(Violation(
                        rule_id="warehouse.release_deadline",
                        object_ids=(op_id,),
                        message="operation ends after deadline_at_s",
                    ))

            if not any(
                sop.start_s >= w.start_s and sop.end_s <= w.end_s
                for w in resource.available_windows
            ):
                violations.append(Violation(
                    rule_id="warehouse.resource_availability",
                    object_ids=(op_id, resource.resource_id),
                    message="operation is not fully contained in an available resource window",
                ))
            for unavailable in resource.unavailable_windows:
                if sop.start_s < unavailable.end_s and sop.end_s > unavailable.start_s:
                    violations.append(Violation(
                        rule_id="warehouse.resource_availability",
                        object_ids=(op_id, resource.resource_id),
                        message="operation overlaps a resource unavailable window",
                    ))

            if op_id in frozen:
                fact = frozen[op_id]
                if sop.resource_id != fact.resource_id or sop.start_s != fact.start_s or sop.end_s != fact.end_s:
                    violations.append(Violation(
                        rule_id="warehouse.frozen_facts",
                        object_ids=(op_id,),
                        message="frozen operation was changed by the schedule",
                    ))

        # Resource pairwise non-overlap, including frozen facts.
        by_resource: dict[str, list] = {}
        for sop in scheduled.values():
            by_resource.setdefault(sop.resource_id, []).append(sop)
        for resource_id, items in by_resource.items():
            items = sorted(items, key=lambda x: (x.start_s, x.end_s, x.operation_id))
            for left, right in zip(items, items[1:]):
                if right.start_s < left.end_s:
                    violations.append(Violation(
                        rule_id="warehouse.resource_non_overlap",
                        object_ids=(left.operation_id, right.operation_id, resource_id),
                        message="operations overlap on the same resource",
                    ))

        # Frozen facts must themselves be internally consistent.
        frozen_by_resource: dict[str, list] = {}
        for fact in frozen.values():
            frozen_by_resource.setdefault(fact.resource_id, []).append(fact)
        for resource_id, facts in frozen_by_resource.items():
            facts = sorted(facts, key=lambda x: (x.start_s, x.end_s, x.operation_id))
            for left, right in zip(facts, facts[1:]):
                if right.start_s < left.end_s:
                    violations.append(Violation(
                        rule_id="warehouse.frozen_facts",
                        object_ids=(left.operation_id, right.operation_id, resource_id),
                        message="snapshot frozen operations overlap",
                    ))

        # Predecessor relationships.
        for op in snapshot.operations:
            if op.order_ids and not any(oid in requested_order_ids for oid in op.order_ids):
                continue
            current = scheduled.get(op.operation_id)
            if current is None:
                continue
            for pred_id in op.predecessor_ids:
                predecessor = scheduled.get(pred_id) or frozen.get(pred_id)
                if predecessor is None:
                    violations.append(Violation(
                        rule_id="warehouse.precedence",
                        object_ids=(op.operation_id, pred_id),
                        message="predecessor is not scheduled or frozen",
                    ))
                elif predecessor.end_s > current.start_s:
                    violations.append(Violation(
                        rule_id="warehouse.precedence",
                        object_ids=(op.operation_id, pred_id),
                        message="operation starts before predecessor finishes",
                    ))

        # Read-only, solver-independent business facts.  Missing live PG
        # reservation data is reported separately by the workflow audit;
        # definite violations must fail the plan validation here as well.
        from app.domain.cold_chain_rules import validate_cold_chain
        business = validate_cold_chain(snapshot.model_dump(mode="python"), request.order_ids)
        for issue in business["violations"]:
            violations.append(Violation(rule_id=issue["rule_id"],
                object_ids=tuple(issue["object_ids"]), message=issue["message"]))

        return ValidationReport(
            status="passed" if not violations else "failed",
            validator_version=VALIDATOR_VERSION,
            checked_rule_ids=rules,
            violations=tuple(violations),
        )
