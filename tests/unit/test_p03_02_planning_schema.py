"""Static checks for the frozen P03-02 planning migration and models (no database)."""

from __future__ import annotations

from pathlib import Path

from logistics_backend.persistence.planning_models import IMMUTABLE_TABLES, PLANNING_TABLES

ROOT = Path(__file__).resolve().parents[2]
MIGRATION = ROOT / "apps/backend/migrations/versions/0002_planning_runtime.py"


def test_planning_tables_cover_versions_tasks_inventory_audit_outbox() -> None:
    names = {table.name for table in PLANNING_TABLES}
    assert {
        "planning_snapshots", "schedules", "schedule_versions", "schedule_tasks",
        "transport_tasks", "warehouse_tasks", "routes", "route_stops",
        "optimization_requests", "optimization_results", "candidate_plans",
        "travel_matrices", "inventory_ledger", "reservations", "audit_entries",
        "outbox", "lifecycle_events",
    } <= names


def test_schedule_version_uniqueness_and_immutability_are_declared() -> None:
    versions = next(table for table in PLANNING_TABLES if table.name == "schedule_versions")
    unique = [constraint for constraint in versions.constraints
              if constraint.__class__.__name__ == "UniqueConstraint"]
    assert any(tuple(column.name for column in constraint.columns)
               == ("schedule_id", "version_no") for constraint in unique)
    assert "schedule_versions" not in IMMUTABLE_TABLES  # status changes remain append-only updates
    text = MIGRATION.read_text(encoding="utf-8")
    assert "CREATE TABLE schedule_versions" in text
    assert "uq_schedule_versions_number UNIQUE (schedule_id, version_no)" in text
    assert "protect_schedule_version_content" in text
    assert "no_delete_schedule_version" in text
    assert "CREATE SEQUENCE outbox_sequence" in text


def test_reservation_table_has_epoch_for_absolute_interval_checks() -> None:
    reservations = next(table for table in PLANNING_TABLES if table.name == "reservations")
    assert "epoch_utc" in reservations.c
    assert "expires_at_utc" in reservations.c
