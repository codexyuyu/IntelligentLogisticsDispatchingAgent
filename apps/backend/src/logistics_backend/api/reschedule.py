"""Local reschedule proposal API (P15-01 subset)."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from logistics_backend.api.dependencies import operator
from logistics_backend.application.reschedule import RescheduleService
from logistics_contracts.reschedule import RescheduleProposalDTO, RescheduleProposalRequest
from logistics_domain.runtime import ActorContext

router = APIRouter(tags=["reschedule"])


def reschedule_service() -> RescheduleService:
    return RescheduleService()


@router.post("/reschedules/proposals", response_model=RescheduleProposalDTO,
             operation_id="propose_reschedule")
def propose_reschedule(command: RescheduleProposalRequest,
                       current: ActorContext = Depends(operator),
                       service: RescheduleService = Depends(reschedule_service)):
    return service.propose(command)
