"""Real PostgreSQL checks for the frozen P03-02 migration (requires TEST_DATABASE_URL)."""

from __future__ import annotations

import pytest

pytestmark = pytest.mark.requires_postgres


def test_migration_created_planning_tables(db_cursor) -> None:
    db_cursor.execute(
        "select table_name from information_schema.tables "
        "where table_schema = 'public' and table_name in ("
        "'planning_snapshots','schedules','schedule_versions','schedule_tasks',"
        "'transport_tasks','warehouse_tasks','routes','route_stops',"
        "'optimization_requests','optimization_results','candidate_plans',"
        "'travel_matrices','inventory_ledger','reservations','audit_entries',"
        "'outbox','lifecycle_events')")
    found = {row[0] for row in db_cursor.fetchall()}
    assert found == {
        "planning_snapshots", "schedules", "schedule_versions", "schedule_tasks",
        "transport_tasks", "warehouse_tasks", "routes", "route_stops",
        "optimization_requests", "optimization_results", "candidate_plans",
        "travel_matrices", "inventory_ledger", "reservations", "audit_entries",
        "outbox", "lifecycle_events"}


def test_version_uniqueness_and_triggers_exist(db_cursor) -> None:
    db_cursor.execute(
        "select conname from pg_constraint where conname = 'uq_schedule_versions_number'")
    assert db_cursor.fetchone() is not None
    db_cursor.execute(
        "select tgname from pg_trigger where not tgisinternal and tgname = any(%s)",
        (["protect_schedule_version", "no_delete_schedule_version",
          "immutable_planning_snapshots", "immutable_inventory_ledger"],))
    found = {row[0] for row in db_cursor.fetchall()}
    assert found == {"protect_schedule_version", "no_delete_schedule_version",
                     "immutable_planning_snapshots", "immutable_inventory_ledger"}


def test_reservation_epoch_column_exists(db_cursor) -> None:
    db_cursor.execute(
        "select column_name from information_schema.columns "
        "where table_schema='public' and table_name='reservations' "
        "and column_name in ('epoch_utc','expires_at_utc','start_s','end_s')")
    assert {row[0] for row in db_cursor.fetchall()} == {
        "epoch_utc", "expires_at_utc", "start_s", "end_s"}
