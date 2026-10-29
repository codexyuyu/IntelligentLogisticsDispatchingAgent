"""Warehouse optimization submission API (P16-01 subset)."""

from __future__ import annotations

from typing import Annotated, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, Header, Query, Request

from logistics_backend.api.dependencies import actor, operator
from logistics_backend.application.warehouse import WarehouseOptimizationService
from logistics_backend.application.warehouse_execution import InventoryView, TaskTransition, WarehouseTaskList
from logistics_contracts.planning import WarehouseTaskDTO
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


@router.get("/warehouses/{warehouse_id}/tasks", response_model=WarehouseTaskList,
            operation_id="list_warehouse_execution_tasks", tags=["warehouse-execution"])
def list_warehouse_tasks(warehouse_id: UUID, request: Request,
                         current: Annotated[ActorContext, Depends(actor)],
                         status: Literal["pending", "ready", "running", "completed",
                                         "cancelled", "interrupted", "failed"] | None = None,
                         order_id: UUID | None = None,
                         limit: int = Query(default=100, ge=1, le=500)):
    return request.app.state.warehouse_execution.tasks(
        warehouse_id, current, status=status, order_id=order_id, limit=limit)


@router.post("/warehouses/{warehouse_id}/tasks/{task_id}/transitions",
             response_model=WarehouseTaskDTO, operation_id="advance_warehouse_execution_task",
             tags=["warehouse-execution"])
def transition_warehouse_task(warehouse_id: UUID, task_id: UUID,
                              command: TaskTransition, request: Request,
                              current: Annotated[ActorContext, Depends(operator)]):
    return request.app.state.warehouse_execution.transition(
        warehouse_id, task_id, command, current)


@router.get("/inventory", response_model=InventoryView, operation_id="get_inventory_ledger",
            tags=["warehouse-execution"])
def get_inventory(request: Request, current: Annotated[ActorContext, Depends(actor)],
                  cargo_id: UUID | None = None, location_id: UUID | None = None,
                  limit: int = Query(default=100, ge=1, le=500)):
    return request.app.state.warehouse_execution.inventory(
        current, cargo_id=cargo_id, location_id=location_id, limit=limit)
