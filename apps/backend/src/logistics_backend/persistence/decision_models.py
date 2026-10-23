"""Decision-record persistence (P19/P23 audit subset)."""

from __future__ import annotations

from sqlalchemy import BigInteger, CheckConstraint, Column, DateTime, Float, ForeignKey, Index, String, Table, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID

from logistics_backend.persistence.resource_models import metadata

decision_records = Table("decision_records", metadata,
    Column("id", UUID(as_uuid=True), primary_key=True),
    Column("scope_id", UUID(as_uuid=True), nullable=False),
    Column("status", String(32), nullable=False),
    Column("created_at", DateTime(timezone=True), nullable=False),
    Column("updated_at", DateTime(timezone=True), nullable=False),
    Column("created_by", UUID(as_uuid=True), nullable=False),
    Column("row_version", BigInteger, nullable=False),
    Column("schema_version", String(16), nullable=False),
    Column("run_id", UUID(as_uuid=True), ForeignKey("agent_runs.id", ondelete="SET NULL")),
    Column("tool_call_id", UUID(as_uuid=True), ForeignKey("tool_calls.id", ondelete="SET NULL")),
    Column("decision_type", String(64), nullable=False),
    Column("payload", JSONB(none_as_null=True), nullable=False),
    Column("rationale", Text, nullable=False),
    Column("confidence", Float, nullable=False),
    Column("evidence_refs", JSONB(none_as_null=True), nullable=False),
    CheckConstraint("status IN ('proposed','accepted','rejected','superseded')", name="status"),
    CheckConstraint("schema_version = '2.0.0'", name="schema"),
    CheckConstraint("confidence >= 0 AND confidence <= 1", name="confidence"),
    Index("ix_decision_records_scope_created", "scope_id", "created_at"))

DECISION_TABLES = (decision_records,)
