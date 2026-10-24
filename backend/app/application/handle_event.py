"""B-04 event handling and local replanning orchestration."""
from __future__ import annotations

import hashlib
import json
from uuid import uuid4

from app.bootstrap import Services, build_services
from app.application.impact_analysis import find_affected_work
from app.application.runtime import runtime
from app.contracts.common import SolveMetadata, ValidationReport
from app.contracts.entities import PlanningSnapshot
from app.contracts.events import DispatchEvent
from app.contracts.planning import CandidatePlan, RoutingRequest, UnservedOrder
from app.contracts.reschedule import LocalRescheduleResult, PlanDiff
from app.domain.plan_rules import validate_plan
from app.domain.transport_rules import validate_transport


def handle_event(*, event: DispatchEvent, previous_plan: CandidatePlan, budget_ms: int,
                 services: Services | None = None) -> LocalRescheduleResult:
    services = services or build_services()
    if budget_ms <= 0:
        raise ValueError("budget_ms_must_be_positive")
    if event.snapshot_id != previous_plan.snapshot_id:
        raise ValueError("event_snapshot_mismatch")
    if event.expected_snapshot_version != previous_plan.snapshot_version:
        raise ValueError("event_snapshot_version_mismatch")
    impact = find_affected_work(event=event, plan=previous_plan)
    snapshot = runtime.get_snapshot(event.snapshot_id, event.expected_snapshot_version)
    derived = _derive_snapshot_for_event(snapshot, event)

    old_handoffs = previous_plan.warehouse.warehouse_handoffs
    # A dock outage moves the *loading window*, not the goods' readiness: ready_at stays as
    # scheduled because validate_plan cross-checks it against the warehouse operations.
    effective_handoffs, undeliverable = _effective_handoffs(handoffs=old_handoffs, event=event)
    warehouse_result = previous_plan.warehouse.model_copy(
        update={"warehouse_handoffs": effective_handoffs})

    # Orders this replan cannot serve any more, each with the reason recorded in the result.
    excluded: dict[str, str] = {oid: reason for oid, reason in undeliverable}
    if event.event_type == "cargo_quarantined":
        for oid in impact.affected_order_ids:
            excluded[oid] = "cargo_quarantined"

    # Preserve the request-local scope of the previous plan. The imported snapshot
    # may contain many orders that were not included in this planning job.
    planned_order_ids = set(h.order_id for h in effective_handoffs)
    planned_order_ids.update(
        oid
        for route in previous_plan.routing.routes
        for stop in route.stops
        if stop.stop_kind == "delivery"
        for oid in stop.order_ids
    )
    planned_order_ids.update(u.order_id for u in previous_plan.routing.unserved_orders)
    planned_order_ids.update(impact.affected_order_ids)
    planned_order_ids -= set(excluded)
    all_order_ids = tuple(sorted(planned_order_ids))
    frozen_routes = tuple(r for r in previous_plan.routing.routes if r.vehicle_id not in set(impact.affected_vehicle_ids))

    # B-02 V1 intentionally accepts a single warehouse per RoutingRequest.
    # B-04 must still support the project-level multi-warehouse snapshot by
    # partitioning the global replan into independent warehouse-local Routing
    # requests, then aggregating the results back into one candidate plan.
    order_by_id = {o.order_id: o for o in derived.orders}
    grouped_order_ids: dict[str, list[str]] = {}
    for order_id in all_order_ids:
        grouped_order_ids.setdefault(order_by_id[order_id].warehouse_id, []).append(order_id)

    vehicle_by_id = {v.vehicle_id: v for v in derived.vehicles}
    frozen_by_warehouse: dict[str, list] = {}
    for route in frozen_routes:
        vehicle = vehicle_by_id.get(route.vehicle_id)
        if vehicle is None:
            raise RuntimeError(f"b04_frozen_route_vehicle_missing:{route.vehicle_id}")
        frozen_by_warehouse.setdefault(vehicle.warehouse_id, []).append(route)

    handoffs_by_order = {h.order_id: h for h in effective_handoffs}
    routing_results = []
    remaining_ms = budget_ms
    solver = services.routing
    warehouse_items = sorted(grouped_order_ids.items())
    for index, (warehouse_id, ids) in enumerate(warehouse_items):
        if remaining_ms <= 0:
            raise RuntimeError("b04_routing_budget_exhausted")
        scoped_ids = tuple(ids)
        scoped_handoffs = tuple(handoffs_by_order[i] for i in scoped_ids if i in handoffs_by_order)
        scoped_frozen = tuple(frozen_by_warehouse.get(warehouse_id, ()))
        warehouses_left = len(warehouse_items) - index
        allocation_ms = max(1, remaining_ms // warehouses_left)
        routing_request = RoutingRequest(
            snapshot=derived,
            order_ids=scoped_ids,
            warehouse_handoffs=scoped_handoffs,
            frozen_routes=scoped_frozen,
            budget={"remaining_ms": allocation_ms, "max_workers": 1, "random_seed": 17},
        )
        routing_piece = solver.solve(routing_request)
        if not routing_piece.metadata.has_solution:
            raise RuntimeError(f"b04_routing_failed:{warehouse_id}:{routing_piece.metadata.raw_status}")
        transport_report = validate_transport(
            request=routing_request.model_dump(mode="python"),
            result=routing_piece.model_dump(mode="python"),
        )
        if not transport_report.passed:
            raise RuntimeError(
                "b04_transport_validation_failed:" + ",".join(transport_report.violations[:8])
            )
        routing_results.append(routing_piece)
        remaining_ms -= max(0, routing_piece.metadata.solve_ms)

    routing = _aggregate_routing_results(routing_results)
    if excluded:
        # Orders this replan cannot serve are recorded explicitly instead of vanishing.
        routing = routing.model_copy(update={"unserved_orders": routing.unserved_orders + tuple(
            UnservedOrder(order_id=oid, reason_code=reason)
            for oid, reason in sorted(excluded.items()))})

    raw_violations = validate_plan(
        snapshot=derived.model_dump(mode="python"),
        order_ids=all_order_ids,
        warehouse=warehouse_result.model_dump(mode="python"),
        routing=routing.model_dump(mode="python"),
    )
    if raw_violations:
        raise RuntimeError("b04_plan_validation_failed:" + ";".join(v["rule_id"] for v in raw_violations[:8]))

    new_plan = _make_new_plan(previous_plan=previous_plan, snapshot=derived, routing=routing,
                              warehouse=warehouse_result)
    diff = _diff_plans(previous_plan, new_plan, impact.affected_order_ids)
    runtime.put_snapshot(derived)
    validation = ValidationReport(
        status="passed",
        validator_version="b04-local-reschedule-validator-2.0",
        checked_rule_ids=_checked_rules(event.event_type),
        violations=(),
    )
    return LocalRescheduleResult(
        event=event,
        impact=impact,
        previous_plan_id=previous_plan.plan_id,
        previous_plan_version=previous_plan.version,
        replanned_plan=new_plan,
        diff=diff,
        validation=validation,
    )


COMMON_RULES = (
    "b04.snapshot.derived",
    "b04.impact.local_scope",
    "b04.locked_routes.preserved",
    "b04.affected_routes.replanned",
    "b04.transport.revalidated",
    "b04.plan.revalidated",
)


def _checked_rules(event_type: str) -> tuple[str, ...]:
    """Every event type declares the extra rules its derivation relies on."""
    if event_type == "departure_delayed":
        return COMMON_RULES
    if event_type == "dock_unavailable":
        return COMMON_RULES + ("b04.dock.loading_window_shifted", "b04.dock.undeliverable_recorded")
    if event_type == "cargo_quarantined":
        return COMMON_RULES + ("b04.quarantine.orders_removed_and_recorded",)
    raise ValueError(f"b04_event_type_not_implemented:{event_type}")


def _effective_handoffs(*, handoffs, event: DispatchEvent):
    """Apply the event to the loading plan.

    Returns ``(handoffs, undeliverable)`` where ``undeliverable`` lists
    ``(order_id, reason_code)`` pairs whose loading window closes before the dock reopens.
    ``ready_at`` is deliberately untouched: it describes when the goods are ready, which a
    dock outage does not change, and the cross-domain validator recomputes it from the
    warehouse operations.
    """
    if event.event_type != "dock_unavailable":
        return tuple(handoffs), ()
    until = event.payload.unavailable_until_s
    updated, undeliverable = [], []
    for handoff in handoffs:
        if handoff.warehouse_id != event.object_id:
            updated.append(handoff)
            continue
        window = handoff.loading_window
        if window.end_s < until:
            undeliverable.append((handoff.order_id, "dock_unavailable"))
            continue
        if window.start_s < until:
            handoff = handoff.model_copy(
                update={"loading_window": window.model_copy(update={"start_s": until})})
        updated.append(handoff)
    return tuple(updated), tuple(undeliverable)


def _derive_snapshot_for_event(snapshot: PlanningSnapshot, event: DispatchEvent) -> PlanningSnapshot:
    if event.event_type in ("dock_unavailable", "cargo_quarantined"):
        # Neither event changes a snapshot fact: a dock outage lives in the loading window
        # and a quarantine removes orders from this replan's scope. The version still
        # advances so every plan stays traceable to exactly one operational state.
        return snapshot.model_copy(update={"version": snapshot.version + 1})
    if event.event_type != "departure_delayed":
        raise ValueError(f"b04_event_type_not_implemented:{event.event_type}")
    delay_s = event.payload.delay_s
    if delay_s is None or delay_s <= 0:
        raise ValueError("departure_delayed_requires_positive_delay_s")
    found = False
    vehicles = []
    for v in snapshot.vehicles:
        if v.vehicle_id == event.object_id:
            found = True
            if event.occurred_at_s > v.shift_window.end_s:
                raise ValueError("event_after_vehicle_shift_end")
            new_available = max(v.available_at_s, event.occurred_at_s) + delay_s
            vehicles.append(v.model_copy(update={"available_at_s": new_available, "version": v.version + 1}))
        else:
            vehicles.append(v)
    if not found:
        raise ValueError(f"vehicle_not_found:{event.object_id}")
    return snapshot.model_copy(update={"version": snapshot.version + 1, "vehicles": tuple(vehicles)})



def _aggregate_routing_results(results):
    """Aggregate one B-02 RoutingResult per warehouse into one B-04 result."""
    if len(results) == 1:
        return results[0]

    first = results[0]
    return first.model_copy(
        update={
            "routes": tuple(route for result in results for route in result.routes),
            "warehouse_arrivals": tuple(a for result in results for a in result.warehouse_arrivals),
            "unserved_orders": tuple(u for result in results for u in result.unserved_orders),
            "metadata": SolveMetadata(
                status="optimal" if all(r.metadata.status == "optimal" for r in results) else "feasible",
                raw_status="B04_MULTI_WAREHOUSE_LOCAL_REPLAN",
                engine="OR-Tools RoutingModel",
                engine_version=first.metadata.engine_version,
                has_solution=True,
                proof_scope="independent warehouse-local RoutingModel solves aggregated by warehouse",
                solve_ms=sum(r.metadata.solve_ms for r in results),
            ),
        }
    )

def _make_new_plan(*, previous_plan: CandidatePlan, snapshot: PlanningSnapshot, routing,
                   warehouse) -> CandidatePlan:
    payload = {
        "snapshot_id": snapshot.snapshot_id,
        "snapshot_version": snapshot.version,
        "version": previous_plan.version + 1,
        "routing": routing.model_dump(mode="json"),
        "warehouse": warehouse.model_dump(mode="json"),
    }
    plan_hash = hashlib.sha256(json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    return CandidatePlan(
        plan_id=f"plan_{uuid4().hex[:20]}",
        snapshot_id=snapshot.snapshot_id,
        snapshot_version=snapshot.version,
        version=previous_plan.version + 1,
        plan_hash=plan_hash,
        routing=routing,
        warehouse=warehouse,
        validation=ValidationReport(
            status="passed",
            validator_version="b04-local-reschedule-plan-2.0",
            checked_rule_ids=("b04.replanned_candidate",),
            violations=(),
        ),
    )


def _diff_plans(old: CandidatePlan, new: CandidatePlan, affected_order_ids: tuple[str, ...]) -> PlanDiff:
    old_by_order = {}
    new_by_order = {}
    for plan, target in ((old.routing, old_by_order), (new.routing, new_by_order)):
        for route in plan.routes:
            for stop in route.stops:
                if stop.stop_kind == "delivery":
                    for oid in stop.order_ids:
                        target[oid] = route.vehicle_id
    changed_orders = tuple(sorted(oid for oid in affected_order_ids if old_by_order.get(oid) != new_by_order.get(oid)))
    old_affected = {r.vehicle_id: r for r in old.routing.routes if r.vehicle_id in {old_by_order.get(oid) for oid in affected_order_ids}}
    new_affected = {r.vehicle_id: r for r in new.routing.routes if r.vehicle_id in set(new_by_order.get(oid) for oid in affected_order_ids)}
    old_distance = sum(r.distance_m for r in old.routing.routes)
    new_distance = sum(r.distance_m for r in new.routing.routes)
    old_duration = sum(r.duration_s for r in old.routing.routes)
    new_duration = sum(r.duration_s for r in new.routing.routes)
    changed_vehicles = tuple(sorted(set(old_by_order.get(oid) for oid in affected_order_ids if old_by_order.get(oid)) | set(new_by_order.get(oid) for oid in affected_order_ids if new_by_order.get(oid))))
    return PlanDiff(
        changed_order_ids=changed_orders,
        changed_vehicle_ids=changed_vehicles,
        old_distance_m=old_distance,
        new_distance_m=new_distance,
        distance_delta_m=new_distance - old_distance,
        old_route_duration_s=old_duration,
        new_route_duration_s=new_duration,
        route_duration_delta_s=new_duration - old_duration,
    )

