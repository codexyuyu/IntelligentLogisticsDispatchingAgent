"""Deterministic three-vehicle breakdown showcase with a REAL OR-Tools VRP.

Synthetic Liuzhou points and times, no GPS/navigation claim and no DB writes.
A truck finishes a delivery, breaks down at that safe handoff point, and
other trucks must collect its remaining cargo BEFORE their rescue deliveries.
Already completed work remains frozen. The solver may report infeasibility;
there are no pre-programmed candidate routes or asserted savings.
"""
from __future__ import annotations

from math import cos, hypot, radians
from itertools import permutations, product


DEPOT = 'demo-depot'
HANDOFF = 'demo-o3'
VEHICLES = ('demo-truck-01', 'demo-truck-02', 'demo-truck-03')
POINTS = {
    DEPOT: (24.3269, 109.4453),
    'demo-o1': (24.3320, 109.4200), 'demo-o2': (24.3430, 109.4230),
    HANDOFF: (24.3450, 109.4500), 'demo-o4': (24.3490, 109.4640),
    'demo-o5': (24.3340, 109.4770), 'demo-o6': (24.3120, 109.4690),
    'demo-o7': (24.3070, 109.4400), 'demo-o8': (24.3200, 109.4240),
}
# Every order is loaded at the depot before departure. Failure occurs AFTER O3
# completes; the undelivered O4/O5 units are physically transferred at O3.
ROUTES = {
    VEHICLES[0]: ('demo-o1', 'demo-o2'),
    VEHICLES[1]: (HANDOFF, 'demo-o4', 'demo-o5'),
    VEHICLES[2]: ('demo-o6', 'demo-o7', 'demo-o8'),
}
STOP_SERVICE_S = 70
TRANSFER_SERVICE_S = 80
VEHICLE_CAPACITY = 5
HORIZON = 6500
METERS_PER_SECOND = 9.0
DRIVE_CENTS_PER_KM = 140
SOFT_LATE_CENTS_PER_S = 2
SOFT_DUES = {'demo-o1': 1050, 'demo-o2': 1600, HANDOFF: 1200,
             'demo-o4': 1500, 'demo-o5': 2000, 'demo-o6': 1050,
             'demo-o7': 1900, 'demo-o8': 2500}


def _distance(a: str, b: str, points: dict) -> int:
    x, y = points[a], points[b]
    return max(0, round(hypot((x[0] - y[0]) * 111_000,
                              (x[1] - y[1]) * 111_000 * cos(radians((x[0] + y[0]) / 2)))))


def _travel(a: str, b: str, points: dict) -> int:
    return max(0, round(_distance(a, b, points) / METERS_PER_SECOND))


def _stop(node: str, arrival: int, departure: int, kind: str = 'delivery') -> dict:
    return {'node_id': node, 'kind': kind, 'arrival_s': arrival, 'departure_s': departure,
            'order_id': node if node.startswith('demo-o') else None}


def _baseline() -> tuple[dict, int]:
    result = {}
    for vehicle, orders in ROUTES.items():
        clock, current, distance = 0, DEPOT, 0
        stops = [_stop(DEPOT, 0, 0, 'depot_start')]
        for order in orders:
            distance += _distance(current, order, POINTS)
            clock += _travel(current, order, POINTS)
            stops.append(_stop(order, clock, clock + STOP_SERVICE_S))
            clock += STOP_SERVICE_S
            current = order
        distance += _distance(current, DEPOT, POINTS)
        clock += _travel(current, DEPOT, POINTS)
        stops.append(_stop(DEPOT, clock, clock, 'depot_end'))
        result[vehicle] = {'stops': stops, 'distance_m': distance}
    fault_time = next(s['departure_s'] for s in result[VEHICLES[1]]['stops'] if s['node_id'] == HANDOFF)
    return result, fault_time


def _continuation_at(stops: list[dict], fault_time: int, vehicle: str, points: dict):
    """Lock completed visits, and finish a service already in progress.

    Backup vehicles must never teleport or drop a partially serviced order.
    If driving, freeze their position on the current arc at the incident time.
    """
    frozen = [dict(s) for s in stops if s['departure_s'] <= fault_time and s['kind'] != 'depot_end']
    in_service = next((s for s in stops if s['kind'] == 'delivery'
                       and s['arrival_s'] <= fault_time < s['departure_s']), None)
    if in_service:
        frozen.append(dict(in_service))
        own_pending = [s['node_id'] for s in stops if s['kind'] == 'delivery'
                       and s['arrival_s'] > fault_time]
        return frozen, own_pending, in_service['node_id'], in_service['departure_s']
    future = [s['node_id'] for s in stops if s['kind'] == 'delivery' and s['arrival_s'] > fault_time]
    last = frozen[-1]
    upcoming = next((s for s in stops if s['arrival_s'] > fault_time), None)
    if upcoming and last['departure_s'] < fault_time:
        travel = max(1, upcoming['arrival_s'] - last['departure_s'])
        ratio = min(1, max(0, (fault_time - last['departure_s']) / travel))
        a, b = points[last['node_id']], points[upcoming['node_id']]
        key = f'demo-fault-position-{vehicle[-2:]}'
        points[key] = (a[0] + (b[0] - a[0]) * ratio, a[1] + (b[1] - a[1]) * ratio)
        frozen.append(_stop(key, fault_time, fault_time, 'waypoint'))
        current = key
    else:
        current = last['node_id']
        if last['departure_s'] < fault_time:
            frozen.append(_stop(current, fault_time, fault_time, 'wait'))
    return frozen, future, current, fault_time


def _simple_no_rescue(original: dict, fault_time: int, points: dict):
    """Breakdown truck stays at the handoff. Others continue their old routes."""
    tracks = []
    for vehicle, route in original.items():
        if vehicle == VEHICLES[1]:
            stops = [dict(s) for s in route['stops'] if s['departure_s'] <= fault_time and s['kind'] != 'depot_end']
            stops.append(_stop(HANDOFF, fault_time, HORIZON, 'broken_down'))
        else:
            stops = [dict(s) for s in route['stops']]
        tracks.append({'vehicle_id': vehicle, 'stops': stops})
    return tracks


def _metrics(tracks: list[dict], points: dict) -> dict:
    delivered = {}
    metres = 0
    for track in tracks:
        stops = track['stops']
        for a, b in zip(stops, stops[1:]):
            if a['node_id'] in points and b['node_id'] in points and a['node_id'] != b['node_id']:
                metres += _distance(a['node_id'], b['node_id'], points)
        for stop in stops:
            if stop['kind'] == 'delivery' and stop['node_id'] in SOFT_DUES:
                delivered[stop['node_id']] = stop['arrival_s']
    late_s = sum(max(0, delivered[o] - SOFT_DUES[o]) for o in delivered)
    cents = (metres * DRIVE_CENTS_PER_KM + 500) // 1000 + late_s * SOFT_LATE_CENTS_PER_S
    return {'total_orders': len(SOFT_DUES), 'delivered_orders': len(delivered),
            'undelivered_orders': len(SOFT_DUES) - len(delivered),
            'late_orders': sum(delivered[o] > SOFT_DUES[o] for o in delivered),
            'late_s': late_s, 'distance_m': metres, 'objective_cents': cents,
            'undelivered_order_ids': sorted(set(SOFT_DUES) - set(delivered)),
            'delivery_times': delivered,
            'note': '费用只含示意行驶成本和迟到罚金；未交付订单另行计数，不把未交付当作零损失。'}




def _seed_route_score(
    routes: list[list[str]], vehicles: tuple[str, ...], starts: dict[str, str],
    ready_times: dict[str, int], own_pending: dict[str, list[str]],
    pickups: dict[str, str], points: dict,
) -> tuple[int, str | None]:
    """Independently check a constructive plan against *business* constraints.

    This deliberately does not assume an OR-Tools answer.  It is a diagnostic
    lower-level check and a source of initial routes for the actual solver.
    Time windows are SOFT: late arrivals are penalized, not forbidden.
    """
    seen_deliveries: set[str] = set()
    seen_pickups: set[str] = set()
    expected_deliveries = set(pickups) | {o for vehicle in vehicles for o in own_pending[vehicle]}
    expected_pickups = set(pickups.values())
    score = 0
    for vi, vehicle in enumerate(vehicles):
        now, current, load = ready_times[vehicle], starts[vehicle], len(own_pending[vehicle])
        carried = set(own_pending[vehicle])
        for node in routes[vi]:
            now += _travel(current, node, points)
            score += _distance(current, node, points)
            if now > HORIZON:
                return score, f'{vehicle} 超过回放时限'
            if node in expected_pickups:
                order = next(order for order, pickup in pickups.items() if pickup == node)
                if node in seen_pickups or order in carried:
                    return score, f'{node} 重复交接'
                load += 1
                carried.add(order)
                seen_pickups.add(node)
                now += TRANSFER_SERVICE_S
            elif node in expected_deliveries:
                if node in seen_deliveries or node not in carried:
                    return score, f'{node} 未装货或重复送达'
                seen_deliveries.add(node)
                carried.remove(node)
                load -= 1
                score += max(0, now - SOFT_DUES[node]) * 8
                now += STOP_SERVICE_S
            else:
                return score, f'未识别的路线节点 {node}'
            if not 0 <= load <= VEHICLE_CAPACITY:
                return score, f'{vehicle} 载重超限'
            current = node
        now += _travel(current, DEPOT, points)
        score += _distance(current, DEPOT, points)
        if now > HORIZON or load != 0:
            return score, f'{vehicle} 返场超时或货物未送完'
    if seen_deliveries != expected_deliveries or seen_pickups != expected_pickups:
        return score, '订单覆盖或交接不完整'
    return score, None


def _construct_rescue_seeds(
    starts: dict[str, str], ready_times: dict[str, int],
    own_pending: dict[str, list[str]], pickups: dict[str, str], points: dict,
) -> list[tuple[int, list[list[str]]]]:
    """Enumerate small, physically feasible seeds; do NOT fix optimizer output.

    All 2**N assignments of stranded orders to the two available vehicles are
    considered.  RoutingModel may freely improve the order/assignment later.
    """
    vehicles = (VEHICLES[0], VEHICLES[2])
    rescued = tuple(pickups)
    plans: list[tuple[int, list[list[str]]]] = []
    for owners in product(range(len(vehicles)), repeat=len(rescued)):
        allocated = {v: [o for o, owner in zip(rescued, owners) if owner == vi]
                     for vi, v in enumerate(vehicles)}
        alternatives: list[list[list[str]]] = []
        for vehicle in vehicles:
            orders = allocated[vehicle]
            # Deliver existing cargo first, so the initial routes are also
            # feasible for trucks already travelling or unloading at failure.
            variants = []
            for pickup_order in permutations(orders):
                for delivery_order in permutations(orders):
                    variants.append([*own_pending[vehicle],
                                     *(pickups[o] for o in pickup_order),
                                     *delivery_order])
            alternatives.append(variants)
        for routes in product(*alternatives):
            candidate = [list(r) for r in routes]
            score, reason = _seed_route_score(candidate, vehicles, starts, ready_times,
                                              own_pending, pickups, points)
            if reason is None:
                plans.append((score, candidate))
    plans.sort(key=lambda row: row[0])
    # Deduplicate while preserving increasing objective cost.
    unique: dict[tuple[tuple[str, ...], ...], tuple[int, list[list[str]]]] = {}
    for score, routes in plans:
        unique.setdefault(tuple(tuple(route) for route in routes), (score, routes))
    return list(unique.values())




def _load_change(node: str, pickup_nodes: set[str], *, at_vehicle_start: bool = False) -> int:
    """Demand is applied on departure, except for an already-serviced start."""
    if at_vehicle_start:
        return 0
    if node in pickup_nodes:
        return 1
    if node in SOFT_DUES:
        return -1
    return 0


def _service_seconds(node: str, pickup_nodes: set[str], *, at_vehicle_start: bool = False) -> int:
    """No second unloading/transfer service at a continuation start."""
    if at_vehicle_start:
        return 0
    if node in pickup_nodes:
        return TRANSFER_SERVICE_S
    if node in SOFT_DUES:
        return STOP_SERVICE_S
    return 0


def _validate_candidate(
    candidate: list[dict], frozen: dict[str, list[dict]], own_pending: dict[str, list[str]],
    pickups: dict[str, str], points: dict, fault_time: int,
) -> list[str]:
    """Independent of OR-Tools: check load, time, every order, and pickup order."""
    errors: list[str] = []
    if sorted(track['vehicle_id'] for track in candidate) != sorted(VEHICLES):
        return ['候选车辆集合不完整']
    delivered: list[str] = []
    pickup_count: dict[str, int] = {order: 0 for order in pickups}
    pickup_by_order = {node: order for order, node in pickups.items()}
    for track in candidate:
        vehicle, stops = track['vehicle_id'], track['stops']
        if vehicle == VEHICLES[1]:
            if not stops or stops[-1]['kind'] != 'broken_down' or stops[-1]['node_id'] != HANDOFF:
                errors.append('故障车辆未停运于交接点')
            if any(s['kind'] == 'delivery' and s['node_id'] in pickups for s in stops):
                errors.append('故障车辆继续投递滞留货物')
            continue
        prefix = frozen[vehicle]
        if stops[:len(prefix)] != prefix:
            errors.append(f'{vehicle} 冻结前缀被改变')
            continue
        if not stops or stops[-1]['kind'] != 'depot_end' or stops[-1]['node_id'] != DEPOT:
            errors.append(f'{vehicle} 未返场')
            continue
        carried = set(own_pending[vehicle])
        load = len(carried)
        previous = prefix[-1]
        for stop in stops[len(prefix):]:
            node, kind = stop['node_id'], stop['kind']
            if node not in points:
                errors.append(f'未知地理节点 {node}')
                continue
            if stop['arrival_s'] < previous['departure_s'] + _travel(previous['node_id'], node, points):
                errors.append(f'{vehicle} 在 {node} 行驶时间不足，轨迹不连续')
            if stop['departure_s'] < stop['arrival_s'] or stop['departure_s'] > HORIZON:
                errors.append(f'{vehicle} 在 {node} 服务时间或时限异常')
            if kind == 'pickup':
                order = pickup_by_order.get(node)
                if order is None or order in carried:
                    errors.append(f'{vehicle} 在 {node} 取货无效')
                else:
                    carried.add(order)
                    pickup_count[order] += 1
                if stop['departure_s'] != stop['arrival_s'] + TRANSFER_SERVICE_S:
                    errors.append(f'{vehicle} 在 {node} 交接时长异常')
                load += 1
            elif kind == 'delivery':
                if node not in carried:
                    errors.append(f'{vehicle} 在 {node} 未装货即配送')
                else:
                    carried.remove(node)
                delivered.append(node)
                if stop['departure_s'] != stop['arrival_s'] + STOP_SERVICE_S:
                    errors.append(f'{vehicle} 在 {node} 卸货时长异常')
                load -= 1
            elif kind != 'depot_end':
                errors.append(f'{vehicle} 出现未知作业 {kind}')
            if not 0 <= load <= VEHICLE_CAPACITY:
                errors.append(f'{vehicle} 在 {node} 载重超限')
            previous = stop
        if carried or load != 0:
            errors.append(f'{vehicle} 返场时存在未配送货物')
    all_delivered = delivered + [HANDOFF, 'demo-o1']
    if sorted(all_delivered) != sorted(SOFT_DUES):
        errors.append('全部订单未恰好交付一次')
    if any(count != 1 for count in pickup_count.values()):
        errors.append('救援货物未恰好交接一次')
    return errors


def solve_breakdown_showcase(budget_ms: int = 1800) -> dict:
    """Compute an actual vehicle rescue solve, no persisted operational action."""
    from logistics_optimization.fault_rescue import routing_bindings

    pywrapcp, routing_enums_pb2 = routing_bindings()

    if not isinstance(budget_ms, int) or not (100 <= budget_ms <= 5000):
        raise ValueError('budget_ms must be 100..5000')
    baseline, fault_time = _baseline()
    points = dict(POINTS)
    frozen = {}
    own_pending = {}
    start_nodes = {}
    continuation_times = {}
    for vehicle in (VEHICLES[0], VEHICLES[2]):
        prefix, waiting, current, ready_at = _continuation_at(baseline[vehicle]['stops'], fault_time, vehicle, points)
        frozen[vehicle], own_pending[vehicle], start_nodes[vehicle] = prefix, waiting, current
        continuation_times[vehicle] = ready_at
    broken_prefix = [dict(s) for s in baseline[VEHICLES[1]]['stops']
                     if s['kind'] != 'depot_end' and s['departure_s'] <= fault_time]
    rescue_orders = list(ROUTES[VEHICLES[1]][1:])
    # Two distinct pickup nodes at the same safe roadside handoff point.
    pickups = {order: f'demo-pickup-{order}' for order in rescue_orders}
    for key in pickups.values():
        points[key] = points[HANDOFF]
    node_ids = [start_nodes[v] for v in (VEHICLES[0], VEHICLES[2])]
    node_ids.append(DEPOT)
    node_ids.extend(o for v in (VEHICLES[0], VEHICLES[2]) for o in own_pending[v])
    for order in rescue_orders:
        node_ids.extend((pickups[order], order))
    if len(node_ids) != len(set(node_ids)):
        raise ValueError('showcase nodes must be unique')
    id_index = {node: i for i, node in enumerate(node_ids)}
    manager = pywrapcp.RoutingIndexManager(len(node_ids), 2, [0, 1], [2, 2])
    routing = pywrapcp.RoutingModel(manager)

    pickup_node_ids = set(pickups.values())

    def travel(from_index, to_index):
        a, b = node_ids[manager.IndexToNode(from_index)], node_ids[manager.IndexToNode(to_index)]
        # A continuation START represents a vehicle *after* its last completed
        # delivery/service, not an ordinary delivery visit.  Counting its
        # service again shifts arrival times and corrupts the replay.
        return _travel(a, b, points) + _service_seconds(
            a, pickup_node_ids, at_vehicle_start=routing.IsStart(from_index))

    def cost(from_index, to_index):
        a, b = node_ids[manager.IndexToNode(from_index)], node_ids[manager.IndexToNode(to_index)]
        return max(1, _distance(a, b, points))

    travel_callback = routing.RegisterTransitCallback(travel)
    cost_callback = routing.RegisterTransitCallback(cost)
    routing.SetArcCostEvaluatorOfAllVehicles(cost_callback)
    routing.AddDimension(travel_callback, HORIZON, HORIZON, False, 'Time')
    time_dimension = routing.GetDimensionOrDie('Time')
    for vi in range(2):
        ready_at = continuation_times[(VEHICLES[0], VEHICLES[2])[vi]]
        time_dimension.CumulVar(routing.Start(vi)).SetRange(ready_at, ready_at)
        time_dimension.CumulVar(routing.End(vi)).SetRange(fault_time, HORIZON)
    for node in node_ids[3:]:
        index = manager.NodeToIndex(id_index[node])
        if node in SOFT_DUES:
            time_dimension.CumulVar(index).SetRange(fault_time, HORIZON)
            # Meter-based distance is the primary cost; penalties trade off
            # late service and extra pickup detours in a documented unit.
            time_dimension.SetCumulVarSoftUpperBound(index, SOFT_DUES[node], 8)
    def demand(index):
        # CRITICAL FIX: truck 01 starts at already-delivered O1 with ONE unit
        # (O2) remaining.  The old callback subtracted O1 a SECOND time at
        # RoutingModel.Start(0): 1 -> 0, then O2 -> -1, making every route
        # infeasible even though two other vehicles have spare capacity.
        if routing.IsEnd(index):
            return 0
        node = node_ids[manager.IndexToNode(index)]
        return _load_change(node, pickup_node_ids, at_vehicle_start=routing.IsStart(index))
    demand_callback = routing.RegisterUnaryTransitCallback(demand)
    routing.AddDimensionWithVehicleCapacity(demand_callback, 0, [VEHICLE_CAPACITY]*2, False, 'Load')
    load_dim = routing.GetDimensionOrDie('Load')
    for vi, v in enumerate((VEHICLES[0], VEHICLES[2])):
        load_dim.CumulVar(routing.Start(vi)).SetRange(len(own_pending[v]), len(own_pending[v]))
        for node in own_pending[v]:
            idx = manager.NodeToIndex(id_index[node])
            routing.solver().Add(routing.VehicleVar(idx) == vi)
    for order in rescue_orders:
        pickup = manager.NodeToIndex(id_index[pickups[order]])
        dropoff = manager.NodeToIndex(id_index[order])
        routing.AddPickupAndDelivery(pickup, dropoff)
        routing.solver().Add(routing.VehicleVar(pickup) == routing.VehicleVar(dropoff))
        routing.solver().Add(time_dimension.CumulVar(pickup) <= time_dimension.CumulVar(dropoff))
    # The original cold start frequently timed out without any solution and
    # misleadingly called that "capacity infeasible".  This fixture has a
    # constructive route (01 finishes O2, visits O3, then O4/O5).  Verify
    # feasible routes independently, let OR-Tools validate their constraints,
    # then optimize FROM an accepted starting assignment.
    seed_plans = _construct_rescue_seeds(start_nodes, continuation_times,
                                         own_pending, pickups, points)
    diagnostic = {'physical_seed_count': len(seed_plans),
                  'ortools_seed_accepted': False, 'attempts': [],
                  'cause': None}
    parameters = pywrapcp.DefaultRoutingSearchParameters()
    parameters.first_solution_strategy = routing_enums_pb2.FirstSolutionStrategy.PATH_CHEAPEST_ARC
    parameters.local_search_metaheuristic = routing_enums_pb2.LocalSearchMetaheuristic.GUIDED_LOCAL_SEARCH
    parameters.time_limit.FromMilliseconds(budget_ms)
    parameters.log_search = False
    solution = None
    for seed_score, routes in seed_plans[:8]:
        try:
            proposed = routing.ReadAssignmentFromRoutes(
                [[id_index[node] for node in route] for route in routes], True)
        except Exception as exc:
            diagnostic['attempts'].append({'stage': 'seed_read', 'result': type(exc).__name__})
            continue
        if proposed is None:
            diagnostic['attempts'].append({'stage': 'seed_read', 'result': 'rejected'})
            continue
        diagnostic['ortools_seed_accepted'] = True
        diagnostic['attempts'].append({'stage': 'seed_read', 'result': 'accepted',
                                       'distance_lateness_score': seed_score})
        # Once the RoutingModel accepted a complete route, this is a genuine
        # solver-based optimization; never synthesize a "solved" response.
        solution = routing.SolveFromAssignmentWithParameters(proposed, parameters)
        diagnostic['attempts'].append({'stage': 'warm_solve',
                                       'result': 'solved' if solution else 'no_solution'})
        if solution:
            break
    if solution is None:
        # A second search strategy is useful when a model has no acceptable
        # warm start.  Failure after a time limit is NOT proof of infeasibility.
        parameters.first_solution_strategy = routing_enums_pb2.FirstSolutionStrategy.PARALLEL_CHEAPEST_INSERTION
        solution = routing.SolveWithParameters(parameters)
        diagnostic['attempts'].append({'stage': 'cold_solve',
                                       'result': 'solved' if solution else 'no_solution'})
    diagnostic['routing_status_code'] = routing.status()
    response = {'case_id': 'wenchang-three-truck-breakdown-v1', 'name': '文昌校区 · 三车冷链故障接管',
        'mode': 'synthetic_solver_showcase', 'source_kind': 'synthetic', 'real_gps': False,
        'solver': 'OR-Tools RoutingModel', 'incident_kind': 'vehicle_breakdown',
        'failure_vehicle_id': VEHICLES[1], 'failure_node_id': HANDOFF,
        'failure_time_s': fault_time, 'horizon_s': HORIZON,
        'baseline': [{'vehicle_id': v, 'stops': info['stops']} for v, info in baseline.items()],
        'no_rescue': _simple_no_rescue(baseline, fault_time, points),
        'points': {key: [lat, lng] for key, (lat, lng) in points.items()},
        'rescue_order_ids': rescue_orders, 'solver_budget_ms': budget_ms,
        'solver_diagnostic': diagnostic,
        'assumptions': [
            '所有订单为等量冷链货品，车辆容量5件；故障发生在已完成O3交付的安全交接点',
            '救援车辆必须先到故障交接点收取货品，之后才能交付O4/O5',
            '其他车辆在故障时刻的位置、已完成订单均保持不变，未完成订单由OR-Tools重新规划',
            '地理坐标和路段时间是柳州合成演示值，非高德导航/GPS；审批仅影响本次浏览器演示',
        ],
    }
    response['metrics'] = {'baseline': _metrics(response['baseline'], points),
                           'no_rescue': _metrics(response['no_rescue'], points)}
    if not solution:
        if seed_plans and not diagnostic['ortools_seed_accepted']:
            status = 'model_invalid'
            reason = '已验证业务可行的救援路线，但 OR-Tools 模型拒绝所有初始解；请检查车辆载重/时刻建模'
        elif seed_plans:
            status = 'no_solution_within_budget'
            reason = '存在业务可行的接管路线，但 OR-Tools 在搜索预算内未返回解，不能断言无解'
        else:
            status = 'no_solution_within_budget'
            reason = '未构造出满足容量、时序和交接约束的初始路线；未证明整个模型无解'
        diagnostic['cause'] = status
        return {**response, 'status': status, 'candidate': [], 'candidate_valid': False,
                'reason': reason}
    candidate = [{'vehicle_id': VEHICLES[1], 'stops': [*broken_prefix,
        _stop(HANDOFF, fault_time, HORIZON, 'broken_down')]}]
    assignments = {}
    for vi, vehicle in enumerate((VEHICLES[0], VEHICLES[2])):
        stops = [dict(s) for s in frozen[vehicle]]
        index = routing.Start(vi)
        while not routing.IsEnd(index):
            nxt = solution.Value(routing.NextVar(index))
            if routing.IsEnd(nxt):
                t = solution.Value(time_dimension.CumulVar(nxt))
                stops.append(_stop(DEPOT, t, t, 'depot_end'))
                break
            node = node_ids[manager.IndexToNode(nxt)]
            t = solution.Value(time_dimension.CumulVar(nxt))
            kind = 'pickup' if node in pickups.values() else 'delivery'
            service = TRANSFER_SERVICE_S if kind == 'pickup' else STOP_SERVICE_S
            stops.append(_stop(node, t, t + service, kind))
            if kind == 'delivery': assignments[node] = vehicle
            index = nxt
        candidate.append({'vehicle_id': vehicle, 'stops': stops})
    candidate.sort(key=lambda route: VEHICLES.index(route["vehicle_id"]))
    # Independent checks after OR-Tools: not merely "found a solution".
    validation_errors = _validate_candidate(candidate, frozen, own_pending,
                                            pickups, points, fault_time)
    valid = not validation_errors
    diagnostic['candidate_checks'] = validation_errors or ['passed']
    comparison = _metrics(candidate, points)
    return {**response, 'status': 'solved' if valid else 'invalid', 'candidate_valid': valid,
            'candidate': candidate, 'metrics': {**response['metrics'], 'candidate': comparison},
            'reassigned_order_ids': [order for order in rescue_orders if assignments.get(order) != VEHICLES[1]],
            'rescue_assignments': {order: assignments.get(order) for order in rescue_orders},
            'recovered_orders': comparison['delivered_orders'] - response['metrics']['no_rescue']['delivered_orders'],
            'reason': None if valid else '独立校验失败，禁止采用候选：' + '；'.join(validation_errors[:3]),
            'objective_note': '对比优先判断恢复交付数量；距离/成本可能上升，不承诺节省费用。'}
