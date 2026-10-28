"""One durable submission path; idempotency describes user input, not generated IDs."""
import hashlib
from datetime import UTC, datetime, timedelta
from uuid import uuid4

from logistics_backend.application.artifacts import canonical_bytes
from logistics_contracts.runtime import (
    JobRequest,
    OptimizationJobPayload,
    RequestRef,
    SimulationJobPayload,
)
from logistics_domain.planning import content_hash
from logistics_domain.states import JobKind


def submit_job(jobs, request, actor, key, trace_id, *, kind, build_content, mode=None, connection=None):
    operation = f"submit:{kind.value}:{mode.value if mode else 'default'}"
    input_hash = content_hash(request.model_dump(mode="json"))

    def prepare():
        content = canonical_bytes(build_content())
        reference = RequestRef(request_id=uuid4(), version=1, schema_version="2.0.0",
                               hash=hashlib.sha256(content).hexdigest(), family=kind)
        if kind == JobKind.OPTIMIZATION:
            payload = OptimizationJobPayload(family="optimization", request_ref=reference, mode=mode)
        else:
            payload = SimulationJobPayload(family="simulation", request_ref=reference)
        command = JobRequest(schema_version="2.0.0", kind=kind, payload=payload,
                             deadline_utc=datetime.now(UTC).replace(microsecond=0) + timedelta(seconds=55))
        return command, content

    return jobs.submit_prepared(actor, key, trace_id, operation, input_hash, prepare,
                               connection=connection)
