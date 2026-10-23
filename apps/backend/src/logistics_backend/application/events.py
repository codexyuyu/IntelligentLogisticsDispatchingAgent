"""Event ingestion service (P13-02 subset) with append-only event rows."""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID, uuid4

from sqlalchemy import func, select

from logistics_backend.errors import ServiceError
from logistics_backend.persistence.event_models import events
from logistics_backend.persistence.uow import UnitOfWork
from logistics_contracts.events import EventReceiptDTO, EventViewDTO
from logistics_domain.events import Event, EventEnvelope, EventReceipt, EventStatus
from logistics_domain.states import EntityState, ErrorCode


class EventService:
    def __init__(self, uow_factory, workspace_id: UUID):
        self.uow_factory = uow_factory
        self.workspace_id = workspace_id

    def ingest(self, envelope_dto, actor, trace_id: UUID) -> EventReceiptDTO:
        envelope = envelope_dto.to_domain()
        if not isinstance(envelope, EventEnvelope):
            raise ServiceError(ErrorCode.INVALID_INPUT, "invalid event envelope")
        now = datetime.now(timezone.utc).replace(microsecond=0)
        with self.uow_factory() as uow:
            existing = uow.connection.execute(select(events).where(
                events.c.scope_id == actor.scope_id, events.c.source == envelope.source,
                events.c.source_event_id == envelope.source_event_id)).mappings().first()
            if existing is not None:
                receipt = EventReceipt(event_id=existing["id"], sequence=existing["sequence"],
                    status=EventStatus(existing["status"]), duplicate=True, trace_id=trace_id)
                return EventReceiptDTO.model_validate(_receipt(receipt))
            sequence = int(uow.connection.execute(select(
                func.coalesce(func.max(events.c.sequence), 0)).where(
                events.c.scope_id == actor.scope_id)).scalar_one()) + 1
            event = Event(id=uuid4(), status=EntityState.RECEIVED, created_at=now,
                updated_at=now, row_version=0, schema_version="2.0.0",
                created_by=actor.actor_id, source=envelope.source,
                source_event_id=envelope.source_event_id, kind=envelope.kind,
                occurred_at_utc=envelope.occurred_at_utc, received_at_utc=now,
                simulation_id=envelope.simulation_id, sequence=sequence,
                payload=envelope.payload)
            uow.connection.execute(events.insert().values(
                id=event.id, scope_id=actor.scope_id, status=event.status.value,
                created_at=now, updated_at=now, created_by=actor.actor_id, row_version=0,
                schema_version="2.0.0", source=event.source,
                source_event_id=event.source_event_id, kind=event.kind.value,
                occurred_at_utc=event.occurred_at_utc, received_at_utc=event.received_at_utc,
                simulation_id=event.simulation_id, sequence=event.sequence,
                payload=envelope_dto.payload.model_dump(mode="json"), trace_id=trace_id))
            receipt = EventReceipt(event_id=event.id, sequence=sequence,
                status=EventStatus.RECEIVED, duplicate=False, trace_id=trace_id)
            return EventReceiptDTO.model_validate(_receipt(receipt))

    def get(self, event_id: UUID, actor) -> EventViewDTO:
        with self.uow_factory() as uow:
            row = uow.connection.execute(select(events).where(
                events.c.id == event_id, events.c.scope_id == actor.scope_id)).mappings().first()
            if row is None:
                raise ServiceError(ErrorCode.NOT_FOUND, "event not found")
            return EventViewDTO(schema_version="2.0.0", event_id=row["id"],
                source=row["source"], source_event_id=row["source_event_id"],
                kind=row["kind"], status=row["status"], occurred_at_utc=row["occurred_at_utc"],
                received_at_utc=row["received_at_utc"], sequence=row["sequence"],
                simulation_id=row["simulation_id"], trace_id=row["trace_id"])


def _receipt(receipt: EventReceipt) -> dict:
    return {"event_id": receipt.event_id, "sequence": receipt.sequence,
            "status": receipt.status, "duplicate": receipt.duplicate,
            "trace_id": receipt.trace_id}
