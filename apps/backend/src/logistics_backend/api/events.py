"""Event ingestion and query API (P13-02 subset)."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, Request

from logistics_backend.api.dependencies import actor, operator
from logistics_backend.application.events import EventService
from logistics_contracts.events import EventEnvelopeDTO, EventReceiptDTO, EventViewDTO
from logistics_domain.runtime import ActorContext

router = APIRouter(tags=["events"])


def event_service(request: Request) -> EventService:
    return request.app.state.events


@router.post("/events", response_model=EventReceiptDTO, status_code=202,
             operation_id="ingest_event")
def ingest_event(request: Request, command: EventEnvelopeDTO,
                 current: ActorContext = Depends(operator),
                 service: EventService = Depends(event_service)):
    return service.ingest(command, current, request.state.trace_id)


@router.get("/events/{event_id}", response_model=EventViewDTO, operation_id="get_event")
def get_event(event_id: UUID, current: ActorContext = Depends(actor),
              service: EventService = Depends(event_service)):
    return service.get(event_id, current)
