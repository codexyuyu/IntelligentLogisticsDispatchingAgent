"""R08 window roles adapted to the current immutable domain contracts.

Offers are suggestions, never stock reservations or changes to a solved plan.
Only the coordinator's public TaskSpec and bounded windows enter the transcript.
"""
from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from logistics_agents.contract_net import Bid, CallForProposals, NegotiationError
from logistics_agents.windows import WindowRole, find_slot, require_nonnegative
from logistics_domain.planning import OperationAssignment, PlanningSnapshot, WarehouseTask
from logistics_domain.primitives import TimeWindow
from logistics_domain.resources import Vehicle


class WarehouseWindowRole(WindowRole):
    """Earliest joint calendar slot on exactly the resources assigned by the solver."""

    role = 'warehouse'

    def __init__(self, snapshot: PlanningSnapshot, tasks: tuple[WarehouseTask, ...],
                 assignments: tuple[OperationAssignment, ...]):
        super().__init__()
        self.snapshot = snapshot
        self.tasks = {str(task.id): task for task in tasks}
        self.assignments = assignments

    def bid(self, cfp: CallForProposals) -> Bid | None:
        task = self.tasks.get(cfp.task.task_id)
        if task is None or str(task.warehouse_id) != cfp.task.warehouse_id:
            return None
        assigned = tuple(a for a in self.assignments if a.task_id == task.id)
        if len(assigned) != len(task.requirements) or task.duration_s <= 0:
            return None
        bundle = self.snapshot.resources
        resources = {item.id: item for item in (*bundle.docks, *bundle.workers, *bundle.equipment)}
        warehouse = next((w for w in bundle.warehouses if w.id == task.warehouse_id), None)
        if warehouse is None:
            return None
        calendars = [(warehouse.calendar, 1)]
        matched = set()
        for assignment in assigned:
            resource = resources.get(assignment.resource_id)
            if (resource is None or resource.warehouse_id != task.warehouse_id
                    or str(resource.id) not in cfp.task.exclusive_resource_ids):
                return None
            matches = [i for i, req in enumerate(task.requirements)
                       if assignment.resource_id in req.eligible_ids and assignment.units == req.units]
            if len(matches) != 1 or matches[0] in matched:
                return None
            matched.add(matches[0])
            calendars.append((resource.calendar, assignment.units))
        if any(c.epoch_utc != self.snapshot.scope.epoch_utc for c, _ in calendars):
            return None
        predecessor_ends = []
        for predecessor in task.predecessor_ids:
            ends = [a.end_s for a in self.assignments if a.task_id == predecessor]
            if not ends:
                return None
            predecessor_ends.append(max(ends))
        start = max(cfp.task.window_start_s, task.window.earliest_s, cfp.issued_at_s,
                    *predecessor_ends)
        end = min(cfp.task.window_end_s, task.window.latest_s, self.snapshot.scope.horizon_s)
        slot = find_slot(tuple(calendars), start, end, task.duration_s)
        if slot is None:
            return None
        return self._offer(cfp, *slot, (str(a.resource_id) for a in assigned),
                           'warehouse window from assigned resource calendars')


@dataclass(frozen=True)
class TransportBinding:
    task_id: str
    warehouse_id: str
    vehicle_id: UUID
    shift: TimeWindow
    available_at_s: int
    handoff_ready_at_s: int
    duration_s: int

    def __post_init__(self):
        for name in ('available_at_s', 'handoff_ready_at_s', 'duration_s'):
            require_nonnegative(getattr(self, name), name)
        if self.duration_s == 0:
            raise NegotiationError('empty_transport_duration')


class TransportWindowRole(WindowRole):
    """Vehicle calendar ∩ declared shift, released by availability AND task handoff."""

    role = 'transport'

    def __init__(self, vehicles: tuple[Vehicle, ...], bindings: tuple[TransportBinding, ...]):
        super().__init__()
        self.vehicles = {v.id: v for v in vehicles}
        self.bindings = {b.task_id: b for b in bindings}
        if len(self.bindings) != len(bindings):
            raise NegotiationError('duplicate_transport_binding')

    def bid(self, cfp: CallForProposals) -> Bid | None:
        binding = self.bindings.get(cfp.task.task_id)
        if binding is None or binding.warehouse_id != cfp.task.warehouse_id:
            return None
        vehicle = self.vehicles.get(binding.vehicle_id)
        if vehicle is None or str(vehicle.id) not in cfp.task.exclusive_resource_ids:
            return None
        start = max(cfp.task.window_start_s, cfp.issued_at_s, binding.shift.earliest_s,
                    binding.available_at_s, binding.handoff_ready_at_s)
        end = min(cfp.task.window_end_s, binding.shift.latest_s)
        slot = find_slot(((vehicle.calendar, 1),), start, end, binding.duration_s)
        if slot is None:
            return None
        return self._offer(cfp, *slot, (str(vehicle.id),), 'vehicle shift, availability and task handoff')


@dataclass(frozen=True)
class RecoveryDeclaration:
    task_id: str
    resource_id: str
    disruption_at_s: int | None
    recovery_s: int

    def __post_init__(self):
        if self.disruption_at_s is not None:
            require_nonnegative(self.disruption_at_s, 'disruption_at_s')
        require_nonnegative(self.recovery_s, 'recovery_s')
        if self.recovery_s == 0:
            raise NegotiationError('empty_recovery_duration')


class ExceptionRecoveryRole(WindowRole):
    """A declared recovery applies only to its named task and bound resource."""

    role = 'exception'

    def __init__(self, declarations: tuple[RecoveryDeclaration, ...] = ()):
        super().__init__()
        self.declarations = {d.task_id: d for d in declarations}
        if len(self.declarations) != len(declarations):
            raise NegotiationError('duplicate_recovery_declaration')

    def bid(self, cfp: CallForProposals) -> Bid | None:
        declaration = self.declarations.get(cfp.task.task_id)
        if (declaration is None or declaration.disruption_at_s is None
                or declaration.resource_id not in cfp.task.exclusive_resource_ids):
            return None
        start = max(cfp.task.window_start_s, cfp.issued_at_s, declaration.disruption_at_s)
        end = start + declaration.recovery_s
        if end > cfp.task.window_end_s:
            return None
        return self._offer(cfp, start, end, (declaration.resource_id,), 'declared task recovery')
