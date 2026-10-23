"""Validation report table (frozen 0009)."""
from alembic import op

revision = "0009_validation_reports"
down_revision = "0008_metric_records"
branch_labels = None
depends_on = None


def upgrade():
    op.execute("""CREATE TABLE validation_reports (
	id UUID NOT NULL, 
	scope_id UUID NOT NULL, 
	candidate_id UUID NOT NULL, 
	candidate_hash VARCHAR(64) NOT NULL, 
	snapshot_hash VARCHAR(64) NOT NULL, 
	rules_version VARCHAR(32) NOT NULL, 
	valid BOOLEAN NOT NULL, 
	report JSONB NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	created_by UUID NOT NULL, 
	CONSTRAINT pk_validation_reports PRIMARY KEY (id), 
	CONSTRAINT ck_validation_reports_distinct_hashes CHECK (candidate_hash <> snapshot_hash), 
	CONSTRAINT uq_validation_reports_candidate UNIQUE (candidate_id)
)""")
    op.execute("""CREATE INDEX ix_validation_reports_candidate ON validation_reports (scope_id, candidate_id)""")


def downgrade():
    op.execute("DROP TABLE validation_reports")

