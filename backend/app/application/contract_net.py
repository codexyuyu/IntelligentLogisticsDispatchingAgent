"""R08 four-role contract-net negotiation.

Owner: PARTNER (乙方). Scope: ``backend/app/application/contract_net.py`` and
``backend/tests/negotiation/``.

The four bounded roles are the coordinator (this module) plus the warehouse,
transport and exception roles, which only exchange availability windows and
constraint summaries — never a full snapshot, stock ledger or price list.

Protocol (one round):

1. the coordinator issues a call for proposals per pending task, with a response
   deadline and bounded public task facts;
2. each role answers with zero or one bid carrying a feasible window, an integer
   cost in that role's own unit and an expiry instant;
3. the coordinator rejects bids that are expired, incomplete, or wider than the
   task window, de-duplicates per role, then builds a conflict-free award set by
   ranking (cost, window start, role order, task id);
4. conflicting bids are recorded and notified to the losing role;
5. each winner must confirm; a refusal revokes the award and retries next round;
6. rounds stop on confirmation of every task, on reaching ``max_rounds``, or on
   exceeding ``deadline_s`` (simulated clock, no wall clock is read).

Everything is deterministic: the caller passes ``now_s``, ranking is total and
the transcript is append-only with a monotonic sequence and a SHA-256 digest.
"""
from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from typing import Iterable, Literal, Protocol, Sequence

from app.contracts.entities import Operation, PlanningSnapshot, Vehicle
from app.contracts.planning import WarehouseHandoff

BiddingRole = Literal['warehouse', 'transport', 'exception']
Actor = Literal['warehouse', 'transport', 'exception', 'coordinator']
MessageKind = Literal[
    'cfp', 'bid', 'conflict', 'award', 'confirm', 'revoke', 'close',
]
NegotiationStatus = Literal[
    'confirmed', 'partial', 'infeasible', 'exhausted', 'expired', 'revoked',
    'already_awarded',
]

ROLE_ORDER: tuple[BiddingRole, ...] = ('warehouse', 'transport', 'exception')


class NegotiationError(ValueError):
    """Invalid negotiation input; the message is a stable reason code."""


@dataclass(frozen=True)
class NegotiationPolicy:
    max_rounds: int = 3
    respond_timeout_s: int = 60
    deadline_s: int = 600
    require_confirmation: bool = True
    rank_by: Literal['cost', 'earliest', 'role'] = 'cost'

    def __post_init__(self):
        if self.max_rounds < 1:
            raise NegotiationError('max_rounds_must_be_positive')
        if self.respond_timeout_s < 1:
            raise NegotiationError('respond_timeout_must_be_positive')
        if self.deadline_s < self.respond_timeout_s:
            raise NegotiationError('deadline_shorter_than_response_timeout')


@dataclass(frozen=True)
class TaskSpec:
    """Bounded public facts the coordinator may share with every role."""

    task_id: str
    warehouse_id: str
    window_start_s: int
    window_end_s: int
    quantity_units: int = 1
    required_resource_kind: str | None = None
    exclusive_resource_ids: tuple[str, ...] = ()

    def __post_init__(self):
        if self.window_end_s < self.window_start_s:
            raise NegotiationError('task_window_reversed')


@dataclass(frozen=True)
class CallForProposals:
    cfp_id: str
    round_no: int
    issued_at_s: int
    respond_by_s: int
    task: TaskSpec


@dataclass(frozen=True)
class Bid:
    bid_id: str
    cfp_id: str
    task_id: str
    round_no: int
    role: BiddingRole
    valid_from_s: int
    valid_to_s: int
    expires_at_s: int
    cost: int
    exclusive_resource_ids: tuple[str, ...] = ()
    note: str = ''

    def inside(self, task: TaskSpec) -> bool:
        """The offered slot must sit inside the requested service window."""
        return (self.valid_from_s >= task.window_start_s
                and self.valid_to_s <= task.window_end_s)

    def is_expired(self, now_s: int) -> bool:
        return self.expires_at_s < now_s

    def overlaps(self, other: 'Bid') -> bool:
        if not set(self.exclusive_resource_ids) & set(other.exclusive_resource_ids):
            return False
        return self.valid_from_s < other.valid_to_s and other.valid_from_s < self.valid_to_s


@dataclass(frozen=True)
class Award:
    award_id: str
    task_id: str
    bid_id: str
    role: BiddingRole
    round_no: int
    awarded_at_s: int


@dataclass(frozen=True)
class Conflict:
    round_no: int
    task_id: str
    rejected_bid_id: str
    rejected_role: BiddingRole
    blocking_bid_id: str
    blocking_role: BiddingRole
    resource_ids: tuple[str, ...]


@dataclass(frozen=True)
class Message:
    seq: int
    round_no: int
    at_s: int
    kind: MessageKind
    role: Actor
    task_id: str
    bid_id: str | None
    detail: str


@dataclass(frozen=True)
class NegotiationResult:
    status: NegotiationStatus
    rounds_used: int
    awards: tuple[Award, ...]
    conflicts: tuple[Conflict, ...]
    task_outcomes: tuple[tuple[str, str], ...]
    reason: str
    transcript: tuple[Message, ...]
    digest: str

    def outcome_of(self, task_id: str) -> str | None:
        return dict(self.task_outcomes).get(task_id)


class Role(Protocol):
    """Bounded role: answers a call for proposals with at most one bid."""

    role: BiddingRole

    def bid(self, cfp: CallForProposals) -> Bid | None: ...

    def confirm(self, award: Award) -> bool: ...


def _digest(transcript: Sequence[Message]) -> str:
    payload = '\n'.join(
        f'{m.seq}|{m.round_no}|{m.at_s}|{m.kind}|{m.role}|{m.task_id}|{m.bid_id or ""}|{m.detail}'
        for m in transcript
    )
    return hashlib.sha256(payload.encode('utf-8')).hexdigest()


class ContractNet:
    """Coordinator side of the four-role contract net."""

    def __init__(self, roles: Iterable[Role], policy: NegotiationPolicy | None = None):
        self._policy = policy or NegotiationPolicy()
        self._roles: dict[BiddingRole, Role] = {}
        for role in roles:
            if role.role in self._roles:
                raise NegotiationError(f'duplicate_role:{role.role}')
            if role.role not in ROLE_ORDER:
                raise NegotiationError(f'unknown_role:{role.role}')
            self._roles[role.role] = role
        missing = [name for name in ROLE_ORDER if name not in self._roles]
        if missing:
            raise NegotiationError('missing_roles:' + ','.join(missing))
        self._seq = 0
        self._transcript: list[Message] = []
        self._results: dict[str, NegotiationResult] = {}
        self._awards: dict[str, Award] = {}

    # -- public API --------------------------------------------------------

    def negotiate(self, tasks: Sequence[TaskSpec], now_s: int,
                  idempotency_key: str | None = None) -> NegotiationResult:
        tasks = tuple(tasks)
        if not tasks:
            raise NegotiationError('no_tasks')
        if len({task.task_id for task in tasks}) != len(tasks):
            raise NegotiationError('duplicate_task_ids')
        if now_s < 0:
            raise NegotiationError('negative_clock')

        key = idempotency_key or 'auto:' + ','.join(sorted(task.task_id for task in tasks))
        if key in self._results:
            # Replay is byte-identical: no new messages, no new awards.
            return self._results[key]
        already = [task.task_id for task in tasks if task.task_id in self._awards]
        if already:
            return self._remember(key, self._result(
                status='already_awarded', rounds_used=0, awards=(),
                conflicts=(), outcomes={task_id: 'already_awarded' for task_id in already},
                reason='task_already_awarded:' + ','.join(sorted(already)),
            ))

        return self._remember(key, self._run(tasks, now_s))

    def revoke(self, task_id: str, now_s: int, reason: str = 'operator_revoked') -> NegotiationResult:
        award = self._awards.pop(task_id, None)
        if award is None:
            return self._result(
                status='revoked', rounds_used=0, awards=(), conflicts=(),
                outcomes={task_id: 'not_awarded'}, reason='nothing_to_revoke',
            )
        self._emit(now_s, award.round_no, 'revoke', award.role, task_id, award.bid_id, reason)
        return self._result(
            status='revoked', rounds_used=award.round_no, awards=(award,), conflicts=(),
            outcomes={task_id: 'revoked'}, reason=reason,
        )

    def transcript(self) -> tuple[Message, ...]:
        return tuple(self._transcript)

    def award_of(self, task_id: str) -> Award | None:
        return self._awards.get(task_id)

    # -- internals ---------------------------------------------------------

    def _remember(self, key: str, result: NegotiationResult) -> NegotiationResult:
        self._results[key] = result
        return result

    def _emit(self, at_s: int, round_no: int, kind: MessageKind, role: Actor,
              task_id: str, bid_id: str | None, detail: str) -> Message:
        self._seq += 1
        message = Message(seq=self._seq, round_no=round_no, at_s=at_s, kind=kind,
                          role=role, task_id=task_id, bid_id=bid_id, detail=detail)
        self._transcript.append(message)
        return message

    def _run(self, tasks: tuple[TaskSpec, ...], now_s: int) -> NegotiationResult:
        policy = self._policy
        outcomes: dict[str, str] = {task.task_id: 'pending' for task in tasks}
        awards: list[Award] = []
        conflicts: list[Conflict] = []
        confirmed: dict[str, Award] = {}
        rounds_used = 0
        reason = 'rounds_exhausted'

        for round_no in range(1, policy.max_rounds + 1):
            round_start = now_s + (round_no - 1) * policy.respond_timeout_s
            respond_by = round_start + policy.respond_timeout_s
            if respond_by > now_s + policy.deadline_s:
                reason = 'deadline_exceeded'
                break
            rounds_used = round_no
            pending = [task for task in tasks if task.task_id not in confirmed]
            if not pending:
                break

            cfps: dict[str, CallForProposals] = {}
            for task in pending:
                cfp = CallForProposals(
                    cfp_id=f'cfp_{round_no}_{task.task_id}', round_no=round_no,
                    issued_at_s=round_start, respond_by_s=respond_by, task=task,
                )
                cfps[task.task_id] = cfp
                self._emit(round_start, round_no, 'cfp', 'coordinator', task.task_id, None,
                           f'respond_by={respond_by}')

            round_state: dict[str, str] = {task.task_id: 'no_bid' for task in pending}
            bids_by_task: dict[str, list[Bid]] = {task.task_id: [] for task in pending}
            responses = 0
            for task in pending:
                cfp = cfps[task.task_id]
                for name in ROLE_ORDER:
                    bid = self._roles[name].bid(cfp)
                    if bid is None:
                        continue
                    responses += 1
                    detail = self._reject_reason(bid, cfp, round_start)
                    self._emit(round_start, round_no, 'bid', name, task.task_id, bid.bid_id,
                               detail or f'cost={bid.cost};window=[{bid.valid_from_s},{bid.valid_to_s})')
                    if detail:
                        if round_state[task.task_id] == 'no_bid':
                            round_state[task.task_id] = 'bid_rejected'
                        continue
                    bids_by_task[task.task_id].append(bid)

            if not any(bids_by_task.values()):
                # Either nobody answered, or every answer was unusable; repeating
                # the identical call cannot change either outcome.
                reason = 'no_acceptable_bid' if responses else 'no_bids'
                break

            ranked = [bid for task in pending for bid in bids_by_task[task.task_id]]

            selected: list[Bid] = []
            for bid in sorted(ranked, key=self._rank):
                # A cheaper/earlier bid for a task that is already covered this
                # round is ordinary competition, not a resource conflict.
                if any(chosen.task_id == bid.task_id for chosen in selected):
                    continue
                blocking = next((chosen for chosen in selected if chosen.overlaps(bid)), None)
                if blocking is None:
                    selected.append(bid)
                    continue
                shared = tuple(sorted(set(blocking.exclusive_resource_ids)
                                      & set(bid.exclusive_resource_ids)))
                conflicts.append(Conflict(
                    round_no=round_no, task_id=bid.task_id, rejected_bid_id=bid.bid_id,
                    rejected_role=bid.role, blocking_bid_id=blocking.bid_id,
                    blocking_role=blocking.role, resource_ids=shared,
                ))
                self._emit(round_start, round_no, 'conflict', bid.role, bid.task_id,
                           bid.bid_id, f'blocked_by={blocking.bid_id}')
                if round_state[bid.task_id] in ('no_bid', 'bid_rejected'):
                    round_state[bid.task_id] = 'conflicted'

            for bid in selected:
                award = Award(award_id=f'award_{round_no}_{bid.bid_id}', task_id=bid.task_id,
                              bid_id=bid.bid_id, role=bid.role, round_no=round_no,
                              awarded_at_s=respond_by)
                self._emit(respond_by, round_no, 'award', 'coordinator', bid.task_id,
                           bid.bid_id, f'role={bid.role}')
                if not policy.require_confirmation:
                    self._awards[bid.task_id] = award
                    confirmed[bid.task_id] = award
                    awards.append(award)
                    continue
                if self._roles[bid.role].confirm(award):
                    self._awards[bid.task_id] = award
                    confirmed[bid.task_id] = award
                    awards.append(award)
                    self._emit(respond_by, round_no, 'confirm', bid.role, bid.task_id,
                               bid.bid_id, 'accepted')
                    continue
                self._emit(respond_by, round_no, 'revoke', bid.role, bid.task_id,
                           bid.bid_id, 'confirmation_refused')
                round_state[bid.task_id] = 'award_retracted'

            if len(confirmed) == len(tasks):
                reason = 'all_tasks_confirmed'
                break

        for task in tasks:
            outcomes[task.task_id] = ('confirmed' if task.task_id in confirmed
                                      else round_state.get(task.task_id, 'no_bid'))

        if len(confirmed) == len(tasks):
            status: NegotiationStatus = 'confirmed'
        elif confirmed:
            status = 'partial'
        elif reason == 'deadline_exceeded':
            status = 'expired'
        elif any(value == 'award_retracted' for value in outcomes.values()):
            status = 'exhausted'
            reason = 'confirmation_refused'
        elif all(value == 'no_bid' for value in outcomes.values()):
            status = 'infeasible'
            reason = 'no_bids'
        else:
            status = 'infeasible'
            reason = 'no_acceptable_bid'

        self._emit(now_s + rounds_used * policy.respond_timeout_s, rounds_used, 'close',
                   'coordinator', tasks[0].task_id if len(tasks) == 1 else '*',
                   None, f'status={status};reason={reason}')
        return self._result(status=status, rounds_used=rounds_used, awards=tuple(awards),
                            conflicts=tuple(conflicts), outcomes=outcomes, reason=reason)

    def _result(self, *, status: NegotiationStatus, rounds_used: int,
                awards: tuple[Award, ...], conflicts: tuple[Conflict, ...],
                outcomes: dict[str, str], reason: str) -> NegotiationResult:
        transcript = tuple(self._transcript)
        ordered = tuple(sorted(outcomes.items()))
        return NegotiationResult(
            status=status, rounds_used=rounds_used, awards=awards, conflicts=conflicts,
            task_outcomes=ordered, reason=reason, transcript=transcript,
            digest=_digest(transcript),
        )

    @staticmethod
    def _reject_reason(bid: Bid, cfp: CallForProposals, now_s: int) -> str:
        if bid.cfp_id != cfp.cfp_id:
            return 'stale_cfp'
        if bid.task_id != cfp.task.task_id:
            return 'task_mismatch'
        if bid.round_no != cfp.round_no:
            return 'stale_round'
        if bid.role not in ROLE_ORDER:
            return 'unknown_role'
        if bid.valid_to_s <= bid.valid_from_s:
            return 'empty_window'
        if bid.is_expired(now_s):
            return 'bid_expired'
        if bid.cost < 0:
            return 'negative_cost'
        if not bid.inside(cfp.task):
            return 'bid_outside_task_window'
        return ''


    def _rank(self, bid: Bid) -> tuple:
        policy = self._policy
        role_index = ROLE_ORDER.index(bid.role)
        if policy.rank_by == 'earliest':
            return (bid.valid_from_s, bid.cost, role_index, bid.task_id)
        if policy.rank_by == 'role':
            return (role_index, bid.cost, bid.valid_from_s, bid.task_id)
        return (bid.cost, bid.valid_from_s, role_index, bid.task_id)


# --------------------------------------------------------------------------- #
# Bounded roles built on the shared contracts
# --------------------------------------------------------------------------- #

@dataclass
class WarehouseWindowRole:
    """Bids the earliest feasible operation slot inside one resource calendar.

    Only the operation duration, its release/deadline and the resource's
    availability windows are used; the role never sees stock levels or prices.
    """

    snapshot: PlanningSnapshot
    resource_id: str
    role: BiddingRole = field(default='warehouse', init=False)

    def bid(self, cfp: CallForProposals) -> Bid | None:
        task = cfp.task
        operation = self._operation(task.task_id)
        resource = next((item for item in self.snapshot.resources
                         if item.resource_id == self.resource_id), None)
        if operation is None or resource is None:
            return None
        earliest = max(task.window_start_s, operation.release_at_s)
        latest = min(task.window_end_s, operation.deadline_at_s)
        duration = operation.duration_s
        for window in sorted(resource.available_windows, key=lambda item: item.start_s):
            start = max(earliest, window.start_s)
            if start + duration <= min(latest, window.end_s):
                return Bid(
                    bid_id=f'bid_{cfp.round_no}_{self.role}_{task.task_id}',
                    cfp_id=cfp.cfp_id, task_id=task.task_id, round_no=cfp.round_no,
                    role=self.role, valid_from_s=start, valid_to_s=start + duration,
                    expires_at_s=cfp.respond_by_s + 300, cost=duration,
                    exclusive_resource_ids=(self.resource_id,),
                    note='warehouse window from resource calendar',
                )
        return None

    def confirm(self, award: Award) -> bool:
        return True

    def _operation(self, operation_id: str) -> Operation | None:
        return next((item for item in self.snapshot.operations
                     if item.operation_id == operation_id), None)


@dataclass
class TransportWindowRole:
    """Bids the vehicle window that respects shift bounds and warehouse handoff."""

    vehicle: Vehicle
    handoffs: tuple[WarehouseHandoff, ...] = ()
    role: BiddingRole = field(default='transport', init=False)

    def bid(self, cfp: CallForProposals) -> Bid | None:
        task = cfp.task
        ready = max(
            (handoff.ready_at_s for handoff in self.handoffs
             if handoff.warehouse_id == task.warehouse_id),
            default=0,
        )
        start = max(task.window_start_s, self.vehicle.shift_window.start_s,
                    self.vehicle.available_at_s, ready)
        end = min(task.window_end_s, self.vehicle.shift_window.end_s)
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
    """Bids a recovery window after a disruption; refuses when recovery overruns."""

    disruption_at_s: int
    recovery_s: int
    resource_id: str
    role: BiddingRole = field(default='exception', init=False)

    def bid(self, cfp: CallForProposals) -> Bid | None:
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





