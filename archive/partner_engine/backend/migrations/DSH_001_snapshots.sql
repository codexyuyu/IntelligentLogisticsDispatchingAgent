-- Explicit opt-in migration; does not change existing business tables.
BEGIN;
CREATE SCHEMA IF NOT EXISTS dsh_planning;
CREATE TABLE IF NOT EXISTS dsh_planning.snapshots (
    snapshot_id text NOT NULL,
    version integer NOT NULL CHECK (version > 0),
    payload jsonb NOT NULL,
    PRIMARY KEY (snapshot_id, version),
    CHECK (jsonb_typeof(payload) = 'object'),
    CHECK (payload ? 'snapshot_id' AND payload ? 'version'),
    CHECK (payload->>'snapshot_id' = snapshot_id),
    CHECK ((payload->>'version')::integer = version)
);
COMMIT;
