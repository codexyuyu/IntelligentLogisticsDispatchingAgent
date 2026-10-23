"""Validation report persistence (P16 commit chain)."""

from __future__ import annotations

from sqlalchemy import Boolean, CheckConstraint, Column, DateTime, Index, String, Table, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID

from logistics_backend.persistence.resource_models import metadata

validation_reports = Table("validation_reports", metadata,
    Column("id", UUID(as_uuid=True), primary_key=True),
    Column("scope_id", UUID(as_uuid=True), nullable=False),
    Column("candidate_id", UUID(as_uuid=True), nullable=False),
    Column("candidate_hash", String(64), nullable=False),
    Column("snapshot_hash", String(64), nullable=False),
    Column("rules_version", String(32), nullable=False),
    Column("valid", Boolean, nullable=False),
    Column("report", JSONB(none_as_null=True), nullable=False),
    Column("created_at", DateTime(timezone=True), nullable=False),
    Column("created_by", UUID(as_uuid=True), nullable=False),
    CheckConstraint("candidate_hash <> snapshot_hash", name="distinct_hashes"),
    UniqueConstraint("candidate_id", name="uq_validation_reports_candidate"),
    Index("ix_validation_reports_candidate", "scope_id", "candidate_id"))

VALIDATION_TABLES = (validation_reports,)
