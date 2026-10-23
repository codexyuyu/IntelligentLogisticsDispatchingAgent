"""Synchronous independent validation API (P10 subset)."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from logistics_backend.api.dependencies import actor
from logistics_contracts.planning import ValidationReportDTO
from logistics_contracts.validation import (
    JointValidationRequest,
    TransportValidationRequest,
    WarehouseValidationRequest,
)
from logistics_domain.runtime import ActorContext
from logistics_optimization.validation.joint import validate_joint
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


@router.post("/validations/joint", response_model=ValidationReportDTO,
             operation_id="validate_joint_plan")
def validate_joint_plan(command: JointValidationRequest,
                        current: ActorContext = Depends(actor)):
    transport = command.transport
    warehouse = command.warehouse
    return validate_joint(transport.plan.to_domain(), transport.problem.to_domain(),
        tuple(stop.to_domain() for stop in transport.stops),
        warehouse.problem.to_domain(), warehouse.solution.to_domain())
