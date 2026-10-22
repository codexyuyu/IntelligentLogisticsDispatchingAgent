"""Owner: AC | Business status: scaffold; every route has an explicit operation_id."""
from fastapi import APIRouter
from app.api.dependencies import IdempotencyKey
from app.contracts.http import *
from app.contracts.planning import DispatchRequest
from app.contracts.events import DispatchEvent, SimulationRequest
from app.application import http_services
router = APIRouter()

@router.post('/events', response_model=EventAccepted, status_code=202, operation_id='submit_event')
def submit_event(body: DispatchEvent, idempotency_key: IdempotencyKey) -> EventAccepted:
    return http_services.submit_event(body, idempotency_key)

