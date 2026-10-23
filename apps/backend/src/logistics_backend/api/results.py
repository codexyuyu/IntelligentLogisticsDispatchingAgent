"""Typed job result query API (P16); never a placeholder."""

from __future__ import annotations

from typing import Annotated, Literal, TypeAlias
from uuid import UUID

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel, ConfigDict, Field, ValidationError

from logistics_backend.api.dependencies import actor, job_service
from logistics_contracts.simulation import SimulationResultDTO
from logistics_contracts.transport import TransportSolutionDTO
from logistics_contracts.warehouse import WarehouseSolutionDTO
from logistics_domain.runtime import ActorContext

router = APIRouter(tags=["jobs"])


class TransportResultView(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    kind: Literal["transport"]
    value: TransportSolutionDTO


class WarehouseResultView(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    kind: Literal["warehouse"]
    value: WarehouseSolutionDTO


class SimulationResultView(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    kind: Literal["simulation"]
    value: SimulationResultDTO


JobResultView: TypeAlias = Annotated[
    TransportResultView | WarehouseResultView | SimulationResultView,
    Field(discriminator="kind")]


def transport_results(request: Request):
    return request.app.state.results


def warehouse_results(request: Request):
    return request.app.state.warehouse_results


def simulation_results(request: Request):
    return request.app.state.simulation_results


@router.get("/jobs/{job_id}/result", response_model=JobResultView,
            operation_id="get_job_result")
def get_job_result(job_id: UUID, current: ActorContext = Depends(actor),
                   service=Depends(job_service), transport=Depends(transport_results),
                   warehouse=Depends(warehouse_results),
                   simulation=Depends(simulation_results)):
    job = service.get(job_id, current)
    try:
        return {"kind": "transport", "value": transport.read(job)}
    except ValidationError:
        try:
            return {"kind": "warehouse", "value": warehouse.read(job)}
        except ValidationError:
            return {"kind": "simulation", "value": simulation.read(job)}
