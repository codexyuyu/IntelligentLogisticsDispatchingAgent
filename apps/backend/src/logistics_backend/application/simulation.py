"""Simulation submission/result service and durable-job handler (P11/P16 subset)."""

from __future__ import annotations

import json
from uuid import UUID, uuid4

from logistics_backend.application.artifacts import ResultArtifactStore, TypedResultStore
from logistics_backend.application.submission import submit_job
from logistics_contracts.mapping import simulation_result_dto
from logistics_contracts.simulation import SimulationRequestDTO, SimulationResultDTO
from logistics_domain.errors import InvalidInputError
from logistics_domain.states import JobKind
from logistics_simulation.engine import SimPySimulationEngine


class SimulationJobHandler:
    family = JobKind.SIMULATION

    def __init__(self, result_store: ResultArtifactStore | None = None):
        self.result_store = result_store or ResultArtifactStore()

    def validate(self, content: bytes) -> None:
        try:
            SimulationRequestDTO.model_validate_json(content).to_domain()
        except Exception as exc:
            raise InvalidInputError("simulation job content is not a valid request") from exc

    def execute(self, content: bytes, deadline):
        from logistics_contracts.runtime import JobResultRef

        request = SimulationRequestDTO.model_validate_json(content).to_domain()
        result = SimPySimulationEngine().run(request)
        result_id = uuid4()
        digest = self.result_store.write(result_id, json.loads(
            simulation_result_dto(result).model_dump_json()))
        return JobResultRef(result_id=result_id, version=1, schema_version="2.0.0",
                            hash=digest, family=JobKind.SIMULATION)


class SimulationResultStore(TypedResultStore):
    result_type = SimulationResultDTO


class SimulationService:
    def __init__(self, job_service):
        self.job_service = job_service

    def submit(self, request: SimulationRequestDTO, actor, key: str, trace_id: UUID):
        request.to_domain()
        return submit_job(self.job_service, request, actor, key, trace_id,
                          kind=JobKind.SIMULATION,
                          build_content=lambda: request.model_dump(mode="json"))
