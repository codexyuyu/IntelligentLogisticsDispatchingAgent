"""R08 over a solved plan: tasks and roles bound to real solver output.

Owner: PARTNER (乙方). Demo/link layer only — it does not change planning, the
contracts, or any DSH file. Everything it negotiates about is taken from a plan
that CP-SAT and OR-Tools actually produced:

* the task id is the loading operation the warehouse scheduler placed,
* the task window comes from that operation's release/deadline,
* the warehouse role is bound to the resource CP-SAT assigned,
* the transport role is bound to the vehicle that actually carries the order and
  to the handoff time the warehouse schedule produced.
"""
from __future__ import annotations

from dataclasses import dataclass

from app.application.contract_net import (
    NegotiationPolicy,
    NegotiationResult,
    TaskSpec,
    format_transcript,
)
from app.bootstrap import build_negotiator
from app.contracts.planning import CandidatePlan, PlanningSnapshot


@dataclass(frozen=True)
class NegotiationOutcome:
    order_id: str
    operation_id: str
    vehicle_id: str
    resource_id: str
    result: NegotiationResult

    @property
    def awarded_role(self) -> str | None:
        return self.result.awards[0].role if self.result.awards else None

    def transcript_lines(self) -> tuple[str, ...]:
        return format_transcript(self.result)


def _loading_operation(snapshot: PlanningSnapshot, order_id: str):
    candidates = [op for op in snapshot.operations
                  if order_id in op.order_ids and 'load' in op.operation_kind]
    return sorted(candidates, key=lambda op: op.operation_id)[0] if candidates else None


def _carrying_vehicle(plan: CandidatePlan, order_id: str) -> str | None:
    for route in plan.routing.routes:
        for stop in route.stops:
            if order_id in stop.order_ids:
                return route.vehicle_id
    return None


def tasks_from_plan(plan: CandidatePlan, snapshot: PlanningSnapshot) -> tuple[TaskSpec, ...]:
    """One task per delivered order, keyed by its scheduled loading operation."""
    delivered = {order_id for route in plan.routing.routes
                 for stop in route.stops if stop.stop_kind == 'delivery'
                 for order_id in stop.order_ids}
    warehouses = {order.order_id: order.warehouse_id for order in snapshot.orders}
    tasks = []
    for order_id in sorted(delivered):
        operation = _loading_operation(snapshot, order_id)
        vehicle_id = _carrying_vehicle(plan, order_id)
        if operation is None or vehicle_id is None:
            continue
        tasks.append(TaskSpec(
            task_id=operation.operation_id,
            warehouse_id=warehouses.get(order_id, operation.warehouse_id),
            window_start_s=operation.release_at_s,
            window_end_s=operation.deadline_at_s,
            exclusive_resource_ids=(operation.resource_id, vehicle_id),
        ))
    return tuple(tasks)


def negotiate_plan(plan: CandidatePlan, snapshot: PlanningSnapshot, *, now_s: int = 0,
                   policy: NegotiationPolicy | None = None) -> tuple[NegotiationOutcome, ...]:
    """Run the four-role protocol once per delivered order, on real plan facts."""
    vehicles = {vehicle.vehicle_id: vehicle for vehicle in snapshot.vehicles}
    operations = {operation.operation_id: operation for operation in snapshot.operations}
    orders = {order.order_id: order for order in snapshot.orders}
    handoffs = {handoff.order_id: handoff for handoff in plan.warehouse.warehouse_handoffs}

    outcomes = []
    for task in tasks_from_plan(plan, snapshot):
        operation = operations[task.task_id]
        vehicle_id = next((rid for rid in task.exclusive_resource_ids if rid in vehicles), None)
        order_id = next((order_id for order_id, order in orders.items()
                         if order_id in operation.order_ids), None)
        if vehicle_id is None or order_id is None:
            continue
        handoff = handoffs.get(order_id)
        negotiator = build_negotiator(
            snapshot, policy=policy, warehouse_resource_id=operation.resource_id,
            vehicle_id=vehicle_id, handoffs=(handoff,) if handoff is not None else (),
        )
        result = negotiator.negotiate([task], now_s=now_s)
        outcomes.append(NegotiationOutcome(
            order_id=order_id, operation_id=task.task_id, vehicle_id=vehicle_id,
            resource_id=operation.resource_id, result=result,
        ))
    return tuple(outcomes)

