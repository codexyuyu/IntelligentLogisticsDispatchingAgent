"""A separate durable simulation projection and single-incident review record."""

from alembic import op

revision = '0012_integration_simulation'
down_revision = '0011_integration_timeline'
branch_labels = None
depends_on = None


def upgrade():
    op.execute("""CREATE TABLE integration_simulations (
        id UUID PRIMARY KEY,
        scope_id UUID NOT NULL,
        run_id UUID NOT NULL REFERENCES integration_runs(id) ON DELETE RESTRICT,
        created_at TIMESTAMPTZ NOT NULL,
        created_by UUID NOT NULL,
        payload JSONB NOT NULL,
        CONSTRAINT uq_integration_simulations_run UNIQUE (run_id),
        CONSTRAINT ck_integration_simulations_payload_identity
            CHECK (payload->>'id' = id::text AND payload->>'run_id' = run_id::text)
    )""")
    op.execute("""CREATE INDEX ix_integration_simulations_scope_run
                  ON integration_simulations (scope_id, run_id)""")
    op.execute("""CREATE TABLE integration_simulation_incidents (
        id UUID PRIMARY KEY,
        scope_id UUID NOT NULL,
        simulation_id UUID NOT NULL REFERENCES integration_simulations(id) ON DELETE RESTRICT,
        event_id UUID NOT NULL REFERENCES events(id) ON DELETE RESTRICT,
        status VARCHAR(16) NOT NULL,
        row_version BIGINT NOT NULL,
        created_at TIMESTAMPTZ NOT NULL,
        updated_at TIMESTAMPTZ NOT NULL,
        created_by UUID NOT NULL,
        payload JSONB NOT NULL,
        CONSTRAINT uq_integration_simulation_one_incident UNIQUE (simulation_id),
        CONSTRAINT uq_integration_simulation_incident_event UNIQUE (event_id),
        CONSTRAINT ck_integration_simulation_incidents_status
            CHECK (status IN ('pending','approved','rejected')),
        CONSTRAINT ck_integration_simulation_incidents_row_version_nonnegative
            CHECK (row_version >= 0),
        CONSTRAINT ck_integration_simulation_incidents_payload_identity
            CHECK (payload->>'id' = id::text AND payload->>'simulation_id' = simulation_id::text)
    )""")
    op.execute("""CREATE INDEX ix_integration_simulation_incidents_scope
                  ON integration_simulation_incidents (scope_id, simulation_id)""")


def downgrade():
    op.execute('DROP TABLE integration_simulation_incidents')
    op.execute('DROP TABLE integration_simulations')
