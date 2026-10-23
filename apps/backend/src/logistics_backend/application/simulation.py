"""Simulation submission/result service and durable-job handler (P11/P16 subset)."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timedelta, timezone
from uuid import UUID, uuid4

from logistics_backend.application.artifacts import ResultArtifactStore, canonical_bytes
from logistics_contracts.mapping import simulation_request_dto, simulation_result_dto
from logistics_contracts.runtime import (
    JobRequest,
    SimulationJobPayload,
    RequestRef as RequestRefDTO,
)
from logistics_contracts.simulation import SimulationRequestDTO, SimulationResultDTO
from logistics_domain.errors import InvalidInputError
from logistics_domain.runtime import RequestRef
from logistics_domain.states import JobKind
from logistics_simulation.engine import SimPySimulationEngine


def _now() -> datetime:
    return datetime.now(timezone.utc).replace(microsecond=0)


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


class SimulationResultStore:
    def __init__(self, result_store: ResultArtifactStore | None = None):
        self.result_store = result_store or ResultArtifactStore()

    def read(self, job) -> SimulationResultDTO:
        from logistics_backend.errors import ServiceError
        from logistics_domain.states import ErrorCode, JobStatus

        if job.status != JobStatus.COMPLETED or job.result_ref is None:
            raise ServiceError(ErrorCode.RESULT_NOT_READY, "job result is not ready")
        payload = self.result_store.read(job.result_ref.result_id, job.result_ref.hash)
        return SimulationResultDTO.model_validate_json(payload)


class SimulationService:
    def __init__(self, job_service):
        self.job_service = job_service

    def submit(self, request: SimulationRequestDTO, actor, key: str, trace_id: UUID):
        request.to_domain()
        content = canonical_bytes(json.loads(request.model_dump_json()))
        request_id, version = uuid4(), 1
        digest = hashlib.sha256(content).hexdigest()
        reference = RequestRef(request_id=request_id, version=version, schema_version="2.0.0",
                               hash=digest, family=JobKind.SIMULATION)
        self.job_service.store_request(reference, content, actor)
        command = JobRequest(schema_version="2.0.0", kind=JobKind.SIMULATION,
            payload=SimulationJobPayload(family="simulation",
                request_ref=RequestRefDTO(request_id=request_id, version=version,
                    schema_version="2.0.0", hash=digest, family=JobKind.SIMULATION)),
            deadline_utc=_now() + timedelta(seconds=55))
        return self.job_service.submit(command, actor, key, trace_id)
