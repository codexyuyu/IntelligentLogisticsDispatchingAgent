"""Shared window selection and confirmation rules for all role adapters."""
from itertools import pairwise

from logistics_agents.contract_net import Award, Bid, NegotiationError
from logistics_domain.primitives import ResourceCalendar


def require_nonnegative(value: int, name: str) -> None:
    if type(value) is not int or value < 0:
        raise NegotiationError(f'invalid_{name}')


def find_slot(calendars: tuple[tuple[ResourceCalendar, int], ...], start: int,
          end: int, duration: int) -> tuple[int, int] | None:
    """Intersect piecewise capacity calendars; gaps and zero capacity stay closed."""
    if not calendars or duration <= 0 or start + duration > end:
        return None
    boundaries = sorted({start, end} | {
        point for calendar, _ in calendars for interval in calendar.intervals
        for point in (interval.start_s, interval.end_s) if start < point < end})
    run = None
    for left, right in pairwise(boundaries):
        if all(calendar.available_units_at(left) >= units for calendar, units in calendars):
            run = left if run is None else run
            if run + duration <= right:
                return run, run + duration
        else:
            run = None
    return None


class WindowRole:
    """Confirmation must refer to an actual, unexpired offer made by this role."""

    def __init__(self):
        self._offers: dict[str, Bid] = {}

    def _offer(self, cfp, start, end, resources, note):
        bid = Bid(bid_id=f'bid_{cfp.round_no}_{self.role}_{cfp.task.task_id}',
                  cfp_id=cfp.cfp_id, task_id=cfp.task.task_id, round_no=cfp.round_no,
                  role=self.role, valid_from_s=start, valid_to_s=end,
                  expires_at_s=cfp.respond_by_s + 300, cost=end - start,
                  exclusive_resource_ids=tuple(sorted(resources)), note=note)
        self._offers[bid.bid_id] = bid
        return bid

    def confirm(self, award: Award) -> bool:
        bid = self._offers.get(award.bid_id)
        return bool(bid and (award.task_id, award.role, award.round_no) ==
                    (bid.task_id, bid.role, bid.round_no)
                    and not bid.is_expired(award.awarded_at_s))
