"""Idempotency receipts for commit and other mutating operations (P03-04).

``(scope_id, actor_id, operation, key)`` is the storage key. The same key with the same
request hash returns the previously stored receipt; a different hash is a typed
``IDEMPOTENCY_CONFLICT`` and writes nothing else.
"""

from __future__ import annotations

import json
from datetime import datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert

from logistics_backend.application.master_data import ServiceError
from logistics_backend.persistence.runtime_models import idempotency
from logistics_contracts.runtime import JobRef
from logistics_domain.states import ErrorCode


class IdempotencyStore:
    def lookup(self, connection, *, scope_id: UUID, actor_id: UUID, operation: str, key: str):
        return connection.execute(select(idempotency).where(
            idempotency.c.scope_id == scope_id, idempotency.c.actor_id == actor_id,
            idempotency.c.operation == operation, idempotency.c.key == key)).mappings().first()

    def register(self, connection, *, scope_id: UUID, actor_id: UUID, operation: str, key: str,
                 request_hash: str, receipt: dict, expires_at: datetime):
        if not key or len(key) > 256:
            raise ServiceError(ErrorCode.INVALID_INPUT, "invalid idempotency key")
        result = connection.execute(pg_insert(idempotency).values(
            scope_id=scope_id, actor_id=actor_id, operation=operation, key=key,
            request_hash=request_hash, receipt=receipt, expires_at=expires_at)
            .on_conflict_do_nothing())
        if result.rowcount == 1:
            return receipt
        prior = self.lookup(connection, scope_id=scope_id, actor_id=actor_id,
                            operation=operation, key=key)
        if prior is None:
            raise ServiceError(ErrorCode.RESOURCE_CONFLICT, "idempotency race could not be resolved")
        if prior["request_hash"] != request_hash:
            raise ServiceError(ErrorCode.IDEMPOTENCY_CONFLICT,
                               "idempotency key was used with a different request")
        return prior["receipt"]


def job_receipt(value: JobRef) -> dict:
    """Stored receipt projection used by the durable-job enqueue path."""
    return json.loads(value.model_dump_json())


__all__ = ["IdempotencyStore", "job_receipt"]
