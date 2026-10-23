"""Schedule create/list API (P16 subset)."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request

from logistics_backend.api.dependencies import actor, operator
from logistics_backend.application.schedule import ScheduleService
from logistics_contracts.planning import CommitReceiptDTO
from logistics_contracts.schedules import (
    CandidateCreate,
    CandidateView,
    CommitRequest,
    ScheduleCreate,
    ScheduleDiffView,
    SchedulePage,
    ScheduleVersionDetailView,
    ScheduleVersionPage,
    ScheduleView,
)
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


@router.get("/schedules/{schedule_id}/versions", response_model=ScheduleVersionPage,
            operation_id="list_schedule_versions")
def list_schedule_versions(schedule_id: UUID, current: ActorContext = Depends(actor),
                           service: ScheduleService = Depends(schedule_service),
                           limit: int = Query(default=50, ge=1, le=200)):
    return service.versions(schedule_id, current, limit)


@router.get("/schedules/{schedule_id}/versions/current",
            response_model=ScheduleVersionDetailView,
            operation_id="get_current_schedule_version")
def get_current_schedule_version(schedule_id: UUID, current: ActorContext = Depends(actor),
                                 service: ScheduleService = Depends(schedule_service)):
    return service.current_version(schedule_id, current)


@router.get("/schedules/{schedule_id}/versions/{version_id}",
            response_model=ScheduleVersionDetailView,
            operation_id="get_schedule_version")
def get_schedule_version(schedule_id: UUID, version_id: UUID,
                         current: ActorContext = Depends(actor),
                         service: ScheduleService = Depends(schedule_service)):
    return service.version_detail(schedule_id, version_id, current)


@router.get("/schedules/{schedule_id}/versions/{base_version_id}/diff/{candidate_version_id}",
            response_model=ScheduleDiffView, operation_id="diff_schedule_versions")
def diff_schedule_versions(schedule_id: UUID, base_version_id: UUID,
                           candidate_version_id: UUID,
                           current: ActorContext = Depends(actor),
                           service: ScheduleService = Depends(schedule_service)):
    return service.diff(schedule_id, base_version_id, candidate_version_id, current)


@router.post("/schedules/{schedule_id}/candidates", response_model=CandidateView,
             status_code=201, operation_id="create_candidate")
def create_candidate(schedule_id: UUID, command: CandidateCreate,
                     current: ActorContext = Depends(operator),
                     service: ScheduleService = Depends(schedule_service)):
    return service.create_candidate(schedule_id, command, current)


@router.post("/schedules/{schedule_id}/versions/commit",
             response_model=CommitReceiptDTO, operation_id="commit_schedule_version")
def commit_schedule_version(schedule_id: UUID, request: Request, command: CommitRequest,
                            current: ActorContext = Depends(operator),
                            service: ScheduleService = Depends(schedule_service)):
    return service.commit(schedule_id, command, current, request.state.trace_id)
