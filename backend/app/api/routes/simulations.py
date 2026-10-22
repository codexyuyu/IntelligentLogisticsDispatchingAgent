"""Owner: AC | Business status: scaffold; every route has an explicit operation_id."""
from fastapi import APIRouter
from app.api.dependencies import IdempotencyKey
from app.contracts.http import *
from app.contracts.planning import DispatchRequest
from app.contracts.events import DispatchEvent, SimulationRequest
from app.application import http_services
router = APIRouter()

@router.post('/simulations', response_model=SimulationAccepted, status_code=202, operation_id='submit_simulation')
def submit_simulation(body: SimulationRequest, idempotency_key: IdempotencyKey) -> SimulationAccepted:
    return http_services.submit_simulation(body, idempotency_key)



@router.get('/simulations/{simulation_id}', response_model=SimulationResponse, operation_id='get_simulation')
def get_simulation(simulation_id: str) -> SimulationResponse:
    return http_services.get_simulation(simulation_id)
