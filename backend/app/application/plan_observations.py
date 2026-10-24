"""R09 business observations for the evaluation layer (facts only, no metrics).

Owner: PARTNER (乙方). This module answers "what actually happened in this plan"
— coverage, handoff waits, cold-chain peaks and exposure, negotiation outcome —
so the DSH-owned ``backend/app/evaluation/`` can compute the 14 metrics on real
observations instead of on assumptions.

Deliberate boundaries:

* no metric formulas here (ratios, averages, comparisons stay in ``evaluation``);
* no independent validation here — R05 rules remain the validator's job and the
  planned DSH domain rebuild;
* absent evidence is reported as absent (``coldchain_evidence=False``), never as
  zero-valued measurements.
"""
from __future__ import annotations

from dataclasses import dataclass

from app.application.contract_net import NegotiationResult
from app.contracts.planning import CandidatePlan

__all__ = [
    'CapacityPeak',
    'ExposureTotal',
    'PlanObservations',
    'observe_plan',
]


@dataclass(frozen=True)
class CapacityPeak:
    location_id: str
    unit: str
    peak: int
    interval_start_s: int
    interval_end_s: int


@dataclass(frozen=True)
class ExposureTotal:
    batch_id: str
    scopes: tuple[str, ...]
    union_s: int


@dataclass(frozen=True)
class PlanObservations:
    plan_id: str
    snapshot_id: str
    snapshot_version: int
    requested_order_ids: tuple[str, ...]
    served_order_ids: tuple[str, ...]
    unserved: tuple[tuple[str, str], ...]
    handoff_wait_s: tuple[tuple[str, int], ...]
    warehouse_makespan_s: int
    total_distance_m: int
    total_duration_s: int
    coldchain_evidence: bool
    capacity_peaks: tuple[CapacityPeak, ...]
    exposure_totals: tuple[ExposureTotal, ...]
    changeover_count: int
    changeover_duration_s: int
    warehouse_solve_status: str
    routing_solve_status: str
    validation_status: str
    negotiation_status: str | None = None
    negotiation_awards: int = 0
    negotiation_conflicts: int = 0
    negotiation_digest: str | None = None

    @property
    def requested_count(self) -> int:
        return len(self.requested_order_ids)

    @property
    def served_count(self) -> int:
        return len(self.served_order_ids)


def _union_length(intervals: list[tuple[int, int]]) -> int:
    merged: list[list[int]] = []
    for start, end in sorted(intervals):
        if merged and start <= merged[-1][1]:
            merged[-1][1] = max(merged[-1][1], end)
        else:
            merged.append([start, end])
    return sum(end - start for start, end in merged)


def _peaks(entries: list[tuple[int, int, int]]) -> list[tuple[int, int, int]]:
    """Peak load and the half-open interval that produced it."""
    events: list[tuple[int, int]] = []
    for start, end, amount in entries:
        events.append((start, amount))
        events.append((end, -amount))
    events.sort(key=lambda item: (item[0], item[1]))
    current = 0
    peak = 0
    peak_at = 0
    for moment, delta in events:
        current += delta
        if current > peak:
            peak, peak_at = current, moment
    if peak == 0:
        return []
    following = [moment for moment, _ in events if moment > peak_at]
    end = following[0] if following else peak_at
    return [(peak, peak_at, end)]


def observe_plan(plan: CandidatePlan, requested_order_ids: tuple[str, ...],
                 *, negotiation: NegotiationResult | None = None) -> PlanObservations:
    """Collect the observable business facts of one plan."""
    requested = tuple(requested_order_ids)
    unserved = tuple(sorted((item.order_id, item.reason_code)
                            for item in plan.routing.unserved_orders))
    unserved_ids = {order_id for order_id, _ in unserved}

    served: list[str] = []
    for route in plan.routing.routes:
        for stop in route.stops:
            if stop.stop_kind != 'delivery':
                continue
            for order_id in stop.order_ids:
                if order_id not in unserved_ids and order_id not in served:
                    served.append(order_id)
    served_tuple = tuple(sorted(served))

    departures: dict[str, int] = {}
    for route in plan.routing.routes:
        departure = next((stop.departure_at_s for stop in route.stops
                          if stop.stop_kind == 'depot_start'), None)
        if departure is None:
            continue
        for order_id in (order for stop in route.stops for order in stop.order_ids):
            departures.setdefault(order_id, departure)
    waits = tuple(sorted(
        (handoff.order_id, departures.get(handoff.order_id, handoff.ready_at_s) - handoff.ready_at_s)
        for handoff in plan.warehouse.warehouse_handoffs
    ))

    makespan = max((item.end_s for item in plan.warehouse.operations), default=0)

    coldchain = plan.warehouse.coldchain
    peaks: list[CapacityPeak] = []
    exposures: list[ExposureTotal] = []
    changeovers = 0
    changeover_duration = 0
    if coldchain is not None:
        usage: dict[tuple[str, str], list[tuple[int, int, int]]] = {}
        for occupancy in coldchain.occupancies:
            for use in occupancy.capacity_use:
                usage.setdefault((occupancy.location_id, use.unit), []).append(
                    (occupancy.start_s, occupancy.end_s, use.amount)
                )
        for (location_id, unit), entries in sorted(usage.items()):
            for peak, start, end in _peaks(entries):
                peaks.append(CapacityPeak(location_id=location_id, unit=unit, peak=peak,
                                          interval_start_s=start, interval_end_s=end))

        segments: dict[str, list[tuple[int, int]]] = {}
        scopes: dict[str, set[str]] = {}
        for segment in coldchain.exposure_segments:
            segments.setdefault(segment.batch_id, []).append((segment.start_s, segment.end_s))
            scopes.setdefault(segment.batch_id, set()).add(segment.scope)
        for batch_id, intervals in sorted(segments.items()):
            exposures.append(ExposureTotal(
                batch_id=batch_id, scopes=tuple(sorted(scopes[batch_id])),
                union_s=_union_length(intervals),
            ))

        changeovers = len(coldchain.changeovers)
        changeover_duration = sum(item.duration_s for item in coldchain.changeovers)

    return PlanObservations(
        plan_id=plan.plan_id,
        snapshot_id=plan.snapshot_id,
        snapshot_version=plan.snapshot_version,
        requested_order_ids=requested,
        served_order_ids=served_tuple,
        unserved=unserved,
        handoff_wait_s=waits,
        warehouse_makespan_s=makespan,
        total_distance_m=sum(route.distance_m for route in plan.routing.routes),
        total_duration_s=sum(route.duration_s for route in plan.routing.routes),
        coldchain_evidence=coldchain is not None,
        capacity_peaks=tuple(peaks),
        exposure_totals=tuple(exposures),
        changeover_count=changeovers,
        changeover_duration_s=changeover_duration,
        warehouse_solve_status=plan.warehouse.metadata.status,
        routing_solve_status=plan.routing.metadata.status,
        validation_status=plan.validation.status,
        negotiation_status=negotiation.status if negotiation is not None else None,
        negotiation_awards=len(negotiation.awards) if negotiation is not None else 0,
        negotiation_conflicts=len(negotiation.conflicts) if negotiation is not None else 0,
        negotiation_digest=negotiation.digest if negotiation is not None else None,
    )
