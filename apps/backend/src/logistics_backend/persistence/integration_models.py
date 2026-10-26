"""Immutable scenario evidence and durable negotiation/observation records."""
from sqlalchemy import Column, DateTime, ForeignKey, Index, String, Table, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID

from logistics_backend.persistence.resource_models import metadata

integration_scenarios = Table('integration_scenarios', metadata,
    Column('id', UUID(as_uuid=True), primary_key=True),
    Column('scope_id', UUID(as_uuid=True), nullable=False),
    Column('input_hash', String(64), nullable=False),
    Column('created_at', DateTime(timezone=True), nullable=False),
    Column('created_by', UUID(as_uuid=True), nullable=False),
    Column('payload', JSONB, nullable=False),
    UniqueConstraint('scope_id', 'input_hash', name='uq_integration_scenarios_input'))

integration_runs = Table('integration_runs', metadata,
    Column('id', UUID(as_uuid=True), primary_key=True),
    Column('scope_id', UUID(as_uuid=True), nullable=False),
    Column('scenario_id', UUID(as_uuid=True), ForeignKey('integration_scenarios.id'), nullable=False),
    Column('request_hash', String(64), nullable=False),
    Column('idempotency_key', String(128), nullable=False),
    Column('created_at', DateTime(timezone=True), nullable=False),
    Column('created_by', UUID(as_uuid=True), nullable=False),
    Column('payload', JSONB, nullable=False),
    UniqueConstraint('scope_id', 'idempotency_key', name='uq_integration_runs_key'))
Index('ix_integration_runs_scope', integration_runs.c.scope_id, integration_runs.c.created_at)
