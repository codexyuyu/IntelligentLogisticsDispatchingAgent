"""Paired experiment comparison and persistence API (P33)."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request

from logistics_backend.api.dependencies import actor, operator
from logistics_backend.application.experiment import ExperimentService
from logistics_contracts.experiment import (
    ExperimentCompareRequest,
    ExperimentComparisonDTO,
    ExperimentPage,
    ExperimentView,
)
from logistics_domain.runtime import ActorContext

router = APIRouter(tags=["experiments"])


def experiment_service(request: Request) -> ExperimentService:
    return request.app.state.experiments


@router.post("/experiments/compare", response_model=ExperimentComparisonDTO,
             operation_id="compare_experiment_results")
def compare_experiment_results(command: ExperimentCompareRequest,
                               current: ActorContext = Depends(operator),
                               service: ExperimentService = Depends(experiment_service)):
    return service.compare(command, current)


@router.get("/experiments", response_model=ExperimentPage,
            operation_id="list_experiments")
def list_experiments(current: ActorContext = Depends(actor),
                     service: ExperimentService = Depends(experiment_service),
                     limit: int = Query(default=50, ge=1, le=200)):
    return service.list(current, limit)


@router.get("/experiments/{experiment_id}", response_model=ExperimentView,
            operation_id="get_experiment")
def get_experiment(experiment_id: UUID, current: ActorContext = Depends(actor),
                   service: ExperimentService = Depends(experiment_service)):
    return service.get(experiment_id, current)
