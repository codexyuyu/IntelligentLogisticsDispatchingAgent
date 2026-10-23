"""Unit checks for the P02-03 planning values (no database, no framework)."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest

from logistics_domain.errors import InvalidInputError
from logistics_domain.planning import (
    PlanningScope,
    PlanningSnapshot,
    ScheduleVersion,
    ValidationReport,
    content_hash,
    project_calendar,
)
from logistics_domain.primitives import CalendarInterval, ResourceCalendar
from logistics_domain.resources import ResourceBundle
from logistics_domain.states import EntityState

EPOCH = datetime(2026, 1, 1, tzinfo=timezone.utc)
HASH = "a" * 64


def _bundle() -> ResourceBundle:
    return ResourceBundle((), (), (), (), (), (), ())


def _scope(epoch: datetime = EPOCH, horizon: int = 3600) -> PlanningScope:
    return PlanningScope((), (), (), epoch, horizon)


def test_snapshot_hash_is_reproducible_and_verified() -> None:
    snapshot = PlanningSnapshot.create(
        id=uuid4(), scope=_scope(), orders=(), cargo=(), vehicles=(), drivers=(),
        resources=_bundle(), inventory=(), revisions=(), matrices=())
    assert len(snapshot.hash) == 64
    assert snapshot.hash == content_hash({
        "id": snapshot.id, "scope": snapshot.scope, "orders": snapshot.orders,
        "cargo": snapshot.cargo, "vehicles": snapshot.vehicles, "drivers": snapshot.drivers,
        "resources": snapshot.resources, "inventory": snapshot.inventory,
        "revisions": snapshot.revisions, "matrices": snapshot.matrices,
    })


def test_calendar_projection_clips_and_rebases() -> None:
    calendar = ResourceCalendar(epoch_utc=EPOCH, intervals=(
        CalendarInterval(0, 10, 2), CalendarInterval(10, 120, 1)), version=3)
    projected = project_calendar(calendar, _scope(EPOCH + timedelta(seconds=5), 100))
    assert projected.epoch_utc == EPOCH + timedelta(seconds=5)
    assert [(item.start_s, item.end_s, item.available_units) for item in projected.intervals] == [
        (0, 5, 2), (5, 100, 1)]
    empty = project_calendar(calendar, _scope(EPOCH + timedelta(seconds=500), 10))
    assert empty.intervals == ()


def test_schedule_version_rejects_self_parent() -> None:
    version_id = uuid4()
    with pytest.raises(InvalidInputError):
        ScheduleVersion(
            id=version_id, status=EntityState.CANDIDATE, created_at=EPOCH, updated_at=EPOCH,
            row_version=0, schema_version="2.0.0", created_by=uuid4(), schedule_id=uuid4(),
            version_no=1, parent_version_id=version_id, snapshot_id=uuid4(),
            content_hash=HASH, reason="initial", event_id=None, task_refs=(),
            validation_report_ref=uuid4())


def test_validation_report_with_unsupported_rule_cannot_be_valid() -> None:
    with pytest.raises(InvalidInputError):
        ValidationReport(
            id=uuid4(), candidate_hash=HASH, snapshot_hash=HASH, rules_version="1.0.0",
            valid=True, required_codes=("x",), checked_codes=("x",),
            unsupported_codes=("x",), violations=(), validated_at=EPOCH)
