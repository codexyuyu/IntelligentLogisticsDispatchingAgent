"""Decision record audit table (frozen 0006)."""
from alembic import op

revision = "0006_decision_records"
down_revision = "0005_tool_calls"
branch_labels = None
depends_on = None


def upgrade():
    op.execute("""CREATE TABLE decision_records (
	id UUID NOT NULL, 
	scope_id UUID NOT NULL, 
	status VARCHAR(32) NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	created_by UUID NOT NULL, 
	row_version BIGINT NOT NULL, 
	schema_version VARCHAR(16) NOT NULL, 
	run_id UUID, 
	tool_call_id UUID, 
	decision_type VARCHAR(64) NOT NULL, 
	payload JSONB NOT NULL, 
	rationale TEXT NOT NULL, 
	confidence FLOAT NOT NULL, 
	evidence_refs JSONB NOT NULL, 
	CONSTRAINT pk_decision_records PRIMARY KEY (id), 
	CONSTRAINT ck_decision_records_status CHECK (status IN ('proposed','accepted','rejected','superseded')), 
	CONSTRAINT ck_decision_records_schema CHECK (schema_version = '2.0.0'), 
	CONSTRAINT ck_decision_records_confidence CHECK (confidence >= 0 AND confidence <= 1), 
	CONSTRAINT fk_decision_records_run_id_agent_runs FOREIGN KEY(run_id) REFERENCES agent_runs (id) ON DELETE SET NULL, 
	CONSTRAINT fk_decision_records_tool_call_id_tool_calls FOREIGN KEY(tool_call_id) REFERENCES tool_calls (id) ON DELETE SET NULL
)""")
    op.execute("""CREATE INDEX ix_decision_records_scope_created ON decision_records (scope_id, created_at)""")


def downgrade():
    op.execute("DROP TABLE decision_records")

