"""SimPy simulation kernel (P12-01 subset).

Processes are created only inside the adapter; no SimPy object crosses the boundary. Stop
service times are relative seconds. The engine is deterministic for the same request and seed;
stochastic policies will be added when the event scheduler lands.
"""

from __future__ import annotations

from collections import defaultdict
from uuid import uuid4

import simpy

from logistics_domain.simulation import (
    SimulationEvent,
    SimulationEventKind,
    SimulationRequest,
    SimulationResult,
    SimulationStatus,
)


class SimPySimulationEngine:
    def run(self, request: SimulationRequest) -> SimulationResult:
        if not isinstance(request, SimulationRequest):
            raise TypeError("SimPySimulationEngine expects SimulationRequest")
        env = simpy.Environment()
        events: list[SimulationEvent] = []
        delivered: set = set()
        by_route = defaultdict(list)
        for stop in request.stops:
            by_route[stop.route_id].append(stop)
        route_vehicle = {route.id: route.vehicle_id for route in request.plan.routes}
        for route_id, stops in by_route.items():
            ordered = sorted(stops, key=lambda item: item.sequence)
            for index, stop in enumerate(ordered):
                env.process(self._visit(env, stop, index == len(ordered) - 1,
                                        route_vehicle.get(route_id), events, delivered))
        env.run(until=request.until_s)
        return SimulationResult(status=SimulationStatus.COMPLETED,
            final_time_s=int(env.now), events=tuple(events),
            delivered_order_ids=tuple(sorted(delivered, key=str)), seed=request.seed)

    def _visit(self, env, stop, is_last, vehicle_id, events, delivered):
        yield env.timeout(max(0, stop.arrival_s - env.now))
        events.append(SimulationEvent(uuid4(), int(env.now), SimulationEventKind.ARRIVAL,
                                      vehicle_id, None, stop.id))
        yield env.timeout(max(0, stop.service_start_s - env.now))
        events.append(SimulationEvent(uuid4(), int(env.now), SimulationEventKind.SERVICE_START,
                                      vehicle_id, None, stop.id))
        yield env.timeout(max(0, stop.departure_s - env.now))
        events.append(SimulationEvent(uuid4(), int(env.now), SimulationEventKind.DEPARTURE,
                                      vehicle_id, None, stop.id))
        if is_last:
            for task_id in stop.task_ids:
                delivered.add(task_id)
                events.append(SimulationEvent(uuid4(), int(env.now),
                    SimulationEventKind.DELIVERED, vehicle_id, task_id, stop.id))
