"""Shared candidate projection for standalone and joint scheduling.

Validation and persistence remain caller responsibilities. Task identities are derived
from the candidate, while the complete candidate body has one canonical hash definition.
"""
from uuid import uuid4, uuid5

from logistics_domain.errors import InvalidInputError
from logistics_domain.planning import (
    CandidatePlan,
    CostBreakdown,
    ObjectiveBreakdown,
    ScheduleTask,
    TaskKind,
    WarehousePlan,
    content_hash,
)
from logistics_domain.states import EntityState


def build_candidate(*, schedule_id, snapshot, plan, stops, actor_id, now,
                    warehouse_solution=None, base_version_id=None, solver_evidence_refs=(),
                    candidate_id=None):
    candidate_id = candidate_id or uuid4()
    routes = {route.id: route for route in plan.routes}
    tasks, transport_tasks = [], {}
    for stop in stops:
        route = routes.get(stop.route_id)
        if route is None:
            raise InvalidInputError("stop route is not in the plan")
        for task_id in stop.task_ids:
            transport_tasks.setdefault(task_id, []).append((stop, route))
    for task_id, values in transport_tasks.items():
        tasks.append(ScheduleTask(
            id=uuid5(candidate_id, str(task_id)), status=EntityState.PLANNED,
            created_at=now, updated_at=now, row_version=0, schema_version="2.0.0",
            created_by=actor_id, version_id=candidate_id, task_id=task_id,
            task_kind=TaskKind.TRANSPORT,
            assigned_resource_ids=tuple(sorted({r.vehicle_id for _, r in values}, key=str)),
            planned_start_s=min(s.service_start_s for s, _ in values),
            planned_end_s=max(max(s.departure_s, s.service_start_s + 1) for s, _ in values),
            sequence=min(s.sequence for s, _ in values)))
    zero_cost = CostBreakdown(0, 0, 0, 0, 0, 0)
    warehouse_plan = WarehousePlan((), (), (), zero_cost)
    if warehouse_solution is not None:
        business = warehouse_solution.objective.business_cost_cents if warehouse_solution.objective else 0
        warehouse_plan = WarehousePlan(warehouse_solution.assignments,
            warehouse_solution.storage_allocations, warehouse_solution.setup_operations,
            CostBreakdown(0, 0, business, 0, 0, business))
        grouped = {}
        for assignment in warehouse_solution.assignments:
            grouped.setdefault(assignment.task_id, []).append(assignment)
        for task_id, values in grouped.items():
            if task_id in transport_tasks:
                raise InvalidInputError("warehouse task id collides with a transport task")
            tasks.append(ScheduleTask(
                id=uuid5(candidate_id, str(task_id)), status=EntityState.PLANNED,
                created_at=now, updated_at=now, row_version=0, schema_version="2.0.0",
                created_by=actor_id, version_id=candidate_id, task_id=task_id,
                task_kind=TaskKind.WAREHOUSE,
                assigned_resource_ids=tuple(sorted({a.resource_id for a in values}, key=str)),
                planned_start_s=min(a.start_s for a in values),
                planned_end_s=max(a.end_s for a in values), sequence=None))
    total = plan.cost.total_cents + warehouse_plan.cost.total_cents
    body = dict(schedule_id=schedule_id, snapshot_id=snapshot.id, snapshot_hash=snapshot.hash,
                epoch_utc=snapshot.scope.epoch_utc, horizon_s=snapshot.scope.horizon_s,
                transport_plan=plan, warehouse_plan=warehouse_plan,
                task_assignments=tuple(sorted(tasks, key=lambda t: (t.task_kind.value, str(t.task_id)))),
                objective=ObjectiveBreakdown(total, 0, 0, 0, 0, total),
                solver_evidence_refs=tuple(solver_evidence_refs))
    return CandidatePlan(id=candidate_id, base_version_id=base_version_id,
                         content_hash=content_hash(body), **body)
