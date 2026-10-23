"""Metric calculation API (P32 subset); pure, read-only, no database."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from logistics_backend.api.dependencies import actor
from logistics_contracts.mapping import metric_dto
from logistics_contracts.metrics import (
    MetricPage,
    SimulationMetricsRequest,
    TransportMetricsRequest,
)
from logistics_evaluation.metrics import simulation_metrics, transport_plan_metrics
from logistics_domain.runtime import ActorContext

router = APIRouter(tags=["metrics"])


@router.post("/metrics/transport", response_model=MetricPage, operation_id="transport_metrics")
def transport_metrics(command: TransportMetricsRequest,
                      current: ActorContext = Depends(actor)):
    plan = command.plan.to_domain()
    values = transport_plan_metrics(plan, command.orders_total, command.vehicle_count)
    return MetricPage(metrics=tuple(metric_dto(value) for value in values))


@router.post("/metrics/simulation", response_model=MetricPage, operation_id="simulation_metrics")
def simulation_metric_values(command: SimulationMetricsRequest,
                             current: ActorContext = Depends(actor)):
    result = command.result.to_domain()
    values = simulation_metrics(result, command.orders_total)
    return MetricPage(metrics=tuple(metric_dto(value) for value in values))
