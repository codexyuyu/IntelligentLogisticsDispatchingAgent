"""Local reschedule proposal service (P15-01 subset), no solver claim."""

from __future__ import annotations

from uuid import uuid4

from logistics_backend.application.impact import ImpactService
from logistics_contracts.mapping import reschedule_proposal_dto
from logistics_contracts.reschedule import RescheduleProposalRequest
from logistics_domain.planning import content_hash
from logistics_domain.reschedule import (
    AdjustmentSpec,
    RescheduleProposal,
    RescheduleStrategy,
)


class RescheduleService:
    def __init__(self, impact: ImpactService | None = None):
        self.impact = impact or ImpactService()

    def propose(self, request: RescheduleProposalRequest):
        analysis = self.impact.analyse(request.impact)
        boundary = request.impact.event_time_s
        policy = request.policy.to_domain()
        plan = request.impact.plan.to_domain()
        stops = tuple(stop.to_domain() for stop in request.impact.stops)
        adjustments: list[AdjustmentSpec] = []
        for task_id in analysis.boundary.interrupted_task_ids:
            adjustments.append(AdjustmentSpec(task_id=task_id,
                strategy=RescheduleStrategy.RESCUE_HANDOFF,
                earliest_start_s=boundary,
                note="in-transit task; preserve completed segment and require handoff"))
        for task_id in analysis.boundary.mutable_task_ids:
            adjustments.append(AdjustmentSpec(task_id=task_id,
                strategy=RescheduleStrategy.DEFER,
                earliest_start_s=boundary + min(policy.max_extra_delay_s, 60),
                note="future task may be deferred within the policy bound"))
        manual = not adjustments
        proposal = RescheduleProposal(id=uuid4(),
            base_plan_hash=content_hash({"plan": plan, "stops": stops}),
            event_time_s=boundary, adjustments=tuple(adjustments),
            requires_manual_review=manual,
            rationale=("no safe automatic adjustment; manual review required" if manual
                       else "typed adjustments only; solver and validator must run before commit"))
        return reschedule_proposal_dto(proposal)
