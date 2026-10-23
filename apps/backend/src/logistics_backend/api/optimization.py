"""Transport optimization submission API (P16-01)."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, Header, Request

from logistics_backend.api.dependencies import operator
from logistics_contracts.runtime import JobRef
from logistics_contracts.transport import TransportRequestDTO
from logistics_domain.runtime import ActorContext
from logistics_backend.application.optimization import TransportOptimizationService

router = APIRouter(tags=["optimization"])


def transport_service(request: Request) -> TransportOptimizationService:
    return request.app.state.transport


@router.post("/optimizations/transport", response_model=JobRef, status_code=202,
             operation_id="submit_transport_optimization")
def submit_transport(request: Request, command: TransportRequestDTO,
                     idempotency_key: str = Header(alias="Idempotency-Key"),
                     current: ActorContext = Depends(operator),
                     service: TransportOptimizationService = Depends(transport_service)):
    trace_id: UUID = request.state.trace_id
    return service.submit(command, current, idempotency_key, trace_id)
