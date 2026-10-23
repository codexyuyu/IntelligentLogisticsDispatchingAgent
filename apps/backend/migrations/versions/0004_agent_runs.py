"""Agent run audit table (frozen 0004)."""
from alembic import op

revision = "0004_agent_runs"
down_revision = "0003_events"
branch_labels = None
depends_on = None


def upgrade():
    op.execute("""CREATE TABLE agent_runs (
	id UUID NOT NULL, 
	scope_id UUID NOT NULL, 
	status VARCHAR(32) NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	created_by UUID NOT NULL, 
	row_version BIGINT NOT NULL, 
	schema_version VARCHAR(16) NOT NULL, 
	session_id UUID, 
	prompt TEXT NOT NULL, 
	reply TEXT, 
	model VARCHAR(128), 
	provider_configured BOOLEAN NOT NULL, 
	latency_ms BIGINT NOT NULL, 
	trace_id UUID NOT NULL, 
	CONSTRAINT pk_agent_runs PRIMARY KEY (id), 
	CONSTRAINT ck_agent_runs_status CHECK (status IN ('completed','failed')), 
	CONSTRAINT ck_agent_runs_schema CHECK (schema_version = '2.0.0'), 
	CONSTRAINT ck_agent_runs_latency CHECK (latency_ms >= 0)
)""")
    op.execute("""CREATE INDEX ix_agent_runs_scope_created ON agent_runs (scope_id, created_at)""")


def downgrade():
    op.execute("DROP TABLE agent_runs")

