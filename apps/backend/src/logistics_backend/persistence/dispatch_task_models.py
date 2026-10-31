"""Persistent, operator-reviewed simulation dispatch proposals (migration 0013)."""
from sqlalchemy import BigInteger, CheckConstraint, Column, DateTime, ForeignKey, Index, String, Table, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from logistics_backend.persistence.resource_models import metadata

dispatch_tasks = Table('agent_dispatch_tasks', metadata,
    Column('id', UUID(as_uuid=True), primary_key=True),
    Column('scope_id', UUID(as_uuid=True), nullable=False),
    Column('actor_id', UUID(as_uuid=True), nullable=False),
    Column('source_run_id', UUID(as_uuid=True), ForeignKey('integration_runs.id'), nullable=False),
    Column('candidate_run_id', UUID(as_uuid=True), ForeignKey('integration_runs.id'), nullable=True),
    Column('status', String(24), nullable=False),
    Column('row_version', BigInteger, nullable=False, server_default='0'),
    Column('created_at', DateTime(timezone=True), nullable=False),
    Column('updated_at', DateTime(timezone=True), nullable=False),
    Column('instruction', Text, nullable=False),
    Column('intent', JSONB, nullable=False),
    Column('evidence', JSONB, nullable=False),
    Column('parser', String(24), nullable=False),
    Column('incident_id', UUID(as_uuid=True), nullable=True),
    CheckConstraint("status IN ('draft','solving','ready','approved','rejected','failed')", name='agent_dispatch_task_status'),
    CheckConstraint('row_version >= 0', name='agent_dispatch_task_version'))
Index('ix_agent_dispatch_tasks_scope_created', dispatch_tasks.c.scope_id, dispatch_tasks.c.created_at.desc())
