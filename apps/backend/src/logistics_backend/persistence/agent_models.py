"""Agent run persistence (P19/P23 subset)."""

from __future__ import annotations

from sqlalchemy import BigInteger, Boolean, CheckConstraint, Column, DateTime, Index, String, Table, Text
from sqlalchemy.dialects.postgresql import UUID

from logistics_backend.persistence.resource_models import metadata

agent_runs = Table("agent_runs", metadata,
    Column("id", UUID(as_uuid=True), primary_key=True),
    Column("scope_id", UUID(as_uuid=True), nullable=False),
    Column("status", String(32), nullable=False),
    Column("created_at", DateTime(timezone=True), nullable=False),
    Column("updated_at", DateTime(timezone=True), nullable=False),
    Column("created_by", UUID(as_uuid=True), nullable=False),
    Column("row_version", BigInteger, nullable=False),
    Column("schema_version", String(16), nullable=False),
    Column("session_id", UUID(as_uuid=True)),
    Column("prompt", Text, nullable=False),
    Column("reply", Text),
    Column("model", String(128)),
    Column("provider_configured", Boolean, nullable=False),
    Column("latency_ms", BigInteger, nullable=False),
    Column("trace_id", UUID(as_uuid=True), nullable=False),
    CheckConstraint("status IN ('completed','failed')", name="status"),
    CheckConstraint("schema_version = '2.0.0'", name="schema"),
    CheckConstraint("latency_ms >= 0", name="latency"),
    Index("ix_agent_runs_scope_created", "scope_id", "created_at"))

AGENT_TABLES = (agent_runs,)
