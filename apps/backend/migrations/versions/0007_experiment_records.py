"""Experiment record table (frozen 0007)."""
from alembic import op

revision = "0007_experiment_records"
down_revision = "0006_decision_records"
branch_labels = None
depends_on = None


def upgrade():
    op.execute("""CREATE TABLE experiment_records (
	id UUID NOT NULL, 
	scope_id UUID NOT NULL, 
	status VARCHAR(32) NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	created_by UUID NOT NULL, 
	row_version BIGINT NOT NULL, 
	schema_version VARCHAR(16) NOT NULL, 
	base_label VARCHAR(128) NOT NULL, 
	candidate_label VARCHAR(128) NOT NULL, 
	orders_total BIGINT NOT NULL, 
	metric_version VARCHAR(32) NOT NULL, 
	base_result JSONB NOT NULL, 
	candidate_result JSONB NOT NULL, 
	comparison JSONB NOT NULL, 
	CONSTRAINT pk_experiment_records PRIMARY KEY (id), 
	CONSTRAINT ck_experiment_records_status CHECK (status IN ('completed','failed')), 
	CONSTRAINT ck_experiment_records_schema CHECK (schema_version = '2.0.0'), 
	CONSTRAINT ck_experiment_records_orders CHECK (orders_total >= 0)
)""")
    op.execute("""CREATE INDEX ix_experiment_records_scope_created ON experiment_records (scope_id, created_at)""")


def downgrade():
    op.execute("DROP TABLE experiment_records")

