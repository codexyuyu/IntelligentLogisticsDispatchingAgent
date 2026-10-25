"""State projection helpers for B-05."""
from __future__ import annotations

from app.contracts.entities import PlanningSnapshot


def project_state(snapshot: PlanningSnapshot, simulation_time_s: int) -> PlanningSnapshot:
    """Advance only the simulation clock; operational facts remain immutable.

    B-04 is responsible for deriving operational state after an event. The
    projection deliberately does not reset vehicle load or freshness data.
    """
    return snapshot.model_copy(update={"simulation_time_s": simulation_time_s})
