"""Owner: AC | Business status: scaffold; every route has an explicit operation_id."""
from fastapi import APIRouter
from app.api.dependencies import IdempotencyKey
from app.contracts.http import *
from app.contracts.planning import DispatchRequest
from app.contracts.events import DispatchEvent, SimulationRequest
from app.application import http_services
router = APIRouter()

@router.post('/requests/parse', response_model=ParseResponse, status_code=200, operation_id='parse_request')
def parse_request(body: ParseRequest) -> ParseResponse:
    return http_services.parse_request(body)

