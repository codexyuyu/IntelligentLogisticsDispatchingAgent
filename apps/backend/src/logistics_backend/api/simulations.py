"""Simulation submission API (P16-04 subset)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Header, Request

from logistics_backend.api.dependencies import operator
from logistics_backend.application.simulation import SimulationService
from logistics_contracts.runtime import JobRef
from logistics_contracts.simulation import SimulationRequestDTO
from logistics_domain.runtime import ActorContext

router = APIRouter(tags=["simulations"])


def simulation_service(request: Request) -> SimulationService:
    return request.app.state.simulations


@router.post("/simulations", response_model=JobRef, status_code=202,
             operation_id="submit_simulation")
def submit_simulation(request: Request, command: SimulationRequestDTO,
                      idempotency_key: str = Header(alias="Idempotency-Key"),
                      current: ActorContext = Depends(operator),
                      service: SimulationService = Depends(simulation_service)):
    return service.submit(command, current, idempotency_key, request.state.trace_id)
