"""Real PostgreSQL checks for P03-03 capture (requires TEST_DATABASE_URL)."""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

import pytest
from sqlalchemy import create_engine

from logistics_backend.persistence.snapshots import PlanningSnapshotStore
from logistics_backend.persistence.uow import UnitOfWork
from logistics_domain.planning import PlanningScope

pytestmark = pytest.mark.requires_postgres


def test_empty_scope_capture_is_consistent(database_url: str) -> None:
    engine = create_engine(database_url, pool_pre_ping=True)
    try:
        store = PlanningSnapshotStore(
            lambda **options: UnitOfWork(engine, **options), uuid4())
        scope = PlanningScope((), (), (), datetime(2026, 1, 1, tzinfo=timezone.utc), 3600)
        snapshot = store.capture(scope)
        assert snapshot.scope == scope
        assert snapshot.orders == ()
        assert snapshot.cargo == ()
        assert snapshot.vehicles == ()
        assert snapshot.drivers == ()
        assert snapshot.resources.warehouses == ()
        assert snapshot.inventory == ()
        assert snapshot.revisions == ()
        assert len(snapshot.hash) == 64
    finally:
        engine.dispose()
