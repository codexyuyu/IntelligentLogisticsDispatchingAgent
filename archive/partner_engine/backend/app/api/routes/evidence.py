"""Owner: AC | Business status: scaffold; every route has an explicit operation_id."""
from fastapi import APIRouter
from app.api.dependencies import IdempotencyKey
from app.contracts.http import *
from app.contracts.planning import DispatchRequest
from app.contracts.events import DispatchEvent, SimulationRequest
from app.application import http_services
router = APIRouter()

@router.get('/runs/{run_id}/evidence', response_model=EvidenceResponse, status_code=200, operation_id='get_evidence')
def get_evidence(run_id: str) -> EvidenceResponse:
    return http_services.get_evidence(run_id)

