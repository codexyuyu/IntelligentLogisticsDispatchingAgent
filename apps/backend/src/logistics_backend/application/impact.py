"""Deterministic impact closure and reschedule boundary (P14 subset).

This is a pure read model over an already validated transport plan and its stop rows. It
never mutates the plan, never invents a new candidate and never writes a schedule.
"""

from __future__ import annotations

from collections import defaultdict
from uuid import UUID

from logistics_contracts.impact import ImpactAnalysisDTO, ImpactRequestDTO
from logistics_contracts.mapping import boundary_dto, impact_report_dto
from logistics_domain.execution import AtNodeLocation
from logistics_domain.impact import (
    ImpactReasonPath,
    ImpactReport,
    RescheduleBoundary,
    ResourceBlock,
    VirtualStart,
)
from logistics_domain.planning import content_hash
from logistics_domain.primitives import EntityRef
from logistics_domain.states import EntityKind


class ImpactService:
    def analyse(self, request: ImpactRequestDTO) -> ImpactAnalysisDTO:
        envelope = request.event.to_domain()
        plan = request.plan.to_domain()
        stops = tuple(stop.to_domain() for stop in request.stops)
        payload = envelope.payload
        reference = payload.entity_ref
        event_time = request.event_time_s
        routes_by_vehicle = {route.vehicle_id: route for route in plan.routes}
        routes_by_id = {route.id: route for route in plan.routes}
        stops_by_route = defaultdict(list)
        stops_by_task = defaultdict(list)
        for stop in stops:
            stops_by_route[stop.route_id].append(stop)
            for task_id in stop.task_ids:
                stops_by_task[task_id].append(stop)
        affected_orders: set[UUID] = set()
        affected_tasks: set[UUID] = set()
        affected_resources: set[UUID] = set()
        affected_routes: set[UUID] = set()
        if reference.kind == EntityKind.ORDER:
            affected_orders.add(reference.id)
            for stop in stops_by_task.get(reference.id, ()):
                affected_tasks.update(stop.task_ids)
                affected_routes.add(stop.route_id)
        elif reference.kind == EntityKind.VEHICLE:
            affected_resources.add(reference.id)
            route = routes_by_vehicle.get(reference.id)
            if route is not None:
                affected_routes.add(route.id)
                for stop in stops_by_route.get(route.id, ()):
                    affected_tasks.update(stop.task_ids)
        else:
            affected_resources.add(reference.id)
            for stop in stops:
                if stop.node_id == reference.id:
                    affected_tasks.update(stop.task_ids)
                    affected_routes.add(stop.route_id)
            if not affected_tasks:
                for stop in stops:
                    affected_tasks.update(stop.task_ids)
        # Multi-hop closure over task -> stop -> route -> vehicle -> route tasks.
        for _ in range(4):
            before = (len(affected_orders), len(affected_tasks), len(affected_routes),
                      len(affected_resources))
            for route_id in tuple(affected_routes):
                route = routes_by_id.get(route_id)
                if route is None:
                    continue
                affected_resources.add(route.vehicle_id)
                for stop in stops_by_route.get(route_id, ()):
                    affected_tasks.update(stop.task_ids)
            for task_id in tuple(affected_tasks):
                affected_orders.add(task_id)
                for stop in stops_by_task.get(task_id, ()):
                    affected_routes.add(stop.route_id)
            for order_id in tuple(affected_orders):
                for stop in stops_by_task.get(order_id, ()):
                    affected_tasks.update(stop.task_ids)
                    affected_routes.add(stop.route_id)
            after = (len(affected_orders), len(affected_tasks), len(affected_routes),
                     len(affected_resources))
            if after == before:
                break
        frozen, interrupted, mutable = [], [], []
        virtual_starts = []
        for stop in stops:
            if stop.departure_s <= event_time:
                frozen.append(stop)
            elif stop.arrival_s <= event_time:
                interrupted.append(stop)
                for task_id in stop.task_ids:
                    virtual_starts.append(VirtualStart(task_id=task_id,
                        location=AtNodeLocation(kind="at_node", node_id=stop.node_id),
                        start_s=event_time))
            else:
                mutable.append(stop)
            if set(stop.task_ids) & affected_tasks:
                mutable.append(stop)
        frozen_ids = {task_id for stop in frozen for task_id in stop.task_ids}
        interrupted_ids = {task_id for stop in interrupted for task_id in stop.task_ids}
        mutable_ids = ({task_id for stop in mutable for task_id in stop.task_ids}
                       | affected_tasks) - frozen_ids
        end = max((stop.departure_s for stop in stops if stop.departure_s > event_time),
                  default=event_time + 1)
        blocks = tuple(ResourceBlock(resource_id=resource_id, start_s=event_time,
                                     end_s=max(event_time + 1, end))
                       for resource_id in sorted(affected_resources, key=str))
        reasons = [ImpactReasonPath(code=f"event.{payload.kind}",
            entity_refs=(EntityRef(kind=reference.kind, id=reference.id,
                                   revision=reference.revision),),
            message="impact closure from the ingested event entity reference")]
        if affected_routes:
            reasons.append(ImpactReasonPath(code="closure.routes",
                entity_refs=tuple(EntityRef(kind=EntityKind.ROUTE, id=route_id, revision=None)
                                  for route_id in sorted(affected_routes, key=str)),
                message="routes reachable through affected stops"))
        if affected_resources:
            reasons.append(ImpactReasonPath(code="closure.vehicles",
                entity_refs=tuple(EntityRef(kind=EntityKind.VEHICLE, id=resource_id, revision=None)
                                  for resource_id in sorted(affected_resources, key=str)),
                message="vehicles/resources reachable through affected routes"))
        report = ImpactReport(event_ids=(uuid_for(envelope.source_event_id),),
            affected_orders=tuple(sorted(affected_orders, key=str)),
            affected_tasks=tuple(sorted(affected_tasks, key=str)),
            affected_resources=tuple(sorted(affected_resources, key=str)),
            reason_paths=tuple(reasons))
        boundary_body = {"event_time_s": event_time,
            "frozen": sorted(frozen_ids, key=str), "interrupted": sorted(interrupted_ids, key=str),
            "mutable": sorted(mutable_ids, key=str), "resources": sorted(affected_resources, key=str)}
        boundary = RescheduleBoundary(event_time_s=event_time,
            frozen_task_ids=tuple(sorted(frozen_ids, key=str)),
            interrupted_task_ids=tuple(sorted(interrupted_ids, key=str)),
            virtual_starts=tuple(virtual_starts), residual_loads=(),
            resource_blocks=blocks, mutable_task_ids=tuple(sorted(mutable_ids, key=str)),
            immutable_hash=content_hash(boundary_body))
        return ImpactAnalysisDTO(report=impact_report_dto(report),
                                 boundary=boundary_dto(boundary))


def uuid_for(source_event_id: str) -> UUID:
    """Stable event id when the envelope only carries a foreign string identity.

    In the normal API path the event has already been ingested and the caller can supply
    its UUID; this fallback keeps the pure analysis deterministic for pre-ingestion previews.
    """
    from uuid import UUID as _UUID

    try:
        return _UUID(source_event_id)
    except ValueError:
        from uuid import uuid5

        return uuid5(_UUID("00000000-0000-0000-0000-0000000000aa"), source_event_id)
