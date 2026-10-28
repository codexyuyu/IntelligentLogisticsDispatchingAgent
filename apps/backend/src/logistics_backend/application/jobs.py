"""Job orchestration protocols. Implementations are injected by bootstrap."""
from dataclasses import dataclass
from datetime import datetime
from typing import Literal, Protocol, TypeAlias
from uuid import UUID

from logistics_backend.errors import ServiceError
from logistics_contracts.runtime import JobRequest, JobResultRef
from logistics_domain.states import ErrorCode, JobKind, JobOptimizationMode


@dataclass(frozen=True)
class LeaseToken:
    job_id: UUID
    owner_id: UUID
    epoch: int
    expires_at: datetime

@dataclass(frozen=True)
class Deadline:
    expires_at_utc: datetime

@dataclass(frozen=True)
class WorkIdle:
    kind: Literal["idle"] = "idle"

@dataclass(frozen=True)
class WorkTerminal:
    job_id: UUID
    status: str
    kind: Literal["terminal"] = "terminal"

@dataclass(frozen=True)
class WorkRetryScheduled:
    job_id: UUID
    next_available_at: datetime
    kind: Literal["retry_scheduled"] = "retry_scheduled"

@dataclass(frozen=True)
class WorkLeaseLost:
    job_id: UUID
    kind: Literal["lease_lost"] = "lease_lost"

WorkOutcome: TypeAlias = WorkIdle | WorkTerminal | WorkRetryScheduled | WorkLeaseLost


class JobHandler(Protocol):
    def validate(self, content: bytes) -> None:
        """Parse the real capability schema; reject invalid immutable input."""
    def execute(self, content: bytes, deadline: Deadline) -> JobResultRef:
        """Persist the typed result and return its immutable reference."""


class HandlerRegistry:
    def __init__(self):
        self._handlers: dict[tuple[JobKind, JobOptimizationMode | None], JobHandler] = {}

    def register(self, kind, handler, mode=None):
        if (kind == JobKind.OPTIMIZATION) != (mode is not None):
            raise ValueError("optimization requires an explicit mode")
        self._handlers[(kind, mode)] = handler

    def require(self, command: JobRequest) -> JobHandler:
        key = (command.kind, getattr(command.payload, "mode", None))
        if key not in self._handlers:
            raise ServiceError(ErrorCode.INVALID_INPUT, "capability is not enabled", 501)
        return self._handlers[key]


class JobService:
    def __init__(self, repository, registry: HandlerRegistry):
        self.repository = repository
        self.registry = registry

    def store_request(self, reference, content: bytes, actor) -> None:
        """Persist immutable job input; callers never reach the repository directly."""
        self.repository.store_request(reference, actor.scope_id, content)

    def submit_prepared(self, actor, key, trace_id, operation, input_hash, prepare, *, connection=None):
        def validated():
            command, content = prepare()
            self.registry.require(command).validate(content)
            return command, content
        return self.repository.submit_once(actor, key, trace_id, operation, input_hash,
                                           validated, connection=connection)

    def submit(self, command: JobRequest, actor, key: str, trace_id: UUID):
        handler = self.registry.require(command)
        content = self.repository.load_request(command.payload.request_ref, actor.scope_id)
        handler.validate(content)
        return self.repository.enqueue(command, actor, key, trace_id)

    def get(self, job_id, actor):
        return self.repository.get(job_id, actor.scope_id)

    def result_kind(self, job_id, actor):
        command = self.repository.command(job_id, actor.scope_id)
        return (command.payload.mode.value if command.kind == JobKind.OPTIMIZATION
                else command.kind.value)

    def load_request(self, job_id, actor) -> bytes:
        return self.repository.load_job_request(job_id, actor.scope_id)

    def cancel(self, job_id, command, actor):
        return self.repository.cancel(job_id, command.expected_revision, actor.scope_id)
