"""Metric record table (frozen 0008)."""
from alembic import op

revision = "0008_metric_records"
down_revision = "0007_experiment_records"
branch_labels = None
depends_on = None


def upgrade():
    op.execute("""CREATE TABLE metric_records (
	id UUID NOT NULL, 
	scope_id UUID NOT NULL, 
	status VARCHAR(32) NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	created_by UUID NOT NULL, 
	row_version BIGINT NOT NULL, 
	schema_version VARCHAR(16) NOT NULL, 
	code VARCHAR(64) NOT NULL, 
	definition_version VARCHAR(32) NOT NULL, 
	source VARCHAR(16) NOT NULL, 
	unit VARCHAR(32) NOT NULL, 
	value FLOAT, 
	numerator FLOAT, 
	denominator FLOAT, 
	reason VARCHAR(32), 
	sample_count BIGINT NOT NULL, 
	CONSTRAINT pk_metric_records PRIMARY KEY (id), 
	CONSTRAINT ck_metric_records_status CHECK (status IN ('active','deprecated')), 
	CONSTRAINT ck_metric_records_source CHECK (source IN ('planned','simulation','actual')), 
	CONSTRAINT ck_metric_records_schema CHECK (schema_version = '2.0.0'), 
	CONSTRAINT ck_metric_records_sample CHECK (sample_count >= 0), 
	CONSTRAINT ck_metric_records_value_reason CHECK ((value IS NULL) <> (reason IS NULL))
)""")
    op.execute("""CREATE INDEX ix_metric_records_code ON metric_records (scope_id, code, created_at)""")


def downgrade():
    op.execute("DROP TABLE metric_records")

