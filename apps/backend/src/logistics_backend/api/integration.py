"""Authenticated imports and R05/R08/R09 inspection in the existing API."""
import json
from pathlib import Path
from typing import Annotated, Any, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, Header, Query, Request
from pydantic import BaseModel, ConfigDict, Field

from logistics_backend.api.dependencies import actor, operator
from logistics_backend.application.scenario_import import prepare_scenario
from logistics_backend.application.delay_benchmark import solve_delay_benchmark
from logistics_contracts.integration import IntegrationRun, RevokeInput, ScenarioImport

router = APIRouter(prefix='/integration', tags=['integration'])


def service(request: Request):
    return request.app.state.integration


def simulation_service(request: Request):
    return request.app.state.integration_simulation


class SimulationIncidentInput(BaseModel):
    model_config = ConfigDict(extra='forbid')
    vehicle_id: UUID
    time_s: int = Field(ge=0)
    delay_s: int = Field(gt=0)
    source_event_id: str = Field(min_length=1, max_length=64)
    reason: str = Field(min_length=1, max_length=256)
    budget_ms: int = Field(default=1000, ge=100, le=4000)


class SimulationDecisionInput(BaseModel):
    model_config = ConfigDict(extra='forbid')
    expected_row_version: int = Field(ge=0)


@router.get('/benchmarks/delay-replanning', operation_id='get_delay_replanning_benchmark')
def delay_replanning_benchmark(current: Annotated[Any, Depends(actor)],
                               delay_s: int = Query(default=90, ge=0, le=1200)):
    """Read-only exact counterfactual, not a persisted operational run."""
    return solve_delay_benchmark(delay_s=delay_s)


@router.get('/priority-delay-template', operation_id='get_priority_delay_integration_template')
def priority_delay_template(current: Annotated[Any, Depends(actor)]):
    """Read-only checked-scenario source; importing is a separate operator action.

    This fixture is deliberately synthetic and does NOT guarantee a positive
    saving for every delay/vehicle: actual projection metrics decide that.
    """
    path = Path(__file__).resolve().parents[5] / 'data/scenarios/coldchain_chain_10_priority_delay.json'
    return json.loads(path.read_text(encoding='utf-8'))


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


@router.get('/runs/{run_id}/timeline', operation_id='read_integration_timeline')
def timeline(run_id: UUID, current: Annotated[Any, Depends(actor)], app: Annotated[Any, Depends(service)]):
    return app.timeline(run_id, current)


@router.get('/runs/{run_id}/state-at', operation_id='read_integration_state_at')
def state_at(run_id: UUID, current: Annotated[Any, Depends(actor)], app: Annotated[Any, Depends(service)],
             time_s: int = Query(ge=0)):
    return app.state_at(run_id, time_s, current)


@router.post('/runs/{run_id}/simulation', operation_id='start_checked_integration_simulation')
def start_simulation(run_id: UUID, current: Annotated[Any, Depends(operator)],
                     app: Annotated[Any, Depends(simulation_service)]):
    return app.start(run_id, current)


@router.get('/runs/{run_id}/simulation', operation_id='read_checked_integration_simulation')
def read_simulation(run_id: UUID, current: Annotated[Any, Depends(actor)],
                    app: Annotated[Any, Depends(simulation_service)]):
    return app.get(run_id, current)


@router.get('/runs/{run_id}/simulation/opportunities', operation_id='find_integration_delay_opportunities')
def find_delay_opportunities(run_id: UUID, current: Annotated[Any, Depends(actor)],
                             app: Annotated[Any, Depends(simulation_service)],
                             delay_s: int = Query(default=90, ge=1, le=1200)):
    """Read-only, bounded screening of mid-arc reroutes; no database writes."""
    return app.opportunities(run_id, current, delay_s=delay_s)


@router.post('/runs/{run_id}/simulation/incidents', operation_id='inject_integration_simulated_delay')
def inject_simulated_delay(run_id: UUID, command: SimulationIncidentInput,
                           request: Request, current: Annotated[Any, Depends(operator)],
                           app: Annotated[Any, Depends(simulation_service)]):
    return app.incident(run_id, command, current, request.state.trace_id)


@router.post('/runs/{run_id}/simulation/incidents/{incident_id}/approve',
             operation_id='approve_integration_simulated_delay')
def approve_simulated_delay(run_id: UUID, incident_id: UUID, command: SimulationDecisionInput,
                            current: Annotated[Any, Depends(operator)],
                            app: Annotated[Any, Depends(simulation_service)]):
    return app.decide(run_id, incident_id, 'approved', current, command.expected_row_version)


@router.post('/runs/{run_id}/simulation/incidents/{incident_id}/reject',
             operation_id='reject_integration_simulated_delay')
def reject_simulated_delay(run_id: UUID, incident_id: UUID, command: SimulationDecisionInput,
                           current: Annotated[Any, Depends(operator)],
                           app: Annotated[Any, Depends(simulation_service)]):
    return app.decide(run_id, incident_id, 'rejected', current, command.expected_row_version)


@router.get('/runs/{run_id}/simulation/state-at', operation_id='replay_integration_simulation')
def simulation_state_at(run_id: UUID, current: Annotated[Any, Depends(actor)],
                        app: Annotated[Any, Depends(simulation_service)],
                        time_s: int = Query(ge=0),
                        view: Literal['active', 'baseline', 'candidate'] = 'active'):
    return app.state_at(run_id, time_s, view, current)


@router.post('/runs/{run_id}/revoke', operation_id='revoke_integration_award')
def revoke(run_id: UUID, command: RevokeInput, current: Annotated[Any, Depends(operator)], app: Annotated[Any, Depends(service)]):
    return app.revoke(run_id, command, current)


class BreakdownShowcaseInput(BaseModel):
    model_config = ConfigDict(extra='forbid')
    budget_ms: int = Field(default=1800, ge=100, le=5000)


@router.post('/showcase/vehicle-breakdown/solve', operation_id='solve_vehicle_breakdown_showcase')
def solve_vehicle_breakdown_showcase(command: BreakdownShowcaseInput,
                                    current: Annotated[Any, Depends(operator)]):
    """Real OR-Tools cross-vehicle cargo handoff; synthetic read-only showcase.

    Returns the complete baseline, stranded plan and validated candidate.
    No operational assignment, PostgreSQL state, inventory or approval is changed.
    """
    from logistics_backend.application.fault_rescue_showcase import solve_breakdown_showcase
    return solve_breakdown_showcase(command.budget_ms)


@router.post('/showcase/vehicle-breakdown/ai-collaborate',
             operation_id='collaborate_vehicle_breakdown_showcase')
def collaborate_vehicle_breakdown_showcase(command: BreakdownShowcaseInput,
                                          current: Annotated[Any, Depends(operator)],
                                          request: Request):
    """Bounded DeepSeek tool calls, real solver, no DB writes or auto approval."""
    from logistics_backend.application.ai_fault_rescue import collaborate
    provider = request.app.state.natural_dispatch.provider
    return collaborate(provider, command.budget_ms)
