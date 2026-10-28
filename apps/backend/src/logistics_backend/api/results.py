"""Typed job result query API (P16); never a placeholder."""

from __future__ import annotations

import json
from typing import Annotated, Any, Literal, TypeAlias
from uuid import UUID

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel, ConfigDict, Field

from logistics_backend.api.dependencies import actor, job_service
from logistics_backend.application.artifacts import ResultArtifactStore
from logistics_backend.errors import ServiceError
from logistics_contracts.simulation import SimulationResultDTO
from logistics_contracts.transport import TransportSolutionDTO
from logistics_contracts.warehouse import WarehouseSolutionDTO
from logistics_domain.runtime import ActorContext
from logistics_domain.states import ErrorCode, JobStatus

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


class JointResultView(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    kind: Literal["joint"]
    value: dict[str, Any]


JobResultView: TypeAlias = Annotated[
    TransportResultView | WarehouseResultView | SimulationResultView | JointResultView,
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
    kind = service.result_kind(job_id, current)
    if kind == "joint":
        if job.status != JobStatus.COMPLETED or job.result_ref is None:
            raise ServiceError(ErrorCode.RESULT_NOT_READY, "job result is not ready")
        value = json.loads(ResultArtifactStore().read(job.result_ref.result_id, job.result_ref.hash))
    else:
        stores = {"transport": transport, "warehouse": warehouse, "simulation": simulation}
        if kind not in stores:
            raise ServiceError(ErrorCode.INVALID_INPUT, "result kind is not supported")
        value = stores[kind].read(job)
    return {"kind": kind, "value": value}
