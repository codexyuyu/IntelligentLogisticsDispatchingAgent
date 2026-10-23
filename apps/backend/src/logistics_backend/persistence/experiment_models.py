"""Experiment comparison persistence (P33 subset)."""

from __future__ import annotations

from sqlalchemy import BigInteger, CheckConstraint, Column, DateTime, Index, String, Table
from sqlalchemy.dialects.postgresql import JSONB, UUID

from logistics_backend.persistence.resource_models import metadata

experiment_records = Table("experiment_records", metadata,
    Column("id", UUID(as_uuid=True), primary_key=True),
    Column("scope_id", UUID(as_uuid=True), nullable=False),
    Column("status", String(32), nullable=False),
    Column("created_at", DateTime(timezone=True), nullable=False),
    Column("updated_at", DateTime(timezone=True), nullable=False),
    Column("created_by", UUID(as_uuid=True), nullable=False),
    Column("row_version", BigInteger, nullable=False),
    Column("schema_version", String(16), nullable=False),
    Column("base_label", String(128), nullable=False),
    Column("candidate_label", String(128), nullable=False),
    Column("orders_total", BigInteger, nullable=False),
    Column("metric_version", String(32), nullable=False),
    Column("base_result", JSONB(none_as_null=True), nullable=False),
    Column("candidate_result", JSONB(none_as_null=True), nullable=False),
    Column("comparison", JSONB(none_as_null=True), nullable=False),
    CheckConstraint("status IN ('completed','failed')", name="status"),
    CheckConstraint("schema_version = '2.0.0'", name="schema"),
    CheckConstraint("orders_total >= 0", name="orders"),
    Index("ix_experiment_records_scope_created", "scope_id", "created_at"))

EXPERIMENT_TABLES = (experiment_records,)
