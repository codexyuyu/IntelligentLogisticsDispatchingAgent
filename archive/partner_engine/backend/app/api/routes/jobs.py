"""Owner: AC | Business status: scaffold; every route has an explicit operation_id."""
from fastapi import APIRouter
from app.api.dependencies import IdempotencyKey
from app.contracts.http import *
from app.contracts.planning import DispatchRequest
from app.contracts.events import DispatchEvent, SimulationRequest
from app.application import http_services
router = APIRouter()

@router.get('/jobs/{job_id}', response_model=JobResponse, status_code=200, operation_id='get_job')
def get_job(job_id: str) -> JobResponse:
    return http_services.get_job(job_id)

