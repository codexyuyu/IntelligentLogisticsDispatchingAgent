"""Deterministic impact closure and reschedule boundary (P14 subset).

This is a pure read model over an already validated transport plan and its stop rows. It
never mutates the plan, never invents a new candidate and never writes a schedule.
"""

from __future__ import annotations

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
        affected_orders: set[UUID] = set()
        affected_tasks: set[UUID] = set()
        affected_resources: set[UUID] = set()
        if reference.kind == EntityKind.ORDER:
            affected_orders.add(reference.id)
            for stop in stops:
                if reference.id in stop.task_ids:
                    affected_tasks.update(stop.task_ids)
                    route = next((route for route in plan.routes if route.id == stop.route_id), None)
                    if route is not None:
                        affected_resources.add(route.vehicle_id)
        elif reference.kind == EntityKind.VEHICLE:
            affected_resources.add(reference.id)
            route = routes_by_vehicle.get(reference.id)
            if route is not None:
                for stop in stops:
                    if stop.route_id == route.id:
                        affected_tasks.update(stop.task_ids)
        else:
            affected_resources.add(reference.id)
            for stop in stops:
                affected_tasks.update(stop.task_ids)
        frozen, interrupted, mutable = [], [], []
        virtual_starts = []
        for stop in stops:
            task_id = stop.task_ids[0]
            if stop.departure_s <= event_time:
                frozen.append(stop)
            elif stop.arrival_s <= event_time:
                interrupted.append(stop)
                virtual_starts.append(VirtualStart(task_id=task_id,
                    location=AtNodeLocation(kind="at_node", node_id=stop.node_id),
                    start_s=event_time))
            else:
                mutable.append(stop)
            if task_id in affected_tasks:
                mutable.append(stop)
        frozen_ids = {stop.task_ids[0] for stop in frozen}
        interrupted_ids = {stop.task_ids[0] for stop in interrupted}
        mutable_ids = ({stop.task_ids[0] for stop in mutable} | affected_tasks) - frozen_ids
        end = max((stop.departure_s for stop in stops if stop.departure_s > event_time),
                  default=event_time + 1)
        blocks = tuple(ResourceBlock(resource_id=resource_id, start_s=event_time,
                                     end_s=max(event_time + 1, end))
                       for resource_id in sorted(affected_resources, key=str))
        reasons = (ImpactReasonPath(code=f"event.{payload.kind}",
            entity_refs=(EntityRef(kind=reference.kind, id=reference.id,
                                   revision=reference.revision),),
            message="impact closure from the ingested event entity reference"),)
        report = ImpactReport(event_ids=(uuid_for(envelope.source_event_id),),
            affected_orders=tuple(sorted(affected_orders, key=str)),
            affected_tasks=tuple(sorted(affected_tasks, key=str)),
            affected_resources=tuple(sorted(affected_resources, key=str)),
            reason_paths=reasons)
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
