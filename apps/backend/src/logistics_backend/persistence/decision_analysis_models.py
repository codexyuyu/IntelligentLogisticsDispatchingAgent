"""Scope-bound model analysis of solver candidates and simulation incidents."""
from sqlalchemy import Column, DateTime, ForeignKey, Index, String, Table, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from logistics_backend.persistence.resource_models import metadata

agent_decision_analyses = Table('agent_decision_analyses', metadata,
    Column('id', UUID(as_uuid=True), primary_key=True),
    Column('scope_id', UUID(as_uuid=True), nullable=False),
    Column('actor_id', UUID(as_uuid=True), nullable=False),
    Column('run_id', UUID(as_uuid=True), ForeignKey('integration_runs.id'), nullable=False),
    Column('target_type', String(24), nullable=False),
    Column('target_id', UUID(as_uuid=True), nullable=False),
    Column('created_at', DateTime(timezone=True), nullable=False),
    Column('question', Text, nullable=False),
    Column('reply', Text, nullable=False),
    Column('model', String(128), nullable=True),
    Column('status', String(32), nullable=False),
    Column('error_code', String(64), nullable=True),
    Column('tool_trace', JSONB, nullable=False),
    Column('evidence', JSONB, nullable=False),
    Column('recommendation', String(32), nullable=True))
Index('ix_agent_decision_analyses_target', agent_decision_analyses.c.scope_id,
      agent_decision_analyses.c.target_type, agent_decision_analyses.c.target_id,
      agent_decision_analyses.c.created_at.desc())
