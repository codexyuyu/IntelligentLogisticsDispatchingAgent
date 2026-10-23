"""Metric persistence (P32 subset)."""

from __future__ import annotations

from sqlalchemy import BigInteger, CheckConstraint, Column, DateTime, Float, Index, String, Table
from sqlalchemy.dialects.postgresql import UUID

from logistics_backend.persistence.resource_models import metadata

metric_records = Table("metric_records", metadata,
    Column("id", UUID(as_uuid=True), primary_key=True),
    Column("scope_id", UUID(as_uuid=True), nullable=False),
    Column("status", String(32), nullable=False),
    Column("created_at", DateTime(timezone=True), nullable=False),
    Column("updated_at", DateTime(timezone=True), nullable=False),
    Column("created_by", UUID(as_uuid=True), nullable=False),
    Column("row_version", BigInteger, nullable=False),
    Column("schema_version", String(16), nullable=False),
    Column("code", String(64), nullable=False),
    Column("definition_version", String(32), nullable=False),
    Column("source", String(16), nullable=False),
    Column("unit", String(32), nullable=False),
    Column("value", Float),
    Column("numerator", Float),
    Column("denominator", Float),
    Column("reason", String(32)),
    Column("sample_count", BigInteger, nullable=False),
    CheckConstraint("status IN ('active','deprecated')", name="status"),
    CheckConstraint("source IN ('planned','simulation','actual')", name="source"),
    CheckConstraint("schema_version = '2.0.0'", name="schema"),
    CheckConstraint("sample_count >= 0", name="sample"),
    CheckConstraint("(value IS NULL) <> (reason IS NULL)", name="value_reason"),
    Index("ix_metric_records_code", "scope_id", "code", "created_at"))

METRIC_TABLES = (metric_records,)
