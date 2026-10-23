"""Event and exception boundary projections (P13-02)."""

from __future__ import annotations

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, StrictInt

from logistics_contracts.common import EntityRefDTO
from logistics_contracts.planning import Record
from logistics_contracts.runtime import EventPayloadDTO
from logistics_domain import events as domain
from logistics_domain.execution import EventKind
from logistics_domain.states import EntityState


class EventEnvelopeDTO(Record):
    domain_type = domain.EventEnvelope
    schema_version: Literal["2.0.0"]
    source: str
    source_event_id: str
    kind: EventKind
    occurred_at_utc: datetime
    simulation_id: UUID | None
    payload: EventPayloadDTO
    expected_revision: StrictInt | None = None


class EventReceiptDTO(Record):
    domain_type = domain.EventReceipt
    event_id: UUID
    sequence: StrictInt
    status: domain.EventStatus
    duplicate: bool
    trace_id: UUID


class EventViewDTO(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    schema_version: Literal["2.0.0"] = "2.0.0"
    event_id: UUID
    source: str
    source_event_id: str
    kind: EventKind
    status: EntityState
    occurred_at_utc: datetime
    received_at_utc: datetime
    sequence: StrictInt
    simulation_id: UUID | None
    trace_id: UUID


class ExceptionEventDTO(Record):
    domain_type = domain.ExceptionEvent
    id: UUID
    status: EntityState
    created_at: datetime
    updated_at: datetime
    row_version: StrictInt
    schema_version: Literal["2.0.0"]
    created_by: UUID
    event_id: UUID
    severity: domain.ExceptionSeverity
    affected_entity_refs: tuple[EntityRefDTO, ...]
    impact_report_ref: UUID | None
    decision_record_id: UUID | None


class ExceptionEventView(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    schema_version: Literal["2.0.0"] = "2.0.0"
    exception_id: UUID
    event_id: UUID
    severity: domain.ExceptionSeverity
    status: EntityState
    affected_entity_refs: tuple[EntityRefDTO, ...]
