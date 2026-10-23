"""Storage ports for planning snapshots and atomic plan commits (P03-03/P03-04).

The protocols use only pure domain values. They do not expose a session, ORM row, SQL
statement or connection, so application services remain independent of the PostgreSQL
adapter and no ORM object can cross the boundary.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable
from uuid import UUID

from logistics_domain.planning import (
    CommitCommand,
    CommitReceipt,
    PlanningScope,
    PlanningSnapshot,
    ValidationReport,
)
from logistics_domain.runtime import ActorContext

__all__ = ["PlanCommitStore", "PlanningSnapshotStore", "TransactionalUnitOfWork"]


@runtime_checkable
class PlanningSnapshotStore(Protocol):
    """Capture one consistent snapshot of a planning scope."""

    def capture(self, scope: PlanningScope) -> PlanningSnapshot:
        ...


@runtime_checkable
class PlanCommitStore(Protocol):
    """Commit one validated candidate with CAS, reservations, audit and outbox.

    ``actor`` and ``trace_id`` are supplied by the application boundary (P16); the storage
    contract itself stays ``commit(cmd, report)``. When they are omitted the adapter records
    an explicit system actor and a fresh trace id instead of inventing a user identity.
    """

    def commit(self, cmd: CommitCommand, report: ValidationReport, *,
               actor: ActorContext | None = None, trace_id: UUID | None = None) -> CommitReceipt:
        ...


@runtime_checkable
class TransactionalUnitOfWork(Protocol):
    """Transaction boundary with explicit commit/rollback and automatic rollback on error."""

    def commit(self) -> None:
        ...

    def rollback(self) -> None:
        ...
