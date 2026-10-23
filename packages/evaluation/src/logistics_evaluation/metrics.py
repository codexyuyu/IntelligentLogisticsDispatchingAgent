"""Deterministic metric calculators (P32-01 subset)."""

from __future__ import annotations

from logistics_domain.metrics import MetricSource, MetricValue, MissingReason
from logistics_domain.planning import TransportPlan
from logistics_domain.simulation import SimulationResult

DEFINITION_VERSION = "1.0.0"


def _value(code: str, source: MetricSource, unit: str, value: float,
           numerator: float | None = None, denominator: float | None = None,
           sample_count: int = 1) -> MetricValue:
    return MetricValue(code=code, definition_version=DEFINITION_VERSION, source=source,
        unit=unit, value=float(value), numerator=numerator, denominator=denominator,
        reason=None, sample_count=sample_count)


def _missing(code: str, source: MetricSource, unit: str, reason: MissingReason) -> MetricValue:
    return MetricValue(code=code, definition_version=DEFINITION_VERSION, source=source,
        unit=unit, value=None, numerator=None, denominator=None, reason=reason,
        sample_count=0)


def transport_plan_metrics(plan: TransportPlan, orders_total: int,
                           vehicle_count: int) -> tuple[MetricValue, ...]:
    if orders_total < 0 or vehicle_count < 0:
        raise ValueError("orders_total and vehicle_count must be non-negative")
    routes = len(plan.routes)
    distance = sum(route.total_distance_m for route in plan.routes)
    served = max(0, orders_total - len(plan.unserved_order_ids))
    metrics = [
        _value("route_count", MetricSource.PLANNED, "count", routes, sample_count=routes),
        _value("total_distance_m", MetricSource.PLANNED, "m", distance),
        _value("total_cost_cents", MetricSource.PLANNED, "fen", plan.cost.total_cents),
        _value("served_orders", MetricSource.PLANNED, "count", served, sample_count=served),
        _value("unserved_orders", MetricSource.PLANNED, "count",
               len(plan.unserved_order_ids), sample_count=orders_total),
    ]
    if orders_total:
        metrics.append(_value("delivery_rate", MetricSource.PLANNED, "ratio",
                              served / orders_total, served, orders_total, orders_total))
    else:
        metrics.append(_missing("delivery_rate", MetricSource.PLANNED, "ratio",
                                MissingReason.DIVISION_BY_ZERO))
    if routes:
        metrics.append(_value("average_route_distance_m", MetricSource.PLANNED, "m",
                              distance / routes, distance, routes, routes))
    else:
        metrics.append(_missing("average_route_distance_m", MetricSource.PLANNED, "m",
                                MissingReason.DIVISION_BY_ZERO))
    if vehicle_count:
        metrics.append(_value("route_per_vehicle", MetricSource.PLANNED, "ratio",
                              routes / vehicle_count, routes, vehicle_count, vehicle_count))
    else:
        metrics.append(_missing("route_per_vehicle", MetricSource.PLANNED, "ratio",
                                MissingReason.DIVISION_BY_ZERO))
    metrics.append(_missing("changed_tasks", MetricSource.PLANNED, "count",
                            MissingReason.NOT_APPLICABLE))
    return tuple(metrics)


def simulation_metrics(result: SimulationResult, orders_total: int) -> tuple[MetricValue, ...]:
    delivered = len(result.delivered_order_ids)
    metrics = [
        _value("simulated_events", MetricSource.SIMULATION, "count", len(result.events),
               sample_count=len(result.events)),
        _value("simulated_delivered_orders", MetricSource.SIMULATION, "count", delivered,
               sample_count=delivered),
        _value("simulation_final_time_s", MetricSource.SIMULATION, "s", result.final_time_s),
    ]
    if orders_total:
        metrics.append(_value("simulated_delivery_rate", MetricSource.SIMULATION, "ratio",
                              delivered / orders_total, delivered, orders_total, orders_total))
    else:
        metrics.append(_missing("simulated_delivery_rate", MetricSource.SIMULATION, "ratio",
                                MissingReason.DIVISION_BY_ZERO))
    return tuple(metrics)


__all__ = ["transport_plan_metrics", "simulation_metrics"]
