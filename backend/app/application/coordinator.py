"""R17 B-03: independently validated, budget-bounded two-way warehouse/transport coordination.

A feasible R16-style result is retained as an incumbent.  In opt-in ``deep``
mode, Routing depot departures become explicit *soft* warehouse scheduling
signals. CP-SAT re-assigns/re-times actual operations, Routing re-solves with the
new handoffs, and only lexicographically better, independently checked pairs
are selected. Both engines use the same snapshot and hard business constraints.
"""
from __future__ import annotations

import hashlib
import json
from time import perf_counter
from uuid import uuid4

from app.adapters.routing.ortools_solver import OrToolsRoutingSolver
from app.adapters.warehouse.cp_sat_scheduler import CpSatWarehouseScheduler
from app.adapters.warehouse.validator import WarehouseScheduleValidator
from app.contracts.common import SolveMetadata, ValidationReport
from app.contracts.planning import (
    CandidatePlan, CoordinationReport, CoordinationRound, RoutingRequest,
    WarehouseDepartureTarget, WarehouseScheduleRequest,
)
from app.domain.plan_rules import validate_plan
from app.domain.transport_rules import validate_transport


CHECKED_RULES = (
    "b03.order.exists", "b03.handoff.exists", "b03.handoff.ready_at",
    "b03.handoff.loading_window", "b03.handoff.operation_ready",
    "b03.scope.warehouse", "b03.delivery.freshness",
    "b03.route.monotonic", "b03.route.duration", "b03.order.required_served",
    "b03.return_arrival.time", "warehouse.resource_non_overlap",
    "warehouse.precedence", "transport.vehicle_capacity", "transport.time_windows",
)
OBJECTIVE = "lexicographic:unserved_orders,distance_m,handoff_wait_s,warehouse_makespan_s,route_duration_s"


def _warehouse_budget(total_ms: int, order_count: int) -> int:
    # Preserve R16 time partition for every first-round/benchmark solve.
    fraction = 0.10 if order_count >= 100 else 0.15 if order_count >= 50 else 0.30
    routing_reserve = min(max(5000, int(total_ms * (1 - fraction))), max(1, total_ms - 1))
    return max(1, total_ms - routing_reserve)


def _solve_pair(*, snapshot, order_ids, budget_ms, targets=(), seed=17):
    """CP-SAT -> Routing, both independently checked; rejects partial successes.

    ``seed`` reaches both engines so one coordination round can explore a genuinely
    different candidate: CP-SAT runs single-worker, where the seed changes the search
    trajectory (hence the handoff ready times) deterministically.
    """
    from app.domain.cold_chain_rules import validate_cold_chain
    audit = validate_cold_chain(snapshot.model_dump(mode="python"), order_ids)
    if audit["violations"]:
        raise RuntimeError("coldchain_precheck_failed:" + ";".join(
            x["rule_id"] + ":" + ",".join(x["object_ids"])
            for x in audit["violations"][:8]))
    started = perf_counter()
    selected = {o.order_id: o for o in snapshot.orders if o.order_id in set(order_ids)}
    groups: dict[str, list[str]] = {}
    for order in snapshot.orders:
        if order.order_id in selected:
            groups.setdefault(order.warehouse_id, []).append(order.order_id)

    warehouse_request = WarehouseScheduleRequest(
        snapshot=snapshot, order_ids=order_ids, departure_targets=tuple(targets),
        budget={"remaining_ms": _warehouse_budget(budget_ms, len(order_ids)), "max_workers": 1,
                "random_seed": seed},
    )
    warehouse = CpSatWarehouseScheduler().schedule(warehouse_request)
    if not warehouse.metadata.has_solution:
        raise RuntimeError(f"warehouse_solver_failed:{warehouse.metadata.raw_status}")
    wr = WarehouseScheduleValidator().validate(warehouse_request, warehouse)
    if wr.status != "passed":
        raise RuntimeError("warehouse_validation_failed:" + ",".join(v.rule_id for v in wr.violations[:8]))

    handoffs = {h.order_id: h for h in warehouse.warehouse_handoffs}
    route_results = []
    for idx, (warehouse_id, ids) in enumerate(sorted(groups.items())):
        remaining = budget_ms - int((perf_counter() - started) * 1000)
        if remaining <= 0:
            raise RuntimeError("coordination_budget_exhausted_before_routing")
        per_group = max(1, remaining // (len(groups) - idx))
        request = RoutingRequest(
            snapshot=snapshot, order_ids=tuple(ids),
            warehouse_handoffs=tuple(handoffs[oid] for oid in ids), frozen_routes=(),
            budget={"remaining_ms": per_group, "max_workers": 1, "random_seed": seed},
        )
        routing = OrToolsRoutingSolver().solve(request)
        if not routing.metadata.has_solution:
            raise RuntimeError(f"routing_solver_failed:{warehouse_id}:{routing.metadata.raw_status}")
        checked = validate_transport(request=request.model_dump(mode="python"), result=routing.model_dump(mode="python"))
        if not checked.passed:
            raise RuntimeError("routing_validation_failed:" + ",".join(checked.violations[:8]))
        route_results.append(routing)

    routing = _aggregate_routing(route_results)
    violations = validate_plan(
        snapshot=snapshot.model_dump(mode="python"), order_ids=order_ids,
        warehouse=warehouse.model_dump(mode="python"), routing=routing.model_dump(mode="python"),
    )
    if violations:
        raise RuntimeError("coordination_validation_failed:" + ";".join(
            v["rule_id"] + ":" + v["message"] for v in violations[:8]
        ))
    return warehouse, routing


def _departure_targets(snapshot, routing):
    order_to_warehouse = {o.order_id: o.warehouse_id for o in snapshot.orders}
    targets = []
    for route in routing.routes:
        if not route.stops:
            continue
        start_s = route.stops[0].departure_at_s
        for stop in route.stops:
            if stop.stop_kind != "delivery":
                continue
            for oid in stop.order_ids:
                targets.append(WarehouseDepartureTarget(
                    order_id=oid, warehouse_id=order_to_warehouse[oid], departure_at_s=start_s,
                    vehicle_id=route.vehicle_id,
                ))
    return tuple(sorted(targets, key=lambda t: t.order_id))


def _quality(warehouse, routing):
    ready_by_order = {h.order_id: h.ready_at_s for h in warehouse.warehouse_handoffs}
    wait_s = 0
    for route in routing.routes:
        if not route.stops:
            continue
        departure_s = route.stops[0].departure_at_s
        for stop in route.stops:
            if stop.stop_kind == "delivery":
                for oid in stop.order_ids:
                    wait_s += max(0, departure_s - ready_by_order[oid])
    distance = sum(route.distance_m for route in routing.routes)
    makespan = max((op.end_s for op in warehouse.operations), default=0)
    duration = sum(route.duration_s for route in routing.routes)
    return (len(routing.unserved_orders), distance, wait_s, makespan, duration)


def _round(number: int, stage: str, accepted: bool, reason: str, warehouse=None, routing=None):
    if warehouse is None or routing is None:
        return CoordinationRound(round_number=number, stage=stage, accepted=accepted, reason=reason)
    unserved, distance, wait, makespan, _ = _quality(warehouse, routing)
    return CoordinationRound(
        round_number=number, stage=stage, accepted=accepted, reason=reason,
        distance_m=distance, unserved_count=unserved, total_handoff_wait_s=wait,
        warehouse_makespan_s=makespan, warehouse_solve_ms=warehouse.metadata.solve_ms,
        routing_solve_ms=routing.metadata.solve_ms,
    )


def coordinate(*, snapshot, order_ids: tuple[str, ...], budget_ms: int,
               max_coordination_rounds: int = 1, coordination_mode: str = "sequential") -> CandidatePlan:
    """Generate a fully valid candidate plan. Deep mode is explicit and opt-in.

    Initial pair and every feedback pair must pass warehouse, transport and
    cross-domain validation. Feedback failures NEVER discard the initial plan.
    The time budget is shared across rounds, not applied afresh to every solve.
    """
    if not order_ids:
        raise ValueError("order_ids_must_not_be_empty")
    if len(set(order_ids)) != len(order_ids):
        raise ValueError("duplicate_order_ids")
    if budget_ms <= 0:
        raise ValueError("budget_ms_must_be_positive")
    if max_coordination_rounds not in (1, 2, 3):
        raise ValueError("max_coordination_rounds_must_be_1_to_3")
    if coordination_mode not in ("sequential", "deep"):
        raise ValueError("invalid_coordination_mode")
    known = {o.order_id for o in snapshot.orders}
    missing = sorted(set(order_ids) - known)
    if missing:
        raise ValueError("unknown_orders:" + ",".join(missing))

    started = perf_counter()
    enable_feedback = coordination_mode == "deep" and max_coordination_rounds > 1
    # At 120s, the incumbent gets a full 60s R16-equivalent search.  In deep
    # 60s mode it gets 70% and leaves room for one feedback search.  R16
    # benchmarks always request sequential mode, keeping their old budgets.
    first_budget = (min(60_000, max(10_000, int(budget_ms * .70)))
                    if enable_feedback and budget_ms >= 20_000 else budget_ms)
    first_budget = min(first_budget, budget_ms)
    incumbent_wh, incumbent_rt = _solve_pair(
        snapshot=snapshot, order_ids=order_ids, budget_ms=first_budget,
    )
    initial_quality = _quality(incumbent_wh, incumbent_rt)
    rounds = [_round(1, "initial", True, "validated_initial_incumbent", incumbent_wh, incumbent_rt)]
    selected_round = 1

    if enable_feedback:
        for round_number in range(2, max_coordination_rounds + 1):
            remaining = budget_ms - int((perf_counter() - started) * 1000)
            if remaining < 5000:
                break
            targets = _departure_targets(snapshot, incumbent_rt)
            if not targets:
                break
            try:
                # Split only the remaining global time across remaining rounds.
                # Small residual budgets are spent on the current round instead
                # of pursuing an unreliable tiny last attempt.
                rounds_left = max_coordination_rounds - round_number + 1
                next_budget = remaining if remaining < 12000 else max(5000, remaining // rounds_left)
                # Coordination-layer portfolio: each round is a *different* candidate
                # (its own seed, hence its own warehouse schedule) and every candidate is
                # recorded. Selection stays lexicographic, so the incumbent can only be
                # replaced by a strictly better plan -- distance is never traded away, and
                # waiting only ever decides among distance-equal candidates.
                candidate_wh, candidate_rt = _solve_pair(
                    snapshot=snapshot, order_ids=order_ids,
                    budget_ms=next_budget, targets=targets, seed=17 + round_number,
                )
                new_quality = _quality(candidate_wh, candidate_rt)
                better = new_quality < _quality(incumbent_wh, incumbent_rt)
                rounds.append(_round(
                    round_number, "feedback", better,
                    "better_lexicographic_objective" if better else "feasible_not_better",
                    candidate_wh, candidate_rt,
                ))
                if better:
                    incumbent_wh, incumbent_rt = candidate_wh, candidate_rt
                    selected_round = round_number
                # R20: a neutral candidate no longer ends the search. It used to `break`
                # here, which meant one unlucky seed consumed the whole exploration budget;
                # the remaining rounds now try different seeds while budget allows.
            except Exception as exc:
                # Only the optional feedback phase can be rolled back. Validation
                # or solver failures never silently become accepted improvements.
                rounds.append(_round(round_number, "feedback", False, "rejected:" + str(exc)[:240]))
                break

    selected_quality = _quality(incumbent_wh, incumbent_rt)
    report = CoordinationReport(
        mode=coordination_mode, requested_rounds=max_coordination_rounds if enable_feedback else 1,
        attempted_rounds=len(rounds), selected_round=selected_round,
        baseline_distance_m=initial_quality[1], selected_distance_m=selected_quality[1],
        baseline_handoff_wait_s=initial_quality[2], selected_handoff_wait_s=selected_quality[2],
        rounds=tuple(rounds), objective=OBJECTIVE,
    )
    validation = ValidationReport(
        status="passed", validator_version="b03-deep-coordination-validator-2.0",
        checked_rule_ids=CHECKED_RULES, violations=(),
    )
    payload = {
        "snapshot_id": snapshot.snapshot_id, "snapshot_version": snapshot.version,
        "version": 1, "routing": incumbent_rt.model_dump(mode="json"),
        "warehouse": incumbent_wh.model_dump(mode="json"),
        "validation": validation.model_dump(mode="json"),
        "coordination": report.model_dump(mode="json"),
    }
    plan_hash = hashlib.sha256(
        json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
    return CandidatePlan(
        plan_id=f"plan_{uuid4().hex[:20]}",
        snapshot_id=snapshot.snapshot_id, snapshot_version=snapshot.version, version=1,
        plan_hash=plan_hash, routing=incumbent_rt, warehouse=incumbent_wh,
        validation=validation, coordination=report,
    )


def _aggregate_routing(results):
    if len(results) == 1:
        return results[0]
    first = results[0]
    return first.model_copy(update={
        "routes": tuple(route for result in results for route in result.routes),
        "warehouse_arrivals": tuple(a for result in results for a in result.warehouse_arrivals),
        "unserved_orders": tuple(u for result in results for u in result.unserved_orders),
        "metadata": SolveMetadata(
            status="optimal" if all(r.metadata.status == "optimal" for r in results) else "feasible",
            raw_status="B03_MULTI_WAREHOUSE_AGGREGATE", engine="OR-Tools RoutingModel",
            engine_version=first.metadata.engine_version, has_solution=True,
            proof_scope="independent request-local RoutingModel solves aggregated by warehouse",
            solve_ms=sum(r.metadata.solve_ms for r in results),
        ),
    })
