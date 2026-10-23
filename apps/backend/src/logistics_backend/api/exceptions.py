"""Exception projection API (P14 subset)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query, Request

from logistics_backend.api.dependencies import actor, operator
from logistics_backend.application.exceptions import ExceptionService
from logistics_contracts.events import ExceptionCreate, ExceptionEventView, ExceptionPage
from logistics_domain.runtime import ActorContext

router = APIRouter(tags=["exceptions"])


def exception_service(request: Request) -> ExceptionService:
    return request.app.state.exceptions


@router.post("/exceptions", response_model=ExceptionEventView, status_code=201,
             operation_id="record_exception")
def record_exception(command: ExceptionCreate, current: ActorContext = Depends(operator),
                     service: ExceptionService = Depends(exception_service)):
    return service.record(command, current)


@router.get("/exceptions", response_model=ExceptionPage, operation_id="list_exceptions")
def list_exceptions(current: ActorContext = Depends(actor),
                    service: ExceptionService = Depends(exception_service),
                    limit: int = Query(default=50, ge=1, le=200)):
    return ExceptionPage(items=service.list(current, limit))
