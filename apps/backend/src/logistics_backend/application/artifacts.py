"""Immutable result artifact store shared by job handlers and result queries."""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
from uuid import UUID

from logistics_backend.errors import ServiceError
from logistics_domain.states import ErrorCode

# Default stays cwd-relative so existing deployments and pytest keep their
# current behaviour. Multi-copy / multi-process setups must point both the
# backend and the worker at the same absolute directory through this variable,
# otherwise a completed job's artifact is invisible to the API process.
RESULT_DIR = Path(os.environ.get("LOGISTICS_RESULTS_DIR", "artifacts/results")).expanduser()


def canonical_bytes(value) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True,
                      separators=(",", ":")).encode("utf-8")


class ResultArtifactStore:
    def __init__(self, directory: Path = RESULT_DIR):
        self.directory = directory

    def write(self, result_id: UUID, value) -> str:
        payload = canonical_bytes(value)
        self.directory.mkdir(parents=True, exist_ok=True)
        path = self.directory / f"{result_id}.json"
        temporary = path.with_suffix(".tmp")
        temporary.write_bytes(payload)
        temporary.replace(path)
        return hashlib.sha256(payload).hexdigest()

    def read(self, result_id: UUID, expected_hash: str) -> bytes:
        path = self.directory / f"{result_id}.json"
        if not path.is_file():
            raise ServiceError(ErrorCode.RESULT_NOT_READY, "job result artifact is unavailable")
        payload = path.read_bytes()
        if hashlib.sha256(payload).hexdigest() != expected_hash:
            raise ServiceError(ErrorCode.UNVERIFIED_SOLVER_RESULT, "result hash mismatch")
        return payload


class TypedResultStore:
    """Common readiness and integrity boundary; subclasses specify only their DTO."""
    result_type = None

    def __init__(self, result_store: ResultArtifactStore | None = None):
        self.result_store = result_store or ResultArtifactStore()

    def read(self, job):
        from logistics_domain.states import JobStatus
        if job.status != JobStatus.COMPLETED or job.result_ref is None:
            raise ServiceError(ErrorCode.RESULT_NOT_READY, "job result is not ready")
        payload = self.result_store.read(job.result_ref.result_id, job.result_ref.hash)
        return self.result_type.model_validate_json(payload)


__all__ = ["RESULT_DIR", "ResultArtifactStore", "canonical_bytes"]
