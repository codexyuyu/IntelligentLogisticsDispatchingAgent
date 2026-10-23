"""Focused unit coverage for the P10/P14/P15/P32/P33 pure services.

These tests do not touch PostgreSQL or the network. They exercise the same domain objects and
DTO projections the HTTP layer uses, so the new impact/reschedule/metrics/comparison code is
not left as smoke-only.
"""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

from logistics_backend.application.impact import ImpactService
from logistics_backend.application.reschedule import RescheduleService
from logistics_contracts.events import EventEnvelopeDTO
from logistics_contracts.impact import ImpactRequestDTO
from logistics_contracts.mapping import plan_dto, route_stop_dto
from logistics_contracts.reschedule import ReschedulePolicyDTO, RescheduleProposalRequest
from logistics_domain.planning import (
    CostBreakdown,
    MatrixRef,
    Route,
    RouteStop,
    TransportPlan,
)
from logistics_domain.primitives import Load
from logistics_domain.simulation import (
    SimulationEvent,
    SimulationEventKind,
    SimulationResult,
    SimulationStatus,
)
from logistics_domain.states import EntityState
from logistics_evaluation.metrics import (
    compare_metrics,
    simulation_metrics,
    transport_plan_metrics,
)

EPOCH = datetime(2026, 1, 1, tzinfo=timezone.utc)


def _plan(order_id):
    cost = CostBreakdown(1000, 500, 300, 0, 0, 1800)
    route = Route(id=uuid4(), status=EntityState.CANDIDATE, created_at=EPOCH,
        updated_at=EPOCH, row_version=0, schema_version="2.0.0", created_by=uuid4(),
        version_id=uuid4(), vehicle_id=uuid4(), driver_id=uuid4(),
        start_node_id=uuid4(), end_node_id=uuid4(), total_distance_m=5000,
        cost=cost, matrix_ref=MatrixRef(uuid4(), 1, "a" * 64))
    stop = RouteStop(id=uuid4(), status=EntityState.PLANNED, created_at=EPOCH,
        updated_at=EPOCH, row_version=0, schema_version="2.0.0", created_by=uuid4(),
        route_id=route.id, sequence=0, node_id=uuid4(), task_ids=(order_id,),
        arrival_s=10, service_start_s=10, departure_s=20,
        load_before=Load(0, 0), load_after=Load(10, 0))
    plan = TransportPlan(routes=(route,), unserved_order_ids=(), cost=cost)
    return plan, stop


def _envelope(order_id):
    return EventEnvelopeDTO.model_validate({
        "schema_version": "2.0.0", "source": "unit", "source_event_id": "evt-unit-1",
        "kind": "order_cancellation", "occurred_at_utc": EPOCH.isoformat(),
        "simulation_id": None, "payload": {
            "kind": "order_cancellation",
            "entity_ref": {"kind": "order", "id": str(order_id), "revision": None},
            "effective_at_s": 0, "reason": "cancelled", "order_id": str(order_id),
            "disposition_policy": "return_to_origin",
        }})


def _impact_request(order_id):
    plan, stop = _plan(order_id)
    return ImpactRequestDTO(event=_envelope(order_id), plan=plan_dto(plan),
        stops=(route_stop_dto(stop),), event_time_s=15)


def test_impact_closure_marks_interrupted_and_mutable_tasks():
    order_id = uuid4()
    analysis = ImpactService().analyse(_impact_request(order_id))
    assert analysis.report.affected_orders == (order_id,)
    assert analysis.report.affected_tasks == (order_id,)
    assert analysis.boundary.interrupted_task_ids == (order_id,)
    assert analysis.boundary.mutable_task_ids == (order_id,)
    assert analysis.boundary.frozen_task_ids == ()


def test_reschedule_proposal_is_typed_and_does_not_claim_completion():
    order_id = uuid4()
    request = RescheduleProposalRequest(
        impact=_impact_request(order_id),
        policy=ReschedulePolicyDTO(max_extra_delay_s=300, allow_scope_expansion=False))
    proposal = RescheduleService().propose(request)
    assert proposal.requires_manual_review is False
    assert len(proposal.adjustments) == 2
    assert {item.strategy.value for item in proposal.adjustments} == {
        "rescue_handoff", "defer"}


def test_transport_metrics_keep_missing_values_explicit():
    order_id = uuid4()
    plan, _ = _plan(order_id)
    plan = TransportPlan(routes=plan.routes, unserved_order_ids=(uuid4(),), cost=plan.cost)
    values = {item.code: item for item in transport_plan_metrics(plan, 2, 1)}
    assert values["delivery_rate"].value == 0.5
    assert values["total_distance_m"].value == 5000
    assert values["changed_tasks"].value is None
    assert values["changed_tasks"].reason.value == "not_applicable"


def test_simulation_comparison_returns_signed_deltas():
    order_id = uuid4()
    event = SimulationEvent(uuid4(), 1, SimulationEventKind.DELIVERED, None, order_id, None)
    base = SimulationResult(SimulationStatus.COMPLETED, 100, (event,), (order_id,), 0)
    candidate = SimulationResult(SimulationStatus.COMPLETED, 80, (), (), 0)
    comparison = compare_metrics("base", "candidate",
        simulation_metrics(base, 2), simulation_metrics(candidate, 2))
    deltas = {item.code: item for item in comparison.deltas}
    assert deltas["simulated_delivered_orders"].delta == -1
    assert deltas["simulated_delivery_rate"].delta == -0.5
    assert deltas["simulation_final_time_s"].delta == -20
