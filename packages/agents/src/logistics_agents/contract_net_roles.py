"""R08 concrete roles: the warehouse, transport and exception bidders.

Companion to ``contract_net.py`` (the coordinator/protocol half). Each role
receives only bounded facts — one operation's release/deadline/duration, one
resource calendar, one vehicle shift with handoff readiness, one disruption —
never a full snapshot, stock ledger or price list, so the four-role boundary
of the partner R08 delivery is preserved.

Semantics (ported from the partner implementation, unchanged):

* the warehouse role bids the earliest calendar slot that fits the operation;
* the transport role bids the window bounded by the vehicle shift, its earliest
  free instant and the warehouse handoff readiness;
* the exception role bids a recovery window only when a disruption was
  declared — otherwise it stays silent instead of inventing a free slot.

``build_negotiator`` composes the coordinator plus the three roles; everything
stays deterministic because the windows come from the shared-contract
``TimeWindowDTO`` clock and the coordinator is never given a wall clock.
"""
from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass, field

from logistics_contracts.entities import TimeWindowDTO

from .contract_net import (
    Award,
    Bid,
    BiddingRole,
    CallForProposals,
    ContractNet,
    NegotiationError,
    NegotiationPolicy,
)


@dataclass(frozen=True, slots=True)
class OperationFact:
    """Bounded warehouse facts for one schedulable operation."""

    operation_id: str
    release_at_s: int
    deadline_at_s: int
    duration_s: int

    def __post_init__(self):
        if self.duration_s < 1:
            raise NegotiationError('operation_duration_must_be_positive')
        if self.deadline_at_s < self.release_at_s:
            raise NegotiationError('operation_window_reversed')


@dataclass(frozen=True, slots=True)
class ResourceCalendar:
    """One warehouse resource's availability windows in the shared clock."""

    resource_id: str
    windows: tuple[TimeWindowDTO, ...] = ()


@dataclass(frozen=True, slots=True)
class VehicleAvailability:
    """One vehicle's shift bound and earliest free instant."""

    vehicle_id: str
    shift: TimeWindowDTO
    available_at_s: int = 0

    def __post_init__(self):
        if self.available_at_s < 0:
            raise NegotiationError('negative_available_at')


@dataclass(frozen=True, slots=True)
class HandoffFact:
    """Warehouse-to-transport handoff readiness for one warehouse."""

    warehouse_id: str
    ready_at_s: int


@dataclass
class WarehouseWindowRole:
    """Bids the earliest feasible operation slot inside one resource calendar.

    Only the operation duration, its release/deadline and the resource's
    availability windows are used; the role never sees stock levels or prices.
    """

    operations: tuple[OperationFact, ...]
    calendar: ResourceCalendar
    role: BiddingRole = field(default='warehouse', init=False)

    def bid(self, cfp: CallForProposals) -> Bid | None:
        task = cfp.task
        operation = next((item for item in self.operations
                          if item.operation_id == task.task_id), None)
        if operation is None:
            return None
        earliest = max(task.window_start_s, operation.release_at_s)
        latest = min(task.window_end_s, operation.deadline_at_s)
        duration = operation.duration_s
        for window in sorted(self.calendar.windows, key=lambda item: item.earliest_s):
            start = max(earliest, window.earliest_s)
            if start + duration <= min(latest, window.latest_s):
                return Bid(
                    bid_id=f'bid_{cfp.round_no}_{self.role}_{task.task_id}',
                    cfp_id=cfp.cfp_id, task_id=task.task_id, round_no=cfp.round_no,
                    role=self.role, valid_from_s=start, valid_to_s=start + duration,
                    expires_at_s=cfp.respond_by_s + 300, cost=duration,
                    exclusive_resource_ids=(self.calendar.resource_id,),
                    note='warehouse window from resource calendar',
                )
        return None

    def confirm(self, award: Award) -> bool:
        return True


@dataclass
class TransportWindowRole:
    """Bids the vehicle window that respects shift bounds and warehouse handoff."""

    vehicle: VehicleAvailability
    handoffs: tuple[HandoffFact, ...] = ()
    role: BiddingRole = field(default='transport', init=False)

    def bid(self, cfp: CallForProposals) -> Bid | None:
        task = cfp.task
        ready = max(
            (handoff.ready_at_s for handoff in self.handoffs
             if handoff.warehouse_id == task.warehouse_id),
            default=0,
        )
        start = max(task.window_start_s, self.vehicle.shift.earliest_s,
                    self.vehicle.available_at_s, ready)
        end = min(task.window_end_s, self.vehicle.shift.latest_s)
        if end <= start:
            return None
        return Bid(
            bid_id=f'bid_{cfp.round_no}_{self.role}_{task.task_id}',
            cfp_id=cfp.cfp_id, task_id=task.task_id, round_no=cfp.round_no,
            role=self.role, valid_from_s=start, valid_to_s=end,
            expires_at_s=cfp.respond_by_s + 300, cost=end - start,
            exclusive_resource_ids=(self.vehicle.vehicle_id,),
            note='transport window bounded by shift and handoff',
        )

    def confirm(self, award: Award) -> bool:
        return True


@dataclass
class ExceptionRecoveryRole:
    """Bids a recovery window after a disruption; refuses when recovery overruns.

    ``disruption_at_s is None`` means no disruption was declared, so the role has
    nothing to offer and returns no bid instead of inventing a free slot.
    """

    disruption_at_s: int | None
    recovery_s: int
    resource_id: str
    role: BiddingRole = field(default='exception', init=False)

    def bid(self, cfp: CallForProposals) -> Bid | None:
        if self.disruption_at_s is None:
            return None
        task = cfp.task
        start = max(task.window_start_s, self.disruption_at_s)
        end = start + self.recovery_s
        if end > task.window_end_s:
            return None
        return Bid(
            bid_id=f'bid_{cfp.round_no}_{self.role}_{task.task_id}',
            cfp_id=cfp.cfp_id, task_id=task.task_id, round_no=cfp.round_no,
            role=self.role, valid_from_s=start, valid_to_s=end,
            expires_at_s=cfp.respond_by_s + 300, cost=self.recovery_s,
            exclusive_resource_ids=(self.resource_id,),
            note='recovery window after disruption',
        )

    def confirm(self, award: Award) -> bool:
        return True


def build_negotiator(*, calendar: ResourceCalendar, vehicle: VehicleAvailability,
                     operations: Iterable[OperationFact] = (),
                     handoffs: Iterable[HandoffFact] = (),
                     disruption_at_s: int | None = None, recovery_s: int = 0,
                     policy: NegotiationPolicy | None = None) -> ContractNet:
    """Compose the R08 four-role contract net from bounded facts.

    The warehouse role answers for ``calendar`` operations, the transport role
    for the one ``vehicle``; without a declared disruption the exception role
    has nothing to offer and stays silent, so it never wins by default.
    """
    return ContractNet([
        WarehouseWindowRole(tuple(operations), calendar),
        TransportWindowRole(vehicle, handoffs=tuple(handoffs)),
        ExceptionRecoveryRole(disruption_at_s=disruption_at_s,
                              recovery_s=max(1, recovery_s),
                              resource_id=calendar.resource_id),
    ], policy)


__all__ = [
    'ExceptionRecoveryRole',
    'HandoffFact',
    'OperationFact',
    'ResourceCalendar',
    'TransportWindowRole',
    'VehicleAvailability',
    'WarehouseWindowRole',
    'build_negotiator',
]
