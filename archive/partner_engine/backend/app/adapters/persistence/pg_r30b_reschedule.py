"""R30-B read-only, state-aware exception and constrained suffix replanning.

A source R27/R28 run is independently reconciled before use. The solver NEVER
moves an in-transit truck to the depot: only trucks still physically at WH001
and never departed can enter the one-trip OR-Tools solver. Onboard consignments
on a disabled truck remain stranded until a separately verified transfer exists.
All historical events are immutable; this is a forecast, not execution data.
"""
from __future__ import annotations

from collections import Counter, defaultdict
from datetime import timedelta
from dataclasses import dataclass
from hashlib import sha256
import json
from typing import Literal

from app.adapters.persistence.pg_r28_reconciliation import reconcile
from app.contracts.common import TimeWindow
from app.contracts.entities import PlanningSnapshot, ScheduledOperation
from app.contracts.planning import CandidatePlan, RoutingRequest, WarehouseScheduleRequest
from app.domain.plan_rules import validate_plan
from app.domain.transport_rules import validate_transport


class RescheduleInputError(ValueError):
    pass


@dataclass(frozen=True)
class ExceptionSpec:
    event_type: Literal['vehicle_breakdown', 'delivery_delay', 'warehouse_resource_failure', 'inventory_quarantine']
    object_id: str
    occurred_at_s: int
    delay_s: int = 0


def _delivery_stops(route):
    return ((oid, stop) for stop in route.stops if stop.stop_kind == 'delivery' for oid in stop.order_ids)


def _delivery_by_plan(plan):
    return {oid: (route.vehicle_id, stop) for route in plan.routing.routes for oid, stop in _delivery_stops(route)}


def _location_at(route, t: int) -> dict:
    """A route leg, not a fictitious GPS point. No assumptions about road geometry."""
    if not route.stops:
        return {'state': 'at_depot', 'node_id': None}
    preceding = route.stops[0]
    for stop in route.stops[1:]:
        if t < stop.arrival_at_s and t > preceding.departure_at_s:
            return {'state': 'in_transit_between_nodes', 'from_node_id': preceding.node_id,
                    'to_node_id': stop.node_id, 'location_accuracy': 'leg_only_not_gps'}
        if t <= stop.departure_at_s:
            return {'state': 'at_stop', 'node_id': stop.node_id, 'location_accuracy': 'schedule_estimate'}
        preceding = stop
    return {'state': 'returned_to_depot', 'node_id': route.stops[-1].node_id}


def _time_shift_route(route, snapshot, t: int, delay_s: int):
    """Preserve the reached stops, propagate extra transit time, check hard windows.

    If service would break constraints, halt at that leg; outstanding loaded goods
    remain onboard, never reassigned automatically. Returns (route, blocked IDs).
    """
    orders = {o.order_id: o for o in snapshot.orders}
    vehicles = {v.vehicle_id: v for v in snapshot.vehicles}
    shifted = []
    offset = delay_s
    violated = False
    blocked = []
    for stop in route.stops:
        if stop.arrival_at_s <= t or stop.departure_at_s <= t:
            # Work already in progress is a locked physical fact. Apply the
            # extra travel time to the NEXT leg, never the current stop.
            shifted.append(stop)
            continue
        if violated:
            blocked.extend(stop.order_ids)
            shifted.append(stop)
            continue
        if stop.stop_kind == 'delivery':
            order = orders[stop.order_ids[0]]
            arrived = stop.arrival_at_s + offset
            service = max(arrived, order.service_window.start_s)
            end = service + order.service_duration_s
            if service > order.service_window.end_s or end > order.freshness_deadline_s:
                violated = True
                blocked.extend(stop.order_ids)
                shifted.append(stop)
                continue
            previous_delta = stop.departure_at_s + offset
            offset += max(0, end - previous_delta)
            shifted.append(stop.model_copy(update={'arrival_at_s': arrived,
                'service_start_at_s': service, 'departure_at_s': end}))
        else:
            arrived = stop.arrival_at_s + offset
            if stop.stop_kind == 'depot_end' and arrived > vehicles[route.vehicle_id].shift_window.end_s:
                violated = True
                shifted.append(stop)
                continue
            shifted.append(stop.model_copy(update={'arrival_at_s': arrived,
                'service_start_at_s': arrived, 'departure_at_s': arrived}))
    if violated:
        return route, tuple(blocked), False
    start = shifted[0].departure_at_s
    end = shifted[-1].arrival_at_s
    return route.model_copy(update={'stops': tuple(shifted), 'duration_s': end - start}), (), True


def _hard_check_original(snapshot, plan, events):
    if plan.validation.status != 'passed':
        raise RescheduleInputError('r30b_baseline_not_validated')
    if reconcile(snapshot, plan, events)['status'] != 'passed':
        raise RescheduleInputError('r30b_baseline_r28_check_failed')
    issues = validate_plan(snapshot=snapshot.model_dump(mode='python'),
        order_ids=tuple(o.order_id for o in snapshot.orders),
        warehouse=plan.warehouse.model_dump(mode='python'),
        routing=plan.routing.model_dump(mode='python'))
    if issues:
        raise RescheduleInputError('r30b_baseline_cross_domain_invalid:' + issues[0]['rule_id'])


def _check_future_stock(snapshot, future_ids, event_t):
    """Fail closed on lot depletion, temperature mismatch and expiry.

    Accounting uses the initial snapshot before operations. Every batch's
    original planned scope must fit its on-hand stock, not just the smaller
    replan subset; other current reservations are excluded as unavailable.
    """
    lots = {lot.batch_id: lot for lot in snapshot.stock_lots}
    used = defaultdict(int)
    for order in snapshot.orders:
        used[order.batch_id] += order.quantity_units
    blocked = {}
    now = snapshot.origin_at + timedelta(seconds=event_t)
    for order in snapshot.orders:
        if order.order_id not in future_ids:
            continue
        lot = lots.get(order.batch_id)
        if lot is None:
            blocked[order.order_id] = 'inventory_batch_missing_no_verified_stock'
        elif lot.warehouse_id != order.warehouse_id or lot.temperature_zone != order.temperature_zone:
            blocked[order.order_id] = 'inventory_warehouse_or_temperature_mismatch'
        elif lot.expires_at <= now:
            blocked[order.order_id] = 'inventory_batch_expired_at_event'
        elif used[order.batch_id] > max(0, lot.on_hand_units - lot.reserved_units - lot.quarantined_units):
            blocked[order.order_id] = 'inventory_insufficient_unreserved_stock'
    return blocked


def _eligible_inventory(snapshot, future_ids, quarantined_batch_id):
    """No imaginary replenishment or speculative substitution of recorded orders."""
    blocked = {}
    batches = {lot.batch_id: lot for lot in snapshot.stock_lots}
    for order in snapshot.orders:
        if order.order_id not in future_ids:
            continue
        if order.batch_id != quarantined_batch_id:
            continue
        # The recorded order/lot binding is authoritative. A new lot requires a
        # verified allocation operation, absent from R30-A. Do not fake it.
        blocked[order.order_id] = 'inventory_batch_quarantined_no_verified_reallocation'
    if quarantined_batch_id not in batches:
        raise RescheduleInputError('r30b_batch_not_in_snapshot')
    return blocked


def _validate_transition(*, snapshot, base_plan, base_events, t, future_schedule,
                         future_routing, fresh_order_ids, historical_delivered,
                         immutable_routes, reasons, revised_events, changed_operations,
                         effective_future_orders, event, any_warehouse_failure):
    """Independent accounting, immutable history and cross-domain suffix proof.

    Future-only plans are NOT the R28 full-history plan; R28 is applied to the
    baseline and its domain invariants are rechecked on the changed suffix.
    """
    errors = []
    def check(condition, label):
        if not condition: errors.append(label)
    old_prefix = [e for e in base_events if e['time_s'] <= t]
    revised_prefix = [e for e in revised_events if e['time_s'] <= t and e['kind'] != 'exception_occurred']
    check(old_prefix == revised_prefix, 'past_event_history_changed')
    all_ids = {o.order_id for o in snapshot.orders}
    delivered_now = Counter(e['object_id'] for e in revised_events if e['kind'] == 'order_delivered')
    check(set(delivered_now) | set(reasons) == all_ids, 'unaccounted_orders')
    check(not (set(delivered_now) & set(reasons)), 'served_and_unserved_overlap')
    check(all(n == 1 for n in delivered_now.values()), 'duplicate_delivery_event')
    check(historical_delivered.issubset(delivered_now), 'completed_delivery_missing')
    check(not (historical_delivered & set(fresh_order_ids)), 'completed_order_replanned')
    check(all(v not in {event.object_id} for v in (future_routing.routes if future_routing else ())
              if event.event_type == 'vehicle_breakdown' for v in [v.vehicle_id]), 'failed_vehicle_reused')
    old_scheduled = {op.operation_id: op for op in base_plan.warehouse.operations}
    new_scheduled = {op.operation_id: op for op in (future_schedule.operations if future_schedule else ())}
    for oid, old in old_scheduled.items():
        if old.start_s <= t and not (any_warehouse_failure and old.resource_id == event.object_id and old.end_s > t):
            check(oid not in new_scheduled or new_scheduled[oid] == old,
                  'already_started_warehouse_task_modified:' + oid)
    if future_routing:
        report = validate_transport(request=RoutingRequest(snapshot=effective_future_orders,
            order_ids=tuple(fresh_order_ids), warehouse_handoffs=future_schedule.warehouse_handoffs,
            budget={'remaining_ms': 1000, 'max_workers': 1, 'random_seed': 17}).model_dump(mode='python'),
            result=future_routing.model_dump(mode='python'))
        errors.extend('routing:' + v for v in report.violations)
        check(future_routing.metadata.has_solution, 'future_routing_not_solved')
    if future_schedule:
        check(future_schedule.metadata.has_solution, 'future_warehouse_not_solved')
        # Handoffs must derive strictly from finished scheduled operations.
        by_work = {p.operation_id: p for p in future_schedule.operations}
        for handoff in future_schedule.warehouse_handoffs:
            max_finish = max((by_work[op.operation_id].end_s for op in effective_future_orders.operations
                if handoff.order_id in op.order_ids and op.operation_id in by_work), default=0)
            check(handoff.ready_at_s == max_finish, 'handoff_not_from_cpsat:' + handoff.order_id)
        for op in changed_operations:
            check(op.start_s >= t, 'new_operation_before_event:' + op.operation_id)
            if any_warehouse_failure:
                check(op.resource_id != event.object_id, 'failed_resource_reused:' + op.operation_id)
    # A stranded in-transit package may be reported blocked, but never inserted
    # into a second depot-origin route as if it had magically been unloaded.
    for vid, route in immutable_routes.items():
        check(not (future_routing and any(r.vehicle_id == vid for r in future_routing.routes)),
              'moving_vehicle_entered_depot_solver:' + vid)
    return errors


def run_reschedule(*, baseline: dict, spec: ExceptionSpec, budget_ms: int = 60000,
                   warehouse_solver=None, routing_solver=None) -> dict:
    """Create and independently verify one read-only R30B suffix forecast.

    Solvers can be injected by tests; production uses existing CP-SAT/Routing.
    PostgreSQL is not accessed or mutated by this function.
    """
    if not 0 <= spec.occurred_at_s or not 500 <= budget_ms <= 120000:
        raise RescheduleInputError('r30b_event_time_or_budget_invalid')
    if spec.event_type == 'delivery_delay' and not 1 <= spec.delay_s <= 86400:
        raise RescheduleInputError('r30b_delay_must_be_1_to_86400_seconds')
    snapshot = PlanningSnapshot.model_validate(baseline['snapshot'])
    plan = CandidatePlan.model_validate(baseline['plan'])
    base_events = baseline['events']
    _hard_check_original(snapshot, plan, base_events)
    if len(snapshot.warehouses) != 1:
        raise RescheduleInputError('r30b_requires_one_active_warehouse')
    horizon = max((e['time_s'] for e in base_events), default=0)
    if spec.occurred_at_s >= horizon:
        raise RescheduleInputError('r30b_event_must_precede_baseline_completion')
    t = spec.occurred_at_s
    vehicle_routes = {r.vehicle_id: r for r in plan.routing.routes if r.stops}
    operation_by_id = {x.operation_id: x for x in snapshot.operations}
    scheduled_by_id = {x.operation_id: x for x in plan.warehouse.operations}
    all_ids = {o.order_id for o in snapshot.orders}
    if spec.event_type in ('vehicle_breakdown', 'delivery_delay') and spec.object_id not in {v.vehicle_id for v in snapshot.vehicles}:
        raise RescheduleInputError('r30b_vehicle_not_found')
    if spec.event_type == 'warehouse_resource_failure' and spec.object_id not in {r.resource_id for r in snapshot.resources}:
        raise RescheduleInputError('r30b_resource_not_found')
    if spec.event_type == 'inventory_quarantine' and spec.object_id not in {lot.batch_id for lot in snapshot.stock_lots}:
        raise RescheduleInputError('r30b_batch_not_found')

    completed = {e['object_id'] for e in base_events if e['kind'] == 'order_delivered' and e['time_s'] <= t}
    already_finished_ops = {o.operation_id for o in plan.warehouse.operations if o.end_s <= t}
    active_ops = {o.operation_id for o in plan.warehouse.operations if o.start_s <= t < o.end_s}
    departed = {vid for vid, route in vehicle_routes.items() if route.stops[0].departure_at_s <= t}
    active_vehicles = {vid for vid in departed if vehicle_routes[vid].stops[-1].arrival_at_s > t}
    returned = departed - active_vehicles
    never_departed = {v.vehicle_id for v in snapshot.vehicles} - departed
    on_board = {oid for vid in active_vehicles for oid, stop in _delivery_stops(vehicle_routes[vid])
                if stop.departure_at_s > t}
    issues: dict[str, str] = {}
    suspended_at: dict[str, dict] = {}
    warning_notes = []
    future_shifted_routes = {}
    interrupted_operation_ids = set()
    
    if spec.event_type == 'vehicle_breakdown':
        if spec.object_id in active_vehicles:
            route = vehicle_routes[spec.object_id]
            stranded = {oid for oid, stop in _delivery_stops(route) if stop.departure_at_s > t}
            issues.update({oid: 'stranded_on_disabled_vehicle_requires_verified_transfer' for oid in stranded})
            suspended_at[spec.object_id] = _location_at(route, t)
        elif spec.object_id in never_departed:
            suspended_at[spec.object_id] = {'state': 'at_depot', 'node_id': next(v.start_node_id for v in snapshot.vehicles if v.vehicle_id == spec.object_id)}
        else:
            warning_notes.append('failed_vehicle_already_returned_no_remaining_duties')
    if spec.event_type == 'delivery_delay':
        if spec.object_id in active_vehicles:
            route = vehicle_routes[spec.object_id]
            shifted, blocked, feasible = _time_shift_route(route, snapshot, t, spec.delay_s)
            if feasible:
                future_shifted_routes[spec.object_id] = shifted
            else:
                # Original route projection must stop at event time if re-timing
                # violates customer/driver deadlines. Do not fabricate a delivery.
                remaining = {oid for oid, stop in _delivery_stops(route) if stop.departure_at_s > t}
                issues.update({oid: 'in_transit_delay_exceeds_window_requires_operator_intervention' for oid in remaining})
                suspended_at[spec.object_id] = _location_at(route, t)
        elif spec.object_id in never_departed:
            warning_notes.append('predeparture_delay_shifts_vehicle_earliest_start')
        else:
            warning_notes.append('delay_after_return_no_remaining_duties')

    if spec.event_type == 'warehouse_resource_failure':
        interrupted_operation_ids = {oid for oid, work in scheduled_by_id.items()
                                     if work.resource_id == spec.object_id and work.end_s > t}
        for op_id in interrupted_operation_ids:
            for oid in operation_by_id[op_id].order_ids:
                if oid not in completed and oid not in on_board:
                    issues[oid] = 'warehouse_resource_unavailable_no_verified_substitute'
        for oid in on_board:
            # Already loaded goods are physically outside; a new warehouse event
            # cannot undo the loading operation retrospectively.
            issues.pop(oid, None)
    if spec.event_type == 'inventory_quarantine':
        # Unsafe cargo already on the road must not remain a projected success.
        # Suspend its carrier and mark EVERY remaining parcel on that vehicle
        # for manual assessment; no invisible transshipment or fabricated recall.
        by_order = {o.order_id:o for o in snapshot.orders}
        exposed = {oid for oid in on_board if by_order[oid].batch_id == spec.object_id}
        for vid in active_vehicles:
            route = vehicle_routes[vid]
            if not any(oid in exposed for oid,_ in _delivery_stops(route)):
                continue
            suspended_at[vid] = _location_at(route,t)
            for oid, stop in _delivery_stops(route):
                if stop.departure_at_s > t:
                    issues[oid] = ('onboard_quarantined_batch_requires_recall' if oid in exposed
                                   else 'delivery_paused_due_to_vehicle_quality_hold')
        flagged = _eligible_inventory(snapshot, all_ids - completed - on_board, spec.object_id)
        # Quarantine cannot recall cargo already delivered or onboard without a
        # separate recall workflow. Those are explicitly reported as at risk.
        issues.update(flagged)
        # Any unfinished pick/load touching an isolated batch stops at the
        # exception boundary. A task that STARTED before t is a historical
        # fact; its future completion must not be silently counted as safe.
        interrupted_operation_ids.update(
            work.operation_id for work in plan.warehouse.operations
            if work.end_s > t and any(
                order_id not in completed and by_order[order_id].batch_id == spec.object_id
                for order_id in operation_by_id[work.operation_id].order_ids)
        )
        warning_notes.append('already_delivered_cargo_cannot_be_recalled_by_readonly_simulation')

    # A truck currently on the road is not an available depot vehicle, even
    # when its route has remaining orders. A returned truck is not reused:
    # existing B02 is one-trip-per-vehicle.
    # The normal baseline is already a checked plan, but a fresh exception
    # cannot rely on implicit or unrecorded inventory substitutions.
    issues.update(_check_future_stock(snapshot, all_ids - completed - on_board, t))
    available_ids = never_departed - ({spec.object_id} if spec.event_type == 'vehicle_breakdown' else set())
    prospective = all_ids - completed - on_board - set(issues)
    # Future routing must be distinct from in-transit original commitments.
    previous_assignment = _delivery_by_plan(plan)
    selected_operations = tuple(op for op in snapshot.operations
                                if any(oid in prospective for oid in op.order_ids))
    frozen_ops = tuple(work for work in plan.warehouse.operations
                       if work.start_s <= t and work.operation_id not in interrupted_operation_ids)
    # If the resource will fail, all operations using that resource after t
    # become unservable, even when they are not on the baseline's immediate
    # critical path. CP-SAT must NOT silently choose an unrecorded dock.
    if spec.event_type == 'warehouse_resource_failure':
        for op in selected_operations:
            if op.resource_id == spec.object_id and op.operation_id not in already_finished_ops:
                for oid in op.order_ids:
                    issues[oid] = 'warehouse_resource_unavailable_no_verified_substitute'
        prospective -= set(issues)
        selected_operations = tuple(op for op in selected_operations
                                    if all(oid in prospective for oid in op.order_ids))
    resource_models = []
    for resource in snapshot.resources:
        if resource.resource_id == spec.object_id and spec.event_type == 'warehouse_resource_failure':
            last = max([t + 1] + [x.end_s for x in resource.available_windows])
            resource = resource.model_copy(update={'unavailable_windows': resource.unavailable_windows + (TimeWindow(start_s=t, end_s=last),)})
        resource_models.append(resource)
    # Only orders still awaiting work enter the suffix. Frozen work carries the
    # real historic start/end and blocks simultaneous resource usage.
    adapted_ops = tuple(op if op.operation_id in {f.operation_id for f in frozen_ops}
                        else op.model_copy(update={'release_at_s': max(t + 1, op.release_at_s)})
                        for op in selected_operations)
    potential_orders = tuple(o for o in snapshot.orders if o.order_id in prospective)
    # Warehouse run uses unchanged 'required' status. Routing can drop orders
    # only with an explicit unserved explanation, never silently.
    future_snapshot = snapshot.model_copy(update={
        'version': snapshot.version + 1, 'simulation_time_s': t,
        'orders': potential_orders, 'operations': adapted_ops, 'resources': tuple(resource_models),
        'vehicles': tuple(v.model_copy(update={
            'available_at_s': max(v.available_at_s, t + 1 + (spec.delay_s if spec.event_type == 'delivery_delay' and v.vehicle_id == spec.object_id else 0))})
            for v in snapshot.vehicles if v.vehicle_id in available_ids),
        'frozen_operations': frozen_ops,
    })
    future_snapshot = PlanningSnapshot.model_validate(future_snapshot.model_dump(mode='python'))
    from app.adapters.warehouse.cp_sat_scheduler import CpSatWarehouseScheduler
    from app.adapters.routing.ortools_solver import OrToolsRoutingSolver
    warehouse_solver = warehouse_solver or CpSatWarehouseScheduler()
    routing_solver = routing_solver or OrToolsRoutingSolver()
    planned_future = None
    planned_routes = None
    future_validations = []
    if prospective:
        wh_request = WarehouseScheduleRequest(snapshot=future_snapshot, order_ids=tuple(sorted(prospective)),
            budget={'remaining_ms': max(1000, budget_ms // 2), 'max_workers': 1, 'random_seed': 17})
        planned_future = warehouse_solver.schedule(wh_request)
        if not planned_future.metadata.has_solution:
            issues.update({oid:'warehouse_reschedule_infeasible:' + planned_future.metadata.raw_status
                           for oid in prospective})
        elif available_ids:
            routing_snapshot = future_snapshot.model_copy(update={
                'orders': tuple(o.model_copy(update={'required': False}) for o in future_snapshot.orders),
            })
            routing_snapshot = PlanningSnapshot.model_validate(routing_snapshot.model_dump(mode='python'))
            req = RoutingRequest(snapshot=routing_snapshot, order_ids=tuple(sorted(prospective)),
                warehouse_handoffs=planned_future.warehouse_handoffs,
                budget={'remaining_ms': max(1000, budget_ms // 2), 'max_workers': 1, 'random_seed': 17})
            planned_routes = routing_solver.solve(req)
            if not planned_routes.metadata.has_solution:
                issues.update({oid:'routing_reschedule_infeasible:' + planned_routes.metadata.raw_status for oid in prospective})
                planned_routes = None
            else:
                future_validations = list(validate_transport(request=req.model_dump(mode='python'),
                    result=planned_routes.model_dump(mode='python')).violations)
                if future_validations:
                    raise RuntimeError('r30b_future_transport_invalid:' + ','.join(future_validations[:5]))
                for dropped in planned_routes.unserved_orders:
                    issues[dropped.order_id] = 'routing_unserved:' + dropped.reason_code
        else:
            issues.update({oid:'no_remaining_unstarted_vehicle_at_depot' for oid in prospective})
    # Validated prediction events ONLY; remove old future events from routes that
    # were never dispatched, or are now disabled. Past event timestamps are immutable.
    prefix = [dict(e) for e in base_events if e['time_s'] <= t]
    immutable_future = []
    for vid in departed:
        route = vehicle_routes.get(vid)
        if route is None or vid in suspended_at:
            continue
        effective = future_shifted_routes.get(vid, route)
        for entry in _route_events(effective):
            if entry['time_s'] > t:
                immutable_future.append(entry)
    new_work_events = []
    # An operation already underway at the event is a physical fact, even
    # when the remaining CP-SAT problem is infeasible. Retain its completion
    # forecast unless it was interrupted by the failure itself.
    for work in plan.warehouse.operations:
        if work.start_s <= t < work.end_s and work.operation_id not in interrupted_operation_ids:
            op = operation_by_id[work.operation_id]
            new_work_events.append({'time_s': work.end_s,'kind':'warehouse_work_finished',
                'object_id':work.operation_id,'resource_id':work.resource_id,
                'order_ids':list(op.order_ids),'operation_kind':op.operation_kind})
    if planned_future:
        for work in planned_future.operations:
            if work.operation_id in interrupted_operation_ids:
                continue
            op = operation_by_id[work.operation_id]
            if work.start_s > t:
                new_work_events.append({'time_s':work.start_s,'kind':'warehouse_work_start',
                    'object_id':work.operation_id,'resource_id':work.resource_id,
                    'order_ids':list(op.order_ids),'operation_kind':op.operation_kind})
            if work.end_s > t:
                new_work_events.append({'time_s':work.end_s,'kind':'warehouse_work_finished',
                    'object_id':work.operation_id,'resource_id':work.resource_id,
                    'order_ids':list(op.order_ids),'operation_kind':op.operation_kind})
        for handoff in planned_future.warehouse_handoffs:
            if handoff.ready_at_s > t:
                new_work_events.append({'time_s':handoff.ready_at_s,'kind':'loading_ready',
                                        'object_id':handoff.order_id,'warehouse_id':handoff.warehouse_id})
    new_route_events = [e for route in (planned_routes.routes if planned_routes else ())
                        for e in _route_events(route) if e['time_s'] > t]
    # Avoid representing any explicitly blocked order as a future delivery.
    all_new = [e for e in immutable_future + new_work_events + new_route_events
               if not (e['kind']=='order_delivered' and e['object_id'] in issues)]
    merged = prefix + all_new
    # Frozen/in-progress operations may be projected both from history and
    # from the CP-SAT suffix. One physical completion is only one event.
    seen_keys = set()
    unique = []
    for entry in merged:
        key = (entry['time_s'], entry['kind'], entry['object_id'])
        if key not in seen_keys:
            unique.append(entry)
            seen_keys.add(key)
    merged = unique
    priority = {'warehouse_work_start':0,'warehouse_work_finished':1,'loading_ready':2,
                'vehicle_departure':3,'order_delivered':4,'vehicle_return':5}
    merged.sort(key=lambda e:(e['time_s'],priority.get(e['kind'],9),e['object_id']))
    delivered_ids = {e['object_id'] for e in merged if e['kind']=='order_delivered'}
    for oid in all_ids - delivered_ids - set(issues):
        issues[oid] = 'remaining_service_unresolved_not_assumed_delivered'
    # Frozen completed tasks are attached only to future scopes that require
    # them, and their original times are retained in the projection.
    old_work = {x.operation_id:x for x in plan.warehouse.operations}
    new_work = {x.operation_id:x for x in (planned_future.operations if planned_future and planned_future.metadata.has_solution else ())}
    changed_works = [op for oid, op in new_work.items() if oid not in old_work or op != old_work[oid]]
    next_work = {k:v for k,v in old_work.items() if v.end_s <= t or (v.start_s <= t and k not in interrupted_operation_ids)}
    next_work.update(new_work)
    next_handoffs = {h.order_id:h for h in plan.warehouse.warehouse_handoffs if h.ready_at_s <= t}
    if planned_future and planned_future.metadata.has_solution:
        next_handoffs.update({h.order_id:h for h in planned_future.warehouse_handoffs})
    next_routes = {vid:route for vid, route in vehicle_routes.items() if vid in departed}
    next_routes.update(future_shifted_routes)
    if planned_routes:
        next_routes.update({r.vehicle_id:r for r in planned_routes.routes if r.stops})
    # We keep an interrupted route's original geometry for precise position at
    # event t; the UI freezes it there, and suppresses its invalid future events.
    route_values = list(next_routes.values())
    merged.append({'time_s':t, 'kind':'exception_occurred', 'object_id':spec.object_id,
                   'exception_type':spec.event_type, 'source_kind':'explicit_operator_simulation'})
    merged.sort(key=lambda e:(e['time_s'], priority.get(e['kind'],6), e['object_id']))
    reconstructed = plan.model_dump(mode='json')
    reconstructed['plan_id'] = 'plan_r30e_' + sha256((plan.plan_hash+spec.event_type+spec.object_id+str(t)+str(spec.delay_s)).encode()).hexdigest()[:16]
    reconstructed['version'] = plan.version + 1
    reconstructed['warehouse']['operations'] = [x.model_dump(mode='json') for x in sorted(next_work.values(),key=lambda x:(x.start_s,x.operation_id))]
    reconstructed['warehouse']['warehouse_handoffs'] = [x.model_dump(mode='json') for x in next_handoffs.values()]
    reconstructed['routing']['routes'] = [x.model_dump(mode='json') for x in route_values]
    reconstructed['routing']['unserved_orders'] = [{'order_id':oid,'reason_code':reason} for oid,reason in sorted(issues.items())]
    # Composite replay is visual history + suffix, not a legally executable
    # CandidatePlan. Expose that distinction in the embedded validation field.
    reconstructed['validation'] = {'status':'not_checked',
        'validator_version':'r30b-replay-visual-projection-not-executable',
        'checked_rule_ids':[], 'violations':[]}
    reconstructed['plan_hash'] = sha256(json.dumps(reconstructed,sort_keys=True,ensure_ascii=False).encode()).hexdigest()
    assignment_before = {oid:vid for oid,(vid,stop) in previous_assignment.items()}
    assignment_after = {oid:vid for route in route_values for oid,stop in _delivery_stops(route) if oid in delivered_ids}
    effects = [{'order_id':oid,'previous_vehicle_id':assignment_before.get(oid),
                'next_vehicle_id':assignment_after.get(oid),
                'previous_delivery_at_s': previous_assignment[oid][1].departure_at_s if oid in previous_assignment else None,
                'new_delivery_at_s':next((e['time_s'] for e in merged if e['kind']=='order_delivered' and e['object_id']==oid),None),
                'status': 'completed_before_event' if oid in completed else 'unserved' if oid in issues else 'planned',
                'unserved_reason_code': issues.get(oid)}
               for oid in sorted(all_ids)]
    locked_routes = {vid:vehicle_routes[vid] for vid in active_vehicles if vid not in suspended_at}
    validation_errors = _validate_transition(snapshot=snapshot,base_plan=plan,base_events=base_events,
        t=t,future_schedule=planned_future if planned_future and planned_future.metadata.has_solution else None,
        future_routing=planned_routes,fresh_order_ids=tuple(sorted(prospective)),
        historical_delivered=completed,immutable_routes=locked_routes,
        reasons=issues,revised_events=merged,changed_operations=changed_works,
        effective_future_orders=(routing_snapshot if planned_routes else future_snapshot),
        event=spec,any_warehouse_failure=spec.event_type=='warehouse_resource_failure')
    if validation_errors:
        raise RuntimeError('r30b_transition_validation_failed:' + ';'.join(validation_errors[:8]))
    if any(e['kind']=='order_delivered' and e['object_id'] in completed and e['time_s']>t for e in merged):
        raise RuntimeError('r30b_completed_order_redelivered')
    from app.adapters.persistence.pg_r30e_evidence import build_impact_evidence
    impact = build_impact_evidence(
        baseline=baseline, replay_events=merged,
        next_operations={oid: work.model_dump(mode='json') for oid, work in next_work.items()},
        interrupted_operation_ids=interrupted_operation_ids,
        order_changes=effects, event_t=t, halted_vehicles=suspended_at,
    )
    return {
        'mode':'r30b_event_sourced_readonly_suffix_projection',
        'database_mutated':False,'business_plans_mutated':False,
        'source':baseline['source'],'source_meta':baseline.get('meta',{}),
        'previous_plan_id':plan.plan_id,'previous_plan_version':plan.version,
        'new_plan_id':reconstructed['plan_id'],'new_plan_version':reconstructed['version'],
        'event':{'event_type':spec.event_type,'object_id':spec.object_id,'occurred_at_s':t,
                 'delay_s':spec.delay_s,'source_kind':'explicit_operator_simulation'},
        'state':{'completed_order_ids':sorted(completed),'completed_operation_ids':sorted(already_finished_ops),
                 'active_operation_ids':sorted(active_ops), 'in_transit_vehicle_ids':sorted(active_vehicles),
                 'returned_vehicle_ids':sorted(returned),'not_yet_departed_vehicle_ids':sorted(never_departed),
                 'onboard_pending_order_ids':sorted(on_board),'available_depot_vehicle_ids':sorted(available_ids),
                 'halted_vehicle_positions':suspended_at,'interrupted_operation_ids':sorted(interrupted_operation_ids)},
        'impact_evidence':impact,
        'comparison':{'order_changes':effects,'changed_warehouse_operations':[x.model_dump(mode='json') for x in changed_works],
                      'changed_vehicle_ids':sorted({vid for oid,vid in assignment_after.items() if assignment_before.get(oid)!=vid}
                                                   | set(suspended_at) | set(future_shifted_routes)),
                      'unserved_orders':[{'order_id':oid,'reason_code':reason} for oid,reason in sorted(issues.items())],
                      'delivered_before_event':len(completed),'forecast_delivered_total':len(delivered_ids),
                      'unserved_total':len(issues),'changed_delivery_count':sum(1 for e in effects if e['previous_vehicle_id'] != e['next_vehicle_id']),
                      'warnings':warning_notes},
        'verification':{'status':'passed','baseline_r28':'passed','future_transport':'passed' if planned_routes else 'not_applicable',
                        'suffix_accounting':'passed','no_teleport':'passed_by_depot_vehicle_exclusion',
                        'partial_service_allowed':bool(issues),'violations':[]},
        'solver':{'warehouse':planned_future.model_dump(mode='json') if planned_future else None,
                  'routing':planned_routes.model_dump(mode='json') if planned_routes else None,
                  'warehouse_status':planned_future.metadata.raw_status if planned_future else 'no_pending_warehouse_work',
                  'routing_status':planned_routes.metadata.raw_status if planned_routes else 'no_feasible_or_available_depot_route'},
        'replay':{'snapshot':baseline['snapshot'],'plan':reconstructed,'events':merged,
                  'halted_vehicles':{vid:{'from_s':t,'until_s':10**9} for vid in suspended_at},
                  'disclaimer':'read_only_projection; interrupted_original_route_geometry_is_reference_only; vehicles_frozen_at_event; no_actual_telemetry'},
        'baseline':baseline,
    }


def _route_events(route) -> list[dict]:
    if not route.stops:
        return []
    events=[{'time_s':route.stops[0].departure_at_s,'kind':'vehicle_departure',
             'object_id':route.vehicle_id,'order_ids':[oid for oid,_ in _delivery_stops(route)]}]
    for oid, stop in _delivery_stops(route):
        events.append({'time_s':stop.departure_at_s,'kind':'order_delivered',
                       'object_id':oid,'vehicle_id':route.vehicle_id})
    events.append({'time_s':route.stops[-1].arrival_at_s,'kind':'vehicle_return','object_id':route.vehicle_id})
    return events
