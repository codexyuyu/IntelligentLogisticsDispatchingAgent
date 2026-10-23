"""Event and exception persistence (P13-02)."""

from __future__ import annotations

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    Column,
    DateTime,
    ForeignKey,
    Index,
    String,
    Table,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID

from logistics_backend.persistence.resource_models import metadata

events = Table("events", metadata,
    Column("id", UUID(as_uuid=True), primary_key=True),
    Column("scope_id", UUID(as_uuid=True), nullable=False),
    Column("status", String(32), nullable=False),
    Column("created_at", DateTime(timezone=True), nullable=False),
    Column("updated_at", DateTime(timezone=True), nullable=False),
    Column("created_by", UUID(as_uuid=True), nullable=False),
    Column("row_version", BigInteger, nullable=False),
    Column("schema_version", String(16), nullable=False),
    Column("source", String(256), nullable=False),
    Column("source_event_id", String(256), nullable=False),
    Column("kind", String(32), nullable=False),
    Column("occurred_at_utc", DateTime(timezone=True), nullable=False),
    Column("received_at_utc", DateTime(timezone=True), nullable=False),
    Column("simulation_id", UUID(as_uuid=True)),
    Column("sequence", BigInteger, nullable=False),
    Column("payload", JSONB(none_as_null=True), nullable=False),
    Column("trace_id", UUID(as_uuid=True), nullable=False),
    UniqueConstraint("scope_id", "source", "source_event_id", name="uq_events_identity"),
    CheckConstraint("status IN ('received','validated','applied','duplicate','rejected','quarantined')",
                    name="status"),
    CheckConstraint("row_version >= 0 AND sequence >= 0", name="counters"),
    CheckConstraint("schema_version = '2.0.0'", name="schema"),
    Index("ix_events_sequence", "scope_id", "sequence"),
    Index("ix_events_kind", "scope_id", "kind", "occurred_at_utc"))

exception_events = Table("exception_events", metadata,
    Column("id", UUID(as_uuid=True), primary_key=True),
    Column("scope_id", UUID(as_uuid=True), nullable=False),
    Column("status", String(32), nullable=False),
    Column("created_at", DateTime(timezone=True), nullable=False),
    Column("updated_at", DateTime(timezone=True), nullable=False),
    Column("created_by", UUID(as_uuid=True), nullable=False),
    Column("row_version", BigInteger, nullable=False),
    Column("schema_version", String(16), nullable=False),
    Column("event_id", UUID(as_uuid=True), ForeignKey("events.id", ondelete="RESTRICT"),
           nullable=False),
    Column("severity", String(16), nullable=False),
    Column("affected_entity_refs", JSONB(none_as_null=True), nullable=False),
    Column("impact_report_ref", UUID(as_uuid=True)),
    Column("decision_record_id", UUID(as_uuid=True)),
    CheckConstraint("status IN ('detected','analyzed','proposed','resolved','manual_required','unresolved')",
                    name="status"),
    CheckConstraint("severity IN ('critical','high','medium','low')", name="severity"),
    CheckConstraint("schema_version = '2.0.0'", name="schema"),
    Index("ix_exception_events_event", "event_id"))

EVENT_TABLES = (events, exception_events)
