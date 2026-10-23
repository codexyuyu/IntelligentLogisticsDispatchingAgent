"""Event ingestion and exception projection tables (frozen 0003)."""
from alembic import op

revision = "0003_events"
down_revision = "0002_planning_runtime"
branch_labels = None
depends_on = None


def upgrade():
    op.execute("""CREATE TABLE events (
	id UUID NOT NULL, 
	scope_id UUID NOT NULL, 
	status VARCHAR(32) NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	created_by UUID NOT NULL, 
	row_version BIGINT NOT NULL, 
	schema_version VARCHAR(16) NOT NULL, 
	source VARCHAR(256) NOT NULL, 
	source_event_id VARCHAR(256) NOT NULL, 
	kind VARCHAR(32) NOT NULL, 
	occurred_at_utc TIMESTAMP WITH TIME ZONE NOT NULL, 
	received_at_utc TIMESTAMP WITH TIME ZONE NOT NULL, 
	simulation_id UUID, 
	sequence BIGINT NOT NULL, 
	payload JSONB NOT NULL, 
	trace_id UUID NOT NULL, 
	CONSTRAINT pk_events PRIMARY KEY (id), 
	CONSTRAINT uq_events_identity UNIQUE (scope_id, source, source_event_id), 
	CONSTRAINT ck_events_status CHECK (status IN ('received','validated','applied','duplicate','rejected','quarantined')), 
	CONSTRAINT ck_events_counters CHECK (row_version >= 0 AND sequence >= 0), 
	CONSTRAINT ck_events_schema CHECK (schema_version = '2.0.0')
)""")
    op.execute("""CREATE TABLE exception_events (
	id UUID NOT NULL, 
	scope_id UUID NOT NULL, 
	status VARCHAR(32) NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	created_by UUID NOT NULL, 
	row_version BIGINT NOT NULL, 
	schema_version VARCHAR(16) NOT NULL, 
	event_id UUID NOT NULL, 
	severity VARCHAR(16) NOT NULL, 
	affected_entity_refs JSONB NOT NULL, 
	impact_report_ref UUID, 
	decision_record_id UUID, 
	CONSTRAINT pk_exception_events PRIMARY KEY (id), 
	CONSTRAINT ck_exception_events_status CHECK (status IN ('detected','analyzed','proposed','resolved','manual_required','unresolved')), 
	CONSTRAINT ck_exception_events_severity CHECK (severity IN ('critical','high','medium','low')), 
	CONSTRAINT ck_exception_events_schema CHECK (schema_version = '2.0.0'), 
	CONSTRAINT fk_exception_events_event_id_events FOREIGN KEY(event_id) REFERENCES events (id) ON DELETE RESTRICT
)""")
    op.execute("""CREATE INDEX ix_events_kind ON events (scope_id, kind, occurred_at_utc)""")
    op.execute("""CREATE INDEX ix_events_sequence ON events (scope_id, sequence)""")
    op.execute("""CREATE INDEX ix_exception_events_event ON exception_events (event_id)""")


def downgrade():
    for table in ("exception_events", "events"):
        op.execute(f"DROP TABLE {table}")

