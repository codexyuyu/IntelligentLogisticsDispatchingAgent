"""Owner: B | Transport metrics that do not alter the shared RoutingResult contract.

The shared RoutingResult currently exposes distance and duration but has no
transport-cost field. This module therefore computes cost as a sidecar metric
only when an explicit vehicle cost-per-km catalog is provided. No arbitrary
cost is invented inside the solver.
"""
from __future__ import annotations

from collections.abc import Mapping, Sequence
from decimal import Decimal


def route_cost_by_vehicle(
    routes: Sequence[Mapping[str, object]],
    cost_per_km: Mapping[str, Decimal | int | float | str],
) -> dict[str, Decimal]:
    """Return explicit route transport costs keyed by vehicle id.

    Cost is ``distance_m / 1000 * cost_per_km``. Missing vehicle rates are an
    explicit error because the shared contract does not define a default rate.
    """
    result: dict[str, Decimal] = {}
    for route in routes:
        vehicle_id = str(route["vehicle_id"])
        if vehicle_id not in cost_per_km:
            raise ValueError(f"missing_cost_rate:{vehicle_id}")
        rate = Decimal(str(cost_per_km[vehicle_id]))
        if rate < 0:
            raise ValueError(f"negative_cost_rate:{vehicle_id}")
        distance_m = int(route["distance_m"])
        result[vehicle_id] = (Decimal(distance_m) / Decimal(1000)) * rate
    return result


def total_transport_cost(
    routes: Sequence[Mapping[str, object]],
    cost_per_km: Mapping[str, Decimal | int | float | str],
) -> Decimal:
    return sum(route_cost_by_vehicle(routes, cost_per_km).values(), Decimal("0"))
