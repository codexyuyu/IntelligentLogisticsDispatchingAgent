"""Persist independently reconciled, planned integration replay events."""

from alembic import op

revision = "0011_integration_timeline"
down_revision = "0010_partner_integration"
branch_labels = None
depends_on = None


def upgrade():
    op.execute("""CREATE TABLE integration_timeline_events (
        id UUID PRIMARY KEY,
        scope_id UUID NOT NULL,
        run_id UUID NOT NULL REFERENCES integration_runs(id) ON DELETE RESTRICT,
        sequence BIGINT NOT NULL,
        time_s BIGINT NOT NULL,
        kind VARCHAR(40) NOT NULL,
        created_at TIMESTAMPTZ NOT NULL,
        payload JSONB NOT NULL,
        CONSTRAINT uq_integration_timeline_run_sequence UNIQUE (run_id, sequence),
        CONSTRAINT ck_integration_timeline_events_timeline_nonnegative
            CHECK (sequence >= 0 AND time_s >= 0),
        CONSTRAINT ck_integration_timeline_events_timeline_payload_identity
            CHECK (payload->>'id' = id::text AND (payload->>'sequence')::bigint = sequence
                   AND payload->>'kind' = kind)
    )""")
    op.execute("""CREATE INDEX ix_integration_timeline_scope_run
                  ON integration_timeline_events (scope_id, run_id, sequence)""")


def downgrade():
    op.execute("DROP TABLE integration_timeline_events")
