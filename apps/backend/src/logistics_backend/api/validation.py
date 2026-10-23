"""Synchronous independent validation API (P10 subset)."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from logistics_backend.api.dependencies import actor
from logistics_contracts.planning import ValidationReportDTO
from logistics_contracts.validation import (
    TransportValidationRequest,
    WarehouseValidationRequest,
)
from logistics_domain.runtime import ActorContext
from logistics_optimization.validation.transport import validate_transport
from logistics_optimization.validation.warehouse import validate_warehouse

router = APIRouter(tags=["validation"])


@router.post("/validations/transport", response_model=ValidationReportDTO,
             operation_id="validate_transport_plan")
def validate_transport_plan(command: TransportValidationRequest,
                            current: ActorContext = Depends(actor)):
    problem = command.problem.to_domain()
    plan = command.plan.to_domain()
    stops = tuple(stop.to_domain() for stop in command.stops)
    return validate_transport(plan, problem, stops)


@router.post("/validations/warehouse", response_model=ValidationReportDTO,
             operation_id="validate_warehouse_solution")
def validate_warehouse_solution(command: WarehouseValidationRequest,
                                current: ActorContext = Depends(actor)):
    problem = command.problem.to_domain()
    solution = command.solution.to_domain()
    return validate_warehouse(problem, solution)
