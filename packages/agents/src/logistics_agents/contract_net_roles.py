"""Compatibility fact adapters over the shared role window/confirmation engine.

New integrations use negotiation_roles and immutable domain evidence. These small
adapters preserve the original bounded-fact constructors, not a second protocol.
"""
from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass, field, replace

from logistics_agents.negotiation_roles import ExceptionRecoveryRole as RecoveryRole
from logistics_agents.negotiation_roles import RecoveryDeclaration
from logistics_agents.windows import WindowRole, find_slot
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


@dataclass(frozen=True)
class _Interval:
    start_s: int
    end_s: int


class _Calendar:
    def __init__(self, windows):
        self.intervals = tuple(_Interval(w.earliest_s, w.latest_s) for w in windows)

    def available_units_at(self, time_s):
        return int(any(i.start_s <= time_s < i.end_s for i in self.intervals))


@dataclass
class WarehouseWindowRole(WindowRole):
    """Bids the earliest feasible operation slot inside one resource calendar.

    Only the operation duration, its release/deadline and the resource's
    availability windows are used; the role never sees stock levels or prices.
    """

    operations: tuple[OperationFact, ...]
    calendar: ResourceCalendar
    role: BiddingRole = field(default='warehouse', init=False)

    def __post_init__(self):
        super().__init__()

    def bid(self, cfp: CallForProposals) -> Bid | None:
        task = cfp.task
        operation = next((item for item in self.operations
                          if item.operation_id == task.task_id), None)
        if operation is None:
            return None
        earliest = max(task.window_start_s, operation.release_at_s)
        latest = min(task.window_end_s, operation.deadline_at_s)
        duration = operation.duration_s
        slot = find_slot(((_Calendar(self.calendar.windows), 1),),
                     max(earliest, cfp.issued_at_s), latest, duration)
        if slot is None:
            return None
        return self._offer(cfp, *slot, (self.calendar.resource_id,),
                           'warehouse window from resource calendar')


@dataclass
class TransportWindowRole(WindowRole):
    """Bids the vehicle window that respects shift bounds and warehouse handoff."""

    vehicle: VehicleAvailability
    handoffs: tuple[HandoffFact, ...] = ()
    role: BiddingRole = field(default='transport', init=False)

    def __post_init__(self):
        super().__init__()

    def bid(self, cfp: CallForProposals) -> Bid | None:
        task = cfp.task
        ready = max(
            (handoff.ready_at_s for handoff in self.handoffs
             if handoff.warehouse_id == task.warehouse_id),
            default=0,
        )
        start = max(task.window_start_s, cfp.issued_at_s, self.vehicle.shift.earliest_s,
                    self.vehicle.available_at_s, ready)
        end = min(task.window_end_s, self.vehicle.shift.latest_s)
        if end <= start:
            return None
        return self._offer(cfp, start, end, (self.vehicle.vehicle_id,),
                           'transport window bounded by shift and handoff')


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

    def __post_init__(self):
        self._delegate = RecoveryRole()

    def bid(self, cfp: CallForProposals) -> Bid | None:
        declaration = RecoveryDeclaration(cfp.task.task_id, self.resource_id,
                                          self.disruption_at_s, self.recovery_s)
        self._delegate.declarations[cfp.task.task_id] = declaration
        # Legacy facts name their resource outside TaskSpec; project it explicitly.
        task = replace(cfp.task, exclusive_resource_ids=(self.resource_id,))
        return self._delegate.bid(replace(cfp, task=task))

    def confirm(self, award: Award) -> bool:
        return self._delegate.confirm(award)


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
