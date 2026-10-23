"""Tool-call audit table (frozen 0005)."""
from alembic import op

revision = "0005_tool_calls"
down_revision = "0004_agent_runs"
branch_labels = None
depends_on = None


def upgrade():
    op.execute("""CREATE TABLE tool_calls (
	id UUID NOT NULL, 
	scope_id UUID NOT NULL, 
	status VARCHAR(32) NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	created_by UUID NOT NULL, 
	row_version BIGINT NOT NULL, 
	schema_version VARCHAR(16) NOT NULL, 
	run_id UUID, 
	tool_name VARCHAR(64) NOT NULL, 
	arguments JSONB NOT NULL, 
	result JSONB, 
	error_code VARCHAR(64), 
	duration_ms BIGINT NOT NULL, 
	trace_id UUID NOT NULL, 
	CONSTRAINT pk_tool_calls PRIMARY KEY (id), 
	CONSTRAINT ck_tool_calls_status CHECK (status IN ('requested','authorized','running','succeeded','failed','denied','cancelled')), 
	CONSTRAINT ck_tool_calls_schema CHECK (schema_version = '2.0.0'), 
	CONSTRAINT ck_tool_calls_duration CHECK (duration_ms >= 0), 
	CONSTRAINT fk_tool_calls_run_id_agent_runs FOREIGN KEY(run_id) REFERENCES agent_runs (id) ON DELETE SET NULL
)""")
    op.execute("""CREATE INDEX ix_tool_calls_scope_created ON tool_calls (scope_id, created_at)""")


def downgrade():
    op.execute("DROP TABLE tool_calls")

