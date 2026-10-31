"""Persist natural-language dispatch proposals and human decisions.

Does not mutate any existing integration, simulation, inventory or schedule data.
"""
from alembic import op
revision = '0013_agent_dispatch_tasks'
down_revision = '0012_integration_simulation'
branch_labels = None
depends_on = None


def upgrade():
    op.execute('''CREATE TABLE agent_dispatch_tasks (
        id UUID PRIMARY KEY,
        scope_id UUID NOT NULL,
        actor_id UUID NOT NULL,
        source_run_id UUID NOT NULL REFERENCES integration_runs(id),
        candidate_run_id UUID REFERENCES integration_runs(id),
        status VARCHAR(24) NOT NULL,
        row_version BIGINT NOT NULL DEFAULT 0,
        created_at TIMESTAMPTZ NOT NULL,
        updated_at TIMESTAMPTZ NOT NULL,
        instruction TEXT NOT NULL,
        intent JSONB NOT NULL,
        evidence JSONB NOT NULL,
        parser VARCHAR(24) NOT NULL,
        incident_id UUID,
        CONSTRAINT ck_agent_dispatch_task_status CHECK (status IN ('draft','solving','ready','approved','rejected','failed')),
        CONSTRAINT ck_agent_dispatch_task_version CHECK (row_version >= 0)
    )''')
    op.execute('CREATE INDEX ix_agent_dispatch_tasks_scope_created ON agent_dispatch_tasks (scope_id, created_at DESC)')


def downgrade():
    op.execute('DROP TABLE agent_dispatch_tasks')
