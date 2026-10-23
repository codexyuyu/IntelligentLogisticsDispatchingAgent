"""Paired experiment comparison API (P33-01 subset)."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from logistics_backend.api.dependencies import actor
from logistics_contracts.experiment import ExperimentCompareRequest, ExperimentComparisonDTO
from logistics_contracts.mapping import experiment_comparison_dto
from logistics_domain.runtime import ActorContext
from logistics_evaluation.metrics import compare_metrics, simulation_metrics

router = APIRouter(tags=["experiments"])


@router.post("/experiments/compare", response_model=ExperimentComparisonDTO,
             operation_id="compare_experiment_results")
def compare_experiment_results(command: ExperimentCompareRequest,
                               current: ActorContext = Depends(actor)):
    base = simulation_metrics(command.base.to_domain(), command.orders_total)
    candidate = simulation_metrics(command.candidate.to_domain(), command.orders_total)
    return experiment_comparison_dto(compare_metrics(command.base_label,
        command.candidate_label, base, candidate))
