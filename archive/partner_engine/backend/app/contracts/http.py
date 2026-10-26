"""SHARED: HTTP request and response bodies; routes are declared in api/routes."""
from typing import Literal
from pydantic import StrictStr
from app.contracts.common import ContractModel, Id, PositiveInt, Hash, Source, ValidationReport, CONTRACT_VERSION
from app.contracts.entities import PlanningSnapshot
from app.contracts.planning import CandidatePlan
from app.contracts.reschedule import LocalRescheduleResult
from app.contracts.events import SimulationResult
from app.domain.states import JobStatus, PlanStatus

class HealthResponse(ContractModel):
    status: Literal['ok'] = 'ok'
    mode: Literal['skeleton'] = 'skeleton'
    contract_version: StrictStr = CONTRACT_VERSION

class ScenarioImportRequest(ContractModel):
    scenario_id: Id
    snapshot: PlanningSnapshot

class ScenarioImportResponse(ContractModel):
    scenario_id: Id
    snapshot_id: Id
    version: PositiveInt
    validation: ValidationReport

class ParseRequest(ContractModel):
    snapshot_id: Id
    text: StrictStr

class ParseResponse(ContractModel):
    request_id: Id
    intent: Literal['plan_existing_orders', 'explain_plan', 'unsupported']
    order_ids: tuple[Id, ...]
    sources: tuple[Source, ...]
    clarification_fields: tuple[StrictStr, ...]
    requires_confirmation: Literal[True] = True

class JobAccepted(ContractModel):
    job_id: Id
    status: JobStatus

class JobResponse(ContractModel):
    job_id: Id
    status: JobStatus
    plan_id: Id | None
    error_code: StrictStr | None

class PlanResponse(ContractModel):
    plan: CandidatePlan
    status: PlanStatus

class ConfirmPlanRequest(ContractModel):
    expected_version: PositiveInt
    expected_snapshot_version: PositiveInt
    plan_hash: Hash

class ConfirmPlanResponse(ContractModel):
    plan_id: Id
    version: PositiveInt
    status: Literal['confirmed']

class EventAccepted(ContractModel):
    event_id: Id
    duplicate: bool
    replanning_job_id: Id | None
    result: LocalRescheduleResult | None = None

class SimulationAccepted(ContractModel):
    simulation_id: Id
    job_id: Id

class SimulationResponse(ContractModel):
    simulation: SimulationResult
    status: Literal["completed"] = "completed"

class EvidenceResponse(ContractModel):
    run_id: Id
    plan_id: Id
    source_refs: tuple[StrictStr, ...]
    trace_ids: tuple[StrictStr, ...]
    validation: ValidationReport
