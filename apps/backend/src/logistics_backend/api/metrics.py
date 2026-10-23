"""Metric calculation and persistence API (P32)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query, Request

from logistics_backend.api.dependencies import operator
from logistics_backend.application.metrics import MetricsService
from logistics_contracts.metrics import (
    MetricHistoryPage,
    MetricPage,
    SimulationMetricsRequest,
    TransportMetricsRequest,
)
from logistics_domain.runtime import ActorContext

router = APIRouter(tags=["metrics"])


def metrics_service(request: Request) -> MetricsService:
    return request.app.state.metrics


@router.post("/metrics/transport", response_model=MetricPage, operation_id="transport_metrics")
def transport_metrics(command: TransportMetricsRequest,
                      current: ActorContext = Depends(operator),
                      service: MetricsService = Depends(metrics_service)):
    return service.transport(command, current)


@router.post("/metrics/simulation", response_model=MetricPage, operation_id="simulation_metrics")
def simulation_metric_values(command: SimulationMetricsRequest,
                             current: ActorContext = Depends(operator),
                             service: MetricsService = Depends(metrics_service)):
    return service.simulation(command, current)


@router.get("/metrics/history", response_model=MetricHistoryPage,
            operation_id="metric_history")
def metric_history(current: ActorContext = Depends(operator),
                   service: MetricsService = Depends(metrics_service),
                   code: str | None = Query(default=None, max_length=64),
                   limit: int = Query(default=50, ge=1, le=200)):
    return service.history(current, code, limit)
