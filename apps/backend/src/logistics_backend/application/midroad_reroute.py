"""Conservative, simulation-only mid-road continuation with a real Routing solve.

A truck cannot teleport: freeze its travelled prefix, hold on its current arc,
complete that same arc and its next service stop, then solve ONLY the pending
stops from the reached node with the actual onboard load. Other trucks and the
immutable checked plan are untouched. Failure is explicit; the caller may
choose the independently verified hold/resume fallback.
"""
from __future__ import annotations

from copy import deepcopy
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid5

from logistics_backend.application.integration_simulation_tracks import (
    SimulationTrackError, _segment, sample_track,
)
from logistics_backend.application.timeline import PRIORITY
from logistics_contracts.transport import TransportProblemDTO, TransportSolutionDTO
from logistics_domain.errors import InvalidInputError
from logistics_domain.planning import SolveBudget, SolveStatus
from logistics_domain.primitives import TimeWindow
from logistics_domain.transport import RoutingNodeKind
from logistics_optimization.transport.solver import OrToolsTransportSolver
from logistics_optimization.validation.transport import validate_transport

NAMESPACE = UUID('58e428a1-f15d-4e78-957f-b6317eb79f0a')


def _unresolved(reason: str) -> dict:
    return {'status': 'not_resolved', 'reason': reason, 'applied_to_simulation': False}


def _new_event(kind, when, object_id, vehicle, route_id, incident_id, *, order_id=None, node_id=None):
    return {'id': str(uuid5(NAMESPACE, f'{incident_id}:{kind}:{object_id}:{when}')),
            'kind': kind, 'time_s': when, 'object_id': str(object_id),
            'order_id': order_id, 'vehicle_id': vehicle,
            'route_id': route_id, 'node_id': node_id}


def optimize_midroad_continuation(result: dict, tracks: list[dict], events: list[dict],
                                   vehicle_id: str, at_s: int, delay_s: int,
                                   budget_ms: int, incident_id: str) -> dict:
    """Return a validated, fully materialized projection, or a failure reason.

    No database mutation. Do not call this as a substitute for operator approval.
    Only running mid-arc incidents with a next scheduled service are supported.
    """
    if delay_s <= 0 or budget_ms < 100 or budget_ms > 12000:
        return _unresolved('invalid_delay_or_budget')
    track = next((item for item in tracks if item['vehicle_id'] == vehicle_id), None)
    if track is None:
        return _unresolved('vehicle_not_in_plan')
    leg = next((item for item in track['segments']
                if item['start_s'] < at_s < item['end_s']), None)
    if leg is None or leg['kind'] != 'travel':
        return _unresolved('must_be_between_nodes')
    anchor_id = leg['to_node_id']
    stop_index = next((i for i, stop in enumerate(track['stops'])
                       if stop['node_id'] == anchor_id and stop['arrival_s'] == leg['end_s']), None)
    if stop_index is None or stop_index >= len(track['stops']) - 1:
        return _unresolved('no_remaining_stops_after_anchor')
    try:
        problem = TransportProblemDTO.model_validate(result['transport_problem']).to_domain()
        baseline = TransportSolutionDTO.model_validate(result['transport_solution']).to_domain()
        if baseline.candidate is None:
            return _unresolved('baseline_missing')
        anchor = track['stops'][stop_index]
        nodes = {node.id: node for node in problem.nodes}
        anchor_node = nodes[UUID(anchor_id)]
        # Must finish this arc and serve the anchor before changing destination.
        anchor_arrival = leg['end_s'] + delay_s
        anchor_departure = anchor_arrival + anchor_node.service_s
        if anchor_arrival > anchor_node.hard_window.latest_s:
            return _unresolved('anchor_hard_window_exceeded')
        old_route = next(route for route in baseline.candidate.routes
                         if str(route.vehicle_id) == vehicle_id)
        ordered_stops = sorted((s for s in baseline.stops if s.route_id == old_route.id),
                               key=lambda s: s.sequence)
        if [str(s.node_id) for s in ordered_stops] != [s['node_id'] for s in track['stops']]:
            return _unresolved('baseline_stop_mismatch')
        if ordered_stops[stop_index].load_after.weight_g < 0:
            return _unresolved('invalid_onboard_load')
        original_vehicle = next(v for v in problem.vehicles if str(v.vehicle_id) == vehicle_id)
        spent_drive = sum(s['end_s'] - s['start_s'] for s in track['segments']
                          if s['kind'] in ('travel', 'return') and s['end_s'] <= at_s)
        spent_drive += at_s - leg['start_s'] + (leg['end_s'] - at_s)
        remaining_drive = original_vehicle.max_drive_s - spent_drive
        upper = min(original_vehicle.available_window.latest_s,
                    result['warehouse_problem']['snapshot']['scope']['horizon_s'])
        if remaining_drive <= 0 or anchor_departure >= upper:
            return _unresolved('continuation_outside_vehicle_window')
        local_nodes = tuple(nodes[s.node_id] for s in ordered_stops[stop_index + 1:])
        if not local_nodes or not any(n.kind == RoutingNodeKind.DELIVERY for n in local_nodes):
            return _unresolved('no_remaining_deliveries')
        local_vehicle = replace(original_vehicle, start_node_id=anchor_node.location_id,
                                start_load=ordered_stops[stop_index].load_after,
                                available_window=TimeWindow(anchor_departure, upper),
                                max_drive_s=remaining_drive)
        local_problem = replace(problem, nodes=local_nodes, vehicles=(local_vehicle,))
        budget = SolveBudget(wall_time_ms=budget_ms,
                             deadline_utc=(datetime.now(UTC) + timedelta(seconds=60)).replace(microsecond=0),
                             max_candidates=1, seed=0, worker_count=1,
                             deterministic_test_mode=False)
        solution = OrToolsTransportSolver().solve(local_problem, budget)
        if solution.status not in (SolveStatus.FEASIBLE, SolveStatus.OPTIMAL) or solution.candidate is None:
            return _unresolved('local_routing_infeasible')
        if solution.optional_unserved_order_ids or len(solution.candidate.routes) != 1:
            return _unresolved('remaining_stops_not_served')
        report = validate_transport(solution.candidate, local_problem, solution.stops)
        if not report.valid:
            return _unresolved('local_hard_validation_failed')
        new_stops = sorted(solution.stops, key=lambda s: s.sequence)
        if {str(s.node_id) for s in new_stops} != {str(n.id) for n in local_nodes}:
            return _unresolved('pending_stops_not_preserved')
        # Build the physically continuous track: old prefix / freeze / complete
        # current road / serve anchor / use verified optimized suffix.
        prefix = [deepcopy(s) for s in track['segments'] if s['end_s'] <= leg['start_s']]
        if at_s > leg['start_s']:
            fraction = sample_track(track, at_s)['progress']
            prefix.append({**leg, 'end_s': at_s, 'end_fraction': fraction})
        else:
            fraction = leg['start_fraction']
        prefix.append(_segment(leg['from_node_id'], leg['to_node_id'], at_s,
                               at_s + delay_s, 'hold', fraction, fraction))
        prefix.append(_segment(leg['from_node_id'], leg['to_node_id'], at_s + delay_s,
                               anchor_arrival, 'travel', fraction, leg['end_fraction']))
        prefix.append(_segment(anchor_id, anchor_id, anchor_arrival,
                               anchor_departure, 'service', 0.0, 0.0))
        new_segments = list(prefix)
        cursor, departure = anchor_id, anchor_departure
        indices = {str(node_id): i for i, node_id in enumerate(problem.matrix.node_ids)}
        visited_location = anchor_node.location_id
        for stop in new_stops:
            if stop.arrival_s < departure or stop.departure_s < stop.arrival_s:
                return _unresolved('non_monotone_suffix')
            edge = problem.matrix.travel_s[indices[str(visited_location)]][indices[str(nodes[stop.node_id].location_id)]]
            if edge is None or stop.arrival_s - departure < edge:
                return _unresolved('missing_or_impossible_travel_arc')
            visited_location = nodes[stop.node_id].location_id
            new_segments.append(_segment(cursor, str(stop.node_id), departure, stop.arrival_s, 'travel'))
            new_segments.append(_segment(str(stop.node_id), str(stop.node_id),
                                         stop.arrival_s, stop.departure_s, 'service', 0.0, 0.0))
            cursor, departure = str(stop.node_id), stop.departure_s
        last_location = nodes[new_stops[-1].node_id].location_id
        end_location = original_vehicle.end_node_id
        return_time = problem.matrix.travel_s[indices[str(last_location)]][indices[str(end_location)]]
        if return_time is None:
            return _unresolved('return_arc_blocked')
        end_s = departure + return_time
        if end_s > upper:
            return _unresolved('return_outside_availability')
        new_segments.append(_segment(cursor, track['end_node_id'], departure, end_s, 'return'))
        # Preserve original history and the anchor service; no completed
        # pickup/delivery may be repeated in the generated suffix.
        next_stops = deepcopy(track['stops'][:stop_index + 1])
        next_stops[-1]['arrival_s'] = anchor_arrival
        next_stops[-1]['departure_s'] = anchor_departure
        start_index = len(next_stops)
        next_stops.extend({'node_id': str(stop.node_id), 'sequence': start_index + i,
                           'arrival_s': stop.arrival_s, 'departure_s': stop.departure_s,
                           'task_ids': [str(x) for x in stop.task_ids],
                           'kind': nodes[stop.node_id].kind.value,
                           'order_id': str(nodes[stop.node_id].order_id) if nodes[stop.node_id].order_id else None}
                          for i, stop in enumerate(new_stops))
        updated = deepcopy(tracks)
        replacement = next(t for t in updated if t['vehicle_id'] == vehicle_id)
        replacement['segments'], replacement['stops'] = new_segments, next_stops
        new_events = [deepcopy(e) for e in events if e.get('vehicle_id') != vehicle_id or e['time_s'] <= at_s]
        for stop in [next_stops[stop_index], *next_stops[stop_index+1:]]:
            kind = 'order_handoff' if stop['kind'] == 'pickup' else 'order_delivered'
            if stop['kind'] not in ('pickup', 'delivery'):
                continue
            time_s = stop['arrival_s'] if kind == 'order_handoff' else stop['departure_s']
            new_events.append(_new_event(kind, time_s, stop['order_id'], vehicle_id,
                                         track['route_id'], incident_id,
                                         order_id=stop['order_id'], node_id=stop['node_id']))
        new_events.append(_new_event('vehicle_return', end_s, vehicle_id, vehicle_id,
                                     track['route_id'], incident_id, node_id=track['end_node_id']))
        new_events.append(_new_event('transport_delay', at_s, vehicle_id, vehicle_id,
                                     track['route_id'], incident_id))
        new_events.sort(key=lambda e: (e['time_s'], PRIORITY.get(e['kind'], -1),
                                       str(e['object_id']), str(e['id'])))
        for i, event in enumerate(new_events):
            event['sequence'] = i
        old_future = {e['order_id']: e['time_s'] for e in events
                      if e['kind'] == 'order_delivered' and e['vehicle_id'] == vehicle_id and e['time_s'] > at_s}
        new_future = {e['order_id']: e['time_s'] for e in new_events
                      if e['kind'] == 'order_delivered' and e['vehicle_id'] == vehicle_id and e['time_s'] > at_s}
        if not old_future or old_future.keys() != new_future.keys():
            return _unresolved('delivery_coverage_changed')
        if len(new_future) != sum(e['kind'] == 'order_delivered' and e.get('vehicle_id') == vehicle_id
                                 and e['time_s'] > at_s for e in new_events):
            return _unresolved('duplicate_delivery')
        baseline_hold_return = next(e['time_s'] for e in events
                                    if e['kind'] == 'vehicle_return' and e['vehicle_id'] == vehicle_id) + delay_s
        # Avoid a nominal reroute that worsens both delivery completion and return.
        if end_s > baseline_hold_return and sum(new_future.values()) >= sum(t+delay_s for t in old_future.values()):
            return _unresolved('no_improvement_vs_hold')
        changed = [s['node_id'] for s in next_stops[stop_index+1:]] != [s['node_id'] for s in track['stops'][stop_index+1:]]
        return {'status': 'resolved', 'reason': None, 'applied_to_simulation': True,
                'strategy': 'simulated_local_reroute' if changed else 'simulated_local_retimed',
                'route_changed': changed, 'anchor_node_id': anchor_id,
                'solver_engine': solution.engine_metadata.name, 'solver_status': solution.status.value,
                'candidate_tracks': updated, 'candidate_events': new_events,
                'impact': {'affected_order_ids': list(old_future),
                           'before_eta_s': old_future, 'after_eta_s': new_future,
                           'violations': [], 'valid': True}, 'proposal_valid': True}
    except (KeyError, ValueError, TypeError, IndexError, StopIteration,
            RuntimeError, OverflowError, SimulationTrackError, InvalidInputError) as exc:
        return _unresolved(f'continuation_input_invalid:{type(exc).__name__}')
