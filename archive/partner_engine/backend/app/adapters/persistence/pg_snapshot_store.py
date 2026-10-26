"""DSH: immutable PostgreSQL snapshots; explicit migration, no startup DDL."""
from collections.abc import Callable

import psycopg
from psycopg.types.json import Jsonb

from app.contracts.entities import PlanningSnapshot


class SnapshotVersionConflict(ValueError):
    pass


class PgSnapshotStore:
    """Implements PlanningSnapshotStore; factory returns a NEW connection per call.

    Snapshot identity denotes one history. Re-importing identical content is
    idempotent; changing content at the same version is always rejected.
    """

    def __init__(self, connect: Callable[[], psycopg.Connection]):
        self._connect = connect

    def get_snapshot(self, snapshot_id: str, expected_version: int) -> PlanningSnapshot:
        if type(expected_version) is not int or expected_version < 1:
            raise ValueError('expected_version must be a positive integer')
        with self._connect() as conn:
            if conn.autocommit:
                raise ValueError("snapshot_store_requires_transactional_connection")
            conn.execute('SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY')
            row = conn.execute(
                'SELECT version, payload FROM dsh_planning.snapshots '
                'WHERE snapshot_id = %s ORDER BY version DESC LIMIT 1',
                (snapshot_id,),
            ).fetchone()
            if row is None:
                raise KeyError(snapshot_id)
            if row[0] != expected_version:
                raise SnapshotVersionConflict(f'snapshot_version_conflict:{snapshot_id}')
            snapshot = PlanningSnapshot.model_validate(row[1])
            if snapshot.snapshot_id != snapshot_id or snapshot.version != row[0]:
                raise ValueError('stored_snapshot_identity_mismatch')
            return snapshot

    def save_snapshot(self, snapshot: PlanningSnapshot, *, expected_previous_version: int | None) -> None:
        """Import-only helper, not a new public HTTP/port contract.

        New identity: previous=None, version=1. Updates: expected previous head,
        version=previous+1. Version conflict rolls back without partial writes.
        """
        snapshot = PlanningSnapshot.model_validate(snapshot.model_dump(mode='json'))
        if expected_previous_version is not None and (
            type(expected_previous_version) is not int or expected_previous_version < 1
        ):
            raise ValueError('expected_previous_version must be positive or None')
        if snapshot.version != (expected_previous_version or 0) + 1:
            raise SnapshotVersionConflict('snapshot_version_not_successor')
        payload = snapshot.model_dump(mode='json')
        with self._connect() as conn:
            if conn.autocommit:
                raise ValueError("snapshot_store_requires_transactional_connection")
            conn.execute('SET TRANSACTION ISOLATION LEVEL READ COMMITTED')
            # Serializes imports for this identity, including concurrent first insert.
            conn.execute('SELECT pg_advisory_xact_lock(hashtextextended(%s, 0))',
                         ('dsh.snapshot:' + snapshot.snapshot_id,))
            current = conn.execute(
                'SELECT version, payload FROM dsh_planning.snapshots '
                'WHERE snapshot_id = %s ORDER BY version DESC LIMIT 1',
                (snapshot.snapshot_id,),
            ).fetchone()
            if current and current[0] == snapshot.version and current[1] == payload:
                return
            if (current[0] if current else None) != expected_previous_version:
                raise SnapshotVersionConflict('snapshot_compare_and_swap_failed')
            conn.execute(
                'INSERT INTO dsh_planning.snapshots(snapshot_id, version, payload) VALUES (%s, %s, %s)',
                (snapshot.snapshot_id, snapshot.version, Jsonb(payload)),
            )
