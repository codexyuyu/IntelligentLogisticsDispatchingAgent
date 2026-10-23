"""Impact analysis API (P14 subset)."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from logistics_backend.api.dependencies import operator
from logistics_backend.application.impact import ImpactService
from logistics_contracts.impact import ImpactAnalysisDTO, ImpactRequestDTO
from logistics_domain.runtime import ActorContext

router = APIRouter(tags=["exceptions"])


def impact_service() -> ImpactService:
    return ImpactService()


@router.post("/exceptions/impact", response_model=ImpactAnalysisDTO,
             operation_id="analyse_exception_impact")
def analyse_impact(command: ImpactRequestDTO, current: ActorContext = Depends(operator),
                   service: ImpactService = Depends(impact_service)):
    return service.analyse(command)
