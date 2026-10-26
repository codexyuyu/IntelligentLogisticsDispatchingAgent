"""Owner: AC | Business status: scaffold; every route has an explicit operation_id."""
from fastapi import APIRouter
from app.api.dependencies import IdempotencyKey
from app.contracts.http import *
from app.contracts.planning import DispatchRequest
from app.contracts.events import DispatchEvent, SimulationRequest
from app.application import http_services
router = APIRouter()

@router.post('/scenarios/import', response_model=ScenarioImportResponse, status_code=201, operation_id='import_scenario')
def import_scenario(body: ScenarioImportRequest, idempotency_key: IdempotencyKey) -> ScenarioImportResponse:
    return http_services.import_scenario(body, idempotency_key)

