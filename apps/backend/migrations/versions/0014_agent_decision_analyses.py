"""Persist grounded AI analysis of dispatch candidates and simulation incidents."""
from alembic import op
revision = '0014_agent_decision_analyses'
down_revision = '0013_agent_dispatch_tasks'
branch_labels = None
depends_on = None


def upgrade():
    op.execute('''CREATE TABLE agent_decision_analyses (
        id UUID PRIMARY KEY,
        scope_id UUID NOT NULL,
        actor_id UUID NOT NULL,
        run_id UUID NOT NULL REFERENCES integration_runs(id),
        target_type VARCHAR(24) NOT NULL CHECK (target_type IN ('dispatch_task','incident')),
        target_id UUID NOT NULL,
        created_at TIMESTAMPTZ NOT NULL,
        question TEXT NOT NULL,
        reply TEXT NOT NULL,
        model VARCHAR(128),
        status VARCHAR(32) NOT NULL CHECK (status IN ('model_success','model_unavailable','model_failed')),
        error_code VARCHAR(64),
        tool_trace JSONB NOT NULL,
        evidence JSONB NOT NULL,
        recommendation VARCHAR(32)
    )''')
    op.execute('CREATE INDEX ix_agent_decision_analyses_target ON agent_decision_analyses (scope_id, target_type, target_id, created_at DESC)')


def downgrade():
    op.execute('DROP TABLE agent_decision_analyses')
