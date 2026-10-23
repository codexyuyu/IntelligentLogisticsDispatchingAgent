"""Immutable result artifact store shared by job handlers and result queries."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from uuid import UUID

from logistics_backend.errors import ServiceError
from logistics_domain.states import ErrorCode

RESULT_DIR = Path("artifacts/results")


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


__all__ = ["RESULT_DIR", "ResultArtifactStore", "canonical_bytes"]
