"""Shared server/deadline bounds for deterministic solver jobs."""
from datetime import UTC, datetime

from logistics_domain.errors import InvalidInputError
from logistics_domain.planning import SolveBudget


def solver_budget(deadline, requested=None, *, server_limit_ms=5000):
    expires_at = min(deadline.expires_at_utc, requested.deadline_utc if requested else deadline.expires_at_utc)
    expires_at = expires_at.replace(microsecond=0)
    remaining = int((expires_at - datetime.now(UTC)).total_seconds() * 1000)
    if remaining <= 0:
        raise InvalidInputError("job deadline has expired")
    return SolveBudget(
        wall_time_ms=min(remaining, server_limit_ms, requested.wall_time_ms if requested else server_limit_ms),
        deadline_utc=expires_at, max_candidates=1,
        seed=requested.seed if requested else 0, worker_count=1,
        deterministic_test_mode=False,
    )
