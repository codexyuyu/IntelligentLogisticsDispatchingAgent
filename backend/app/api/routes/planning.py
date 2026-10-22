"""Owner: AC | Business status: scaffold; every route has an explicit operation_id."""
from fastapi import APIRouter
from app.api.dependencies import IdempotencyKey
from app.contracts.http import *
from app.contracts.planning import DispatchRequest
from app.contracts.events import DispatchEvent, SimulationRequest
from app.application import http_services
router = APIRouter()

@router.post('/planning-jobs', response_model=JobAccepted, status_code=202, operation_id='submit_planning_job')
def submit_planning_job(body: DispatchRequest, idempotency_key: IdempotencyKey) -> JobAccepted:
    return http_services.submit_planning_job(body, idempotency_key)

