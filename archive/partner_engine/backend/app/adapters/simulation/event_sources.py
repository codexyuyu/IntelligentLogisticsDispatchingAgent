"""Deterministic event ordering for B-05 simulations."""
from __future__ import annotations

from app.contracts.events import DispatchEvent, SimulationRequest


def build_events(request: SimulationRequest) -> tuple[DispatchEvent, ...]:
    """Return simulation events in deterministic simulation-time order.

    Ties are broken by event_id so a fixed random_seed and identical request
    always produce the same event order.
    """
    return tuple(sorted(request.events, key=lambda e: (e.occurred_at_s, e.event_id)))
