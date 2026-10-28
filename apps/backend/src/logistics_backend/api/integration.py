"""Authenticated imports and R05/R08/R09 inspection in the existing API."""
import json
from pathlib import Path
from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Depends, Header, Request

from logistics_backend.api.dependencies import actor, operator
from logistics_backend.application.scenario_import import prepare_scenario
from logistics_contracts.integration import IntegrationRun, RevokeInput, ScenarioImport

router = APIRouter(prefix='/integration', tags=['integration'])


def service(request: Request):
    return request.app.state.integration


@router.get('/template', operation_id='get_integration_template')
def template(current: Annotated[Any, Depends(actor)]):
    path = Path(__file__).resolve().parents[5] / 'data/scenarios/partner_coldchain_synthetic.json'
    return json.loads(path.read_text(encoding='utf-8'))


@router.post('/scenarios/check', operation_id='check_integration_scenario')
def check_scenario(command: ScenarioImport, current: Annotated[Any, Depends(operator)]):
    result = prepare_scenario(command)
    return {k: v for k, v in result.items() if k != 'payload'}


@router.post('/scenarios', operation_id='import_integration_scenario')
def import_scenario(command: ScenarioImport, current: Annotated[Any, Depends(operator)], app: Annotated[Any, Depends(service)]):
    return app.import_scenario(command, current)


@router.get('/scenarios', operation_id='list_integration_scenarios')
def list_scenarios(current: Annotated[Any, Depends(actor)], app: Annotated[Any, Depends(service)]):
    return app.list_scenarios(current)


@router.post('/runs', operation_id='run_integration')
def run(command: IntegrationRun, current: Annotated[Any, Depends(operator)], app: Annotated[Any, Depends(service)],
        request: Request, key: str = Header(alias='Idempotency-Key', min_length=1, max_length=128),
        wait: bool = True):
    return app.run(command, current, key, request.state.trace_id, wait=wait)


@router.get('/runs/{run_id}', operation_id='read_integration_run')
def get_run(run_id: UUID, current: Annotated[Any, Depends(actor)], app: Annotated[Any, Depends(service)]):
    return app.get(run_id, current)


@router.get('/runs/{run_id}/observations', operation_id='read_integration_observations')
def observations(run_id: UUID, current: Annotated[Any, Depends(actor)], app: Annotated[Any, Depends(service)]):
    result = app.get(run_id, current)
    return {'status': result['status'], 'source_kind': result.get('source_kind'),
            'observations': result.get('observations'), 'reason': result.get('reason')}


@router.post('/runs/{run_id}/revoke', operation_id='revoke_integration_award')
def revoke(run_id: UUID, command: RevokeInput, current: Annotated[Any, Depends(operator)], app: Annotated[Any, Depends(service)]):
    return app.revoke(run_id, command, current)
