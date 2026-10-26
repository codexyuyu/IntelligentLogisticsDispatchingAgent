"""Owner: AC | Business status: scaffold; every route has an explicit operation_id."""
from fastapi import APIRouter
from app.api.dependencies import IdempotencyKey
from app.contracts.http import *
from app.contracts.planning import DispatchRequest
from app.contracts.events import DispatchEvent, SimulationRequest
from app.application import http_services
router = APIRouter()

@router.get('/plans/{plan_id}', response_model=PlanResponse, status_code=200, operation_id='get_plan')
def get_plan(plan_id: str) -> PlanResponse:
    return http_services.get_plan(plan_id)

@router.post('/plans/{plan_id}/confirm', response_model=ConfirmPlanResponse, status_code=200, operation_id='confirm_plan')
def confirm_plan(plan_id: str, body: ConfirmPlanRequest, idempotency_key: IdempotencyKey) -> ConfirmPlanResponse:
    return http_services.confirm_plan(plan_id, body, idempotency_key)

