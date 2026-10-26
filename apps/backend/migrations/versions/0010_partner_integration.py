"""Durable imports and R05/R08/R09 run evidence, separate from committed schedules."""
from alembic import op

revision = '0010_partner_integration'
down_revision = '0009_validation_reports'
branch_labels = None
depends_on = None


def upgrade():
    op.execute('''CREATE TABLE integration_scenarios (
        id UUID PRIMARY KEY, scope_id UUID NOT NULL, input_hash VARCHAR(64) NOT NULL,
        created_at TIMESTAMPTZ NOT NULL, created_by UUID NOT NULL, payload JSONB NOT NULL,
        CONSTRAINT uq_integration_scenarios_input UNIQUE(scope_id, input_hash))''')
    op.execute('''CREATE TABLE integration_runs (
        id UUID PRIMARY KEY, scope_id UUID NOT NULL,
        scenario_id UUID NOT NULL REFERENCES integration_scenarios(id),
        request_hash VARCHAR(64) NOT NULL, idempotency_key VARCHAR(128) NOT NULL,
        created_at TIMESTAMPTZ NOT NULL, created_by UUID NOT NULL, payload JSONB NOT NULL,
        CONSTRAINT uq_integration_runs_key UNIQUE(scope_id, idempotency_key))''')
    op.execute('CREATE INDEX ix_integration_runs_scope ON integration_runs(scope_id, created_at)')


def downgrade():
    op.execute('DROP TABLE integration_runs')
    op.execute('DROP TABLE integration_scenarios')
