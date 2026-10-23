"""Tool-call persistence (P17/P19 subset)."""

from __future__ import annotations

from sqlalchemy import BigInteger, CheckConstraint, Column, DateTime, ForeignKey, Index, String, Table
from sqlalchemy.dialects.postgresql import JSONB, UUID

from logistics_backend.persistence.resource_models import metadata

tool_calls = Table("tool_calls", metadata,
    Column("id", UUID(as_uuid=True), primary_key=True),
    Column("scope_id", UUID(as_uuid=True), nullable=False),
    Column("status", String(32), nullable=False),
    Column("created_at", DateTime(timezone=True), nullable=False),
    Column("updated_at", DateTime(timezone=True), nullable=False),
    Column("created_by", UUID(as_uuid=True), nullable=False),
    Column("row_version", BigInteger, nullable=False),
    Column("schema_version", String(16), nullable=False),
    Column("run_id", UUID(as_uuid=True), ForeignKey("agent_runs.id", ondelete="SET NULL")),
    Column("tool_name", String(64), nullable=False),
    Column("arguments", JSONB(none_as_null=True), nullable=False),
    Column("result", JSONB(none_as_null=True)),
    Column("error_code", String(64)),
    Column("duration_ms", BigInteger, nullable=False),
    Column("trace_id", UUID(as_uuid=True), nullable=False),
    CheckConstraint("status IN ('requested','authorized','running','succeeded','failed','denied','cancelled')",
                    name="status"),
    CheckConstraint("schema_version = '2.0.0'", name="schema"),
    CheckConstraint("duration_ms >= 0", name="duration"),
    Index("ix_tool_calls_scope_created", "scope_id", "created_at"))

TOOL_TABLES = (tool_calls,)
