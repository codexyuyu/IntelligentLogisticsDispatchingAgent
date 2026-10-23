"""Event-ingestion and exception records (P13-01/P13-02 domain subset)."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from uuid import UUID

from logistics_domain.errors import InvalidInputError
from logistics_domain.execution import EventKind, EventPayload
from logistics_domain.orders import Entity
from logistics_domain.primitives import EntityRef, require_int, require_non_negative_int, require_utc_seconds, require_uuid

__all__ = [
    "Event",
    "EventEnvelope",
    "EventReceipt",
    "ExceptionEvent",
    "ExceptionSeverity",
    "EventStatus",
]


class ExceptionSeverity(StrEnum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class EventStatus(StrEnum):
    RECEIVED = "received"
    VALIDATED = "validated"
    APPLIED = "applied"
    DUPLICATE = "duplicate"
    REJECTED = "rejected"
    QUARANTINED = "quarantined"


@dataclass(frozen=True, slots=True)
class Event(Entity):
    lifecycle = "event"

    source: str
    source_event_id: str
    kind: EventKind
    occurred_at_utc: object
    received_at_utc: object
    simulation_id: UUID | None
    sequence: int
    payload: EventPayload

    def __post_init__(self) -> None:
        Entity.__post_init__(self)
        for name in ("source", "source_event_id"):
            value = getattr(self, name)
            if not isinstance(value, str) or not 1 <= len(value) <= 256:
                raise InvalidInputError(f"Event.{name} must be 1..256 characters")
        if not isinstance(self.kind, EventKind):
            raise InvalidInputError("Event.kind must be an EventKind")
        require_utc_seconds(self.occurred_at_utc, field="Event.occurred_at_utc")
        require_utc_seconds(self.received_at_utc, field="Event.received_at_utc")
        if self.simulation_id is not None:
            require_uuid(self.simulation_id, field="Event.simulation_id")
        require_non_negative_int(self.sequence, field="Event.sequence")
        if self.payload.kind != self.kind.value:
            raise InvalidInputError("Event.kind must equal payload.kind")


@dataclass(frozen=True, slots=True)
class EventEnvelope:
    schema_version: str
    source: str
    source_event_id: str
    kind: EventKind
    occurred_at_utc: object
    simulation_id: UUID | None
    payload: EventPayload
    expected_revision: int | None = None

    def __post_init__(self) -> None:
        if self.schema_version != "2.0.0":
            raise InvalidInputError("EventEnvelope.schema_version must be 2.0.0")
        for name in ("source", "source_event_id"):
            value = getattr(self, name)
            if not isinstance(value, str) or not 1 <= len(value) <= 256:
                raise InvalidInputError(f"EventEnvelope.{name} must be 1..256 characters")
        if not isinstance(self.kind, EventKind):
            raise InvalidInputError("EventEnvelope.kind must be EventKind")
        require_utc_seconds(self.occurred_at_utc, field="EventEnvelope.occurred_at_utc")
        if self.simulation_id is not None:
            require_uuid(self.simulation_id, field="EventEnvelope.simulation_id")
        if self.payload.kind != self.kind.value:
            raise InvalidInputError("EventEnvelope.kind must equal payload.kind")
        if self.expected_revision is not None:
            require_int(self.expected_revision, field="EventEnvelope.expected_revision", minimum=0)


@dataclass(frozen=True, slots=True)
class EventReceipt:
    event_id: UUID
    sequence: int
    status: EventStatus
    duplicate: bool
    trace_id: UUID

    def __post_init__(self) -> None:
        require_uuid(self.event_id, field="EventReceipt.event_id")
        require_non_negative_int(self.sequence, field="EventReceipt.sequence")
        if not isinstance(self.status, EventStatus):
            raise InvalidInputError("EventReceipt.status must be EventStatus")
        if not isinstance(self.duplicate, bool):
            raise InvalidInputError("EventReceipt.duplicate must be bool")
        require_uuid(self.trace_id, field="EventReceipt.trace_id")


@dataclass(frozen=True, slots=True)
class ExceptionEvent(Entity):
    lifecycle = "exception_event"

    event_id: UUID
    severity: ExceptionSeverity
    affected_entity_refs: tuple[EntityRef, ...]
    impact_report_ref: UUID | None
    decision_record_id: UUID | None

    def __post_init__(self) -> None:
        Entity.__post_init__(self)
        require_uuid(self.event_id, field="ExceptionEvent.event_id")
        if not isinstance(self.severity, ExceptionSeverity):
            raise InvalidInputError("ExceptionEvent.severity must be ExceptionSeverity")
        if not isinstance(self.affected_entity_refs, tuple):
            raise InvalidInputError("ExceptionEvent.affected_entity_refs must be a tuple")
        for index, reference in enumerate(self.affected_entity_refs):
            if not isinstance(reference, EntityRef):
                raise InvalidInputError(f"affected_entity_refs[{index}] must be EntityRef")
        for name in ("impact_report_ref", "decision_record_id"):
            value = getattr(self, name)
            if value is not None:
                require_uuid(value, field=f"ExceptionEvent.{name}")
