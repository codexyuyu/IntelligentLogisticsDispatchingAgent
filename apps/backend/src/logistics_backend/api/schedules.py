"""Schedule create/list API (P16 subset)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query, Request

from logistics_backend.api.dependencies import actor, operator
from logistics_backend.application.schedule import ScheduleService
from logistics_contracts.schedules import ScheduleCreate, SchedulePage, ScheduleView
from logistics_domain.runtime import ActorContext

router = APIRouter(tags=["schedules"])


def schedule_service(request: Request) -> ScheduleService:
    return request.app.state.schedules


@router.post("/schedules", response_model=ScheduleView, status_code=201,
             operation_id="create_schedule")
def create_schedule(command: ScheduleCreate, current: ActorContext = Depends(operator),
                    service: ScheduleService = Depends(schedule_service)):
    return service.create(command, current)


@router.get("/schedules", response_model=SchedulePage, operation_id="list_schedules")
def list_schedules(current: ActorContext = Depends(actor),
                   service: ScheduleService = Depends(schedule_service),
                   limit: int = Query(default=50, ge=1, le=200)):
    return service.list(current, limit)
