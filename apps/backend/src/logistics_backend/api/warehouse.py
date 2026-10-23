"""Warehouse optimization submission API (P16-01 subset)."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, Header, Request

from logistics_backend.api.dependencies import operator
from logistics_backend.application.warehouse import WarehouseOptimizationService
from logistics_contracts.runtime import JobRef
from logistics_contracts.warehouse import WarehouseRequestDTO
from logistics_domain.runtime import ActorContext

router = APIRouter(tags=["optimization"])


def warehouse_service(request: Request) -> WarehouseOptimizationService:
    return request.app.state.warehouse


@router.post("/optimizations/warehouse", response_model=JobRef, status_code=202,
             operation_id="submit_warehouse_optimization")
def submit_warehouse(request: Request, command: WarehouseRequestDTO,
                     idempotency_key: str = Header(alias="Idempotency-Key"),
                     current: ActorContext = Depends(operator),
                     service: WarehouseOptimizationService = Depends(warehouse_service)):
    return service.submit(command, current, idempotency_key, request.state.trace_id)
