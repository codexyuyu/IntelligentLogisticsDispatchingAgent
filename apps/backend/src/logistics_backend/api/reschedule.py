"""Local reschedule proposal API (P15-01 subset) + 车辆延误处置审批端点。"""

from __future__ import annotations

from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel, ConfigDict, Field

from logistics_backend.api.dependencies import operator
from logistics_backend.application.reschedule import RescheduleService
from logistics_backend.application.vehicle_delay_approval import (
    VehicleDelayApprovalService,
)
from logistics_contracts.reschedule import RescheduleProposalDTO, RescheduleProposalRequest
from logistics_domain.runtime import ActorContext

router = APIRouter(tags=["reschedule"])


def reschedule_service() -> RescheduleService:
    return RescheduleService()


def vehicle_delay_service(request: Request) -> VehicleDelayApprovalService:
    return request.app.state.vehicle_delay


class VehicleDelayApproveRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    expected_active_version_id: UUID | None = None


@router.post("/reschedules/proposals", response_model=RescheduleProposalDTO,
             operation_id="propose_reschedule")
def propose_reschedule(command: RescheduleProposalRequest,
                       current: ActorContext = Depends(operator),
                       service: RescheduleService = Depends(reschedule_service)):
    return service.propose(command)


class VehicleDelayFromEventRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    event_id: UUID
    schedule_id: UUID
    budget_ms: int = Field(default=4000, ge=100, le=12000)


@router.post("/reschedules/vehicle-delay/from-event",
             operation_id="prepare_vehicle_delay_from_event")
def prepare_vehicle_delay_from_event(command: VehicleDelayFromEventRequest,
                                     request: Request,
                                     current: ActorContext = Depends(operator),
                                     service: VehicleDelayApprovalService = Depends(vehicle_delay_service)):
    """事件驱动入口：读取持久化事件，基于已批准基线重解并生成待审决策。"""

    def read_event(event_id: UUID, actor: ActorContext) -> dict:
        return request.app.state.events.payload(event_id, actor)

    return service.prepare_from_event(actor=current, event_id=command.event_id,
                                      schedule_id=command.schedule_id,
                                      read_event=read_event, budget_ms=command.budget_ms)


@router.post("/reschedules/vehicle-delay/decisions/{decision_id}/approve",
             operation_id="approve_vehicle_delay_decision")
def approve_vehicle_delay(decision_id: UUID,
                          command: VehicleDelayApproveRequest | None = None,
                          current: ActorContext = Depends(operator),
                          service: VehicleDelayApprovalService = Depends(vehicle_delay_service)):
    """人工批准：提交新版本。未批准前不会产生任何版本。"""

    return service.approve(actor=current, decision_id=decision_id, trace_id=uuid4(),
                           expected_active_version_id=(command.expected_active_version_id
                                                       if command else None))


@router.post("/reschedules/vehicle-delay/decisions/{decision_id}/reject",
             operation_id="reject_vehicle_delay_decision")
def reject_vehicle_delay(decision_id: UUID,
                         current: ActorContext = Depends(operator),
                         service: VehicleDelayApprovalService = Depends(vehicle_delay_service)):
    """人工拒绝：只关闭决策，不提交版本。"""

    return service.reject(actor=current, decision_id=decision_id)


@router.get("/reschedules/vehicle-delay/base-plan/{schedule_id}",
            operation_id="get_vehicle_delay_base_plan")
def read_vehicle_delay_base_plan(schedule_id: UUID,
                                 current: ActorContext = Depends(operator),
                                 service: VehicleDelayApprovalService = Depends(vehicle_delay_service)):
    """读取该排程最近一次已批准处置方案，作为下一次局部重解的基线。"""

    plan, stops = service.load_base_plan(actor=current, schedule_id=schedule_id)
    return {
        "schedule_id": str(schedule_id),
        "routes": len(plan.routes),
        "stops": len(stops),
        "cost_total_cents": plan.cost.total_cents,
        "unserved_order_ids": [str(o) for o in plan.unserved_order_ids],
    }
