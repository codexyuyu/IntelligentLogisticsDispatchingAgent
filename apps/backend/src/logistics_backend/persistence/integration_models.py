"""Immutable scenario evidence and durable negotiation/observation records."""
from sqlalchemy import BigInteger, CheckConstraint, Column, DateTime, ForeignKey, Index, String, Table, UniqueConstraint
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


# Planned replay stream, deliberately separate from real incident `events` and
# from actual task state transitions.  One immutable sequence per checked run.
integration_timeline_events = Table('integration_timeline_events', metadata,
    Column('id', UUID(as_uuid=True), primary_key=True),
    Column('scope_id', UUID(as_uuid=True), nullable=False),
    Column('run_id', UUID(as_uuid=True), ForeignKey('integration_runs.id', ondelete='RESTRICT'), nullable=False),
    Column('sequence', BigInteger, nullable=False),
    Column('time_s', BigInteger, nullable=False),
    Column('kind', String(40), nullable=False),
    Column('created_at', DateTime(timezone=True), nullable=False),
    Column('payload', JSONB, nullable=False),
    UniqueConstraint('run_id', 'sequence', name='uq_integration_timeline_run_sequence'),
    CheckConstraint('sequence >= 0 AND time_s >= 0', name='timeline_nonnegative'),
    CheckConstraint("payload->>'id' = id::text AND (payload->>'sequence')::bigint = sequence "
                    "AND payload->>'kind' = kind", name='timeline_payload_identity'))
Index('ix_integration_timeline_scope_run', integration_timeline_events.c.scope_id,
      integration_timeline_events.c.run_id, integration_timeline_events.c.sequence)


# Simulation-only projections.  These never replace planned timeline evidence,
# warehouse execution transitions, or approved operational schedule versions.
integration_simulations = Table('integration_simulations', metadata,
    Column('id', UUID(as_uuid=True), primary_key=True),
    Column('scope_id', UUID(as_uuid=True), nullable=False),
    Column('run_id', UUID(as_uuid=True), ForeignKey('integration_runs.id', ondelete='RESTRICT'), nullable=False),
    Column('created_at', DateTime(timezone=True), nullable=False),
    Column('created_by', UUID(as_uuid=True), nullable=False),
    Column('payload', JSONB, nullable=False),
    UniqueConstraint('run_id', name='uq_integration_simulations_run'),
    CheckConstraint("payload->>'id' = id::text AND payload->>'run_id' = run_id::text",
                    name='payload_identity'))
Index('ix_integration_simulations_scope_run', integration_simulations.c.scope_id,
      integration_simulations.c.run_id)

integration_simulation_incidents = Table('integration_simulation_incidents', metadata,
    Column('id', UUID(as_uuid=True), primary_key=True),
    Column('scope_id', UUID(as_uuid=True), nullable=False),
    Column('simulation_id', UUID(as_uuid=True), ForeignKey('integration_simulations.id', ondelete='RESTRICT'), nullable=False),
    Column('event_id', UUID(as_uuid=True), ForeignKey('events.id', ondelete='RESTRICT'), nullable=False),
    Column('status', String(16), nullable=False),
    Column('row_version', BigInteger, nullable=False),
    Column('created_at', DateTime(timezone=True), nullable=False),
    Column('updated_at', DateTime(timezone=True), nullable=False),
    Column('created_by', UUID(as_uuid=True), nullable=False),
    Column('payload', JSONB, nullable=False),
    UniqueConstraint('simulation_id', name='uq_integration_simulation_one_incident'),
    UniqueConstraint('event_id', name='uq_integration_simulation_incident_event'),
    CheckConstraint("status IN ('pending','approved','rejected')", name='status'),
    CheckConstraint('row_version >= 0', name='row_version_nonnegative'),
    CheckConstraint("payload->>'id' = id::text AND payload->>'simulation_id' = simulation_id::text",
                    name='payload_identity'))
Index('ix_integration_simulation_incidents_scope', integration_simulation_incidents.c.scope_id,
      integration_simulation_incidents.c.simulation_id)
