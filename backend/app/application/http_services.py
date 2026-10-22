from __future__ import annotations
import hashlib, json
from uuid import uuid4
from app.adapters.routing.ortools_solver import OrToolsRoutingSolver
from app.adapters.warehouse.cp_sat_scheduler import CpSatWarehouseScheduler
from app.application.runtime import JobRecord, runtime
from app.contracts.common import SolveMetadata, ValidationReport
from app.contracts.http import *
from app.contracts.planning import CandidatePlan, DispatchRequest, RoutingRequest, WarehouseScheduleRequest
from app.contracts.events import DispatchEvent, SimulationRequest
from app.common.errors import FeatureNotImplemented
from app.domain.transport_rules import validate_transport

def import_scenario(body: ScenarioImportRequest, idempotency_key: str):
    existing = runtime.snapshots.get(body.snapshot.snapshot_id)
    if existing and existing.version != body.snapshot.version:
        raise ValueError(f"snapshot_version_conflict:{body.snapshot.snapshot_id}:existing={existing.version}:incoming={body.snapshot.version}")
    runtime.put_snapshot(body.snapshot)
    return ScenarioImportResponse(scenario_id=body.scenario_id, snapshot_id=body.snapshot.snapshot_id, version=body.snapshot.version, validation=ValidationReport(status="passed", validator_version="scenario-import-0.1", checked_rule_ids=("scenario.snapshot_contract",), violations=()))

def parse_request(body: ParseRequest): raise FeatureNotImplemented("parse_request", "AC")

def submit_planning_job(body: DispatchRequest, idempotency_key: str):
    key=f"planning:{idempotency_key}"
    if key in runtime.idempotency: return JobAccepted.model_validate(runtime.idempotency[key]["response"])
    snapshot=runtime.get_snapshot(body.snapshot_id, body.expected_snapshot_version)
    job=JobRecord(job_id=f"job_{uuid4().hex[:20]}", status="running"); runtime.put_job(job)
    try:
        plan=_build_candidate_plan(snapshot, body)
        runtime.put_plan(plan); job.status="succeeded"; job.plan_id=plan.plan_id
        response=JobAccepted(job_id=job.job_id,status="succeeded")
    except Exception as exc:
        job.status="failed"; job.error_code=str(exc); response=JobAccepted(job_id=job.job_id,status="failed")
    runtime.idempotency[key]={"response":response.model_dump(mode="json")}
    return response

def get_job(job_id: str):
    r=runtime.get_job(job_id)
    return JobResponse(job_id=r.job_id,status=r.status,plan_id=r.plan_id,error_code=r.error_code)

def get_plan(plan_id: str):
    p=runtime.get_plan(plan_id)
    return PlanResponse(plan=p,status="validated")

def confirm_plan(plan_id, body, idempotency_key): raise FeatureNotImplemented("confirm_plan", "AC")
def submit_event(body: DispatchEvent, idempotency_key: str):
    key = f"event:{idempotency_key}"
    if key in runtime.idempotency:
        return EventAccepted.model_validate(runtime.idempotency[key]["response"])
    previous_plan = runtime.get_latest_plan(body.snapshot_id, body.expected_snapshot_version)
    job = JobRecord(job_id=f"job_{uuid4().hex[:20]}", status="running")
    runtime.put_job(job)
    try:
        from app.application.handle_event import handle_event
        result = handle_event(event=body, previous_plan=previous_plan, budget_ms=60000)
        runtime.put_snapshot(_snapshot_from_result(result))
        runtime.put_plan(result.replanned_plan)
        runtime.put_reschedule(result)
        runtime.events[body.event_id] = body
        job.status = "succeeded"
        job.plan_id = result.replanned_plan.plan_id
        response = EventAccepted(event_id=body.event_id, duplicate=False, replanning_job_id=job.job_id, result=result)
    except Exception as exc:
        job.status = "failed"
        job.error_code = str(exc)
        response = EventAccepted(event_id=body.event_id, duplicate=False, replanning_job_id=job.job_id, result=None)
    runtime.idempotency[key] = {"response": response.model_dump(mode="json")}
    return response
def submit_simulation(body: SimulationRequest, idempotency_key: str):
    key = f"simulation:{idempotency_key}"
    if key in runtime.idempotency:
        return SimulationAccepted.model_validate(runtime.idempotency[key]["response"])
    job = JobRecord(job_id=f"job_{uuid4().hex[:20]}", status="running")
    runtime.put_job(job)
    try:
        from app.adapters.simulation.simpy_simulator import SimPySimulator
        result = SimPySimulator().simulate(body)
        runtime.put_simulation(result)
        final_plans = [p for p in runtime.plans.values() if p.snapshot_id == result.final_snapshot.snapshot_id]
        if final_plans:
            job.plan_id = max(final_plans, key=lambda p: (p.snapshot_version, p.version)).plan_id
        job.status = "succeeded"
        response = SimulationAccepted(simulation_id=result.simulation_id, job_id=job.job_id)
    except Exception as exc:
        job.status = "failed"
        job.error_code = str(exc)
        # Preserve accepted contract: caller can inspect the job for failure details.
        simulation_id = f"sim_{uuid4().hex[:20]}"
        response = SimulationAccepted(simulation_id=simulation_id, job_id=job.job_id)
    runtime.idempotency[key] = {"response": response.model_dump(mode="json")}
    return response

def get_simulation(simulation_id: str):
    return SimulationResponse(simulation=runtime.get_simulation(simulation_id))
def get_evidence(run_id): raise FeatureNotImplemented("get_evidence", "AC")

def _snapshot_from_result(result):
    """Retrieve the derived snapshot already produced by the B-04 handler."""
    return runtime.get_snapshot(result.replanned_plan.snapshot_id, result.replanned_plan.snapshot_version)


def _build_candidate_plan(snapshot, body):
    from app.application.coordinator import coordinate
    return coordinate(
        snapshot=snapshot,
        order_ids=tuple(body.order_ids),
        budget_ms=int(body.budget_ms),
        max_coordination_rounds=int(body.max_coordination_rounds),
        coordination_mode=body.coordination_mode,
    )
