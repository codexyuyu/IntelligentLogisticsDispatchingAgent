"""Explicit live acceptance: pytest tests/persistence/pg_acceptance.py.

DSH_TEST_DATABASE_URL must name an isolated disposable PostgreSQL database.
No skips/fakes: missing configuration fails. Migration is explicit below.
"""
import json
import os
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from uuid import uuid4
import psycopg
import pytest
from app.contracts.entities import PlanningSnapshot
from app.adapters.persistence.pg_snapshot_store import PgSnapshotStore, SnapshotVersionConflict

@pytest.fixture
def store():
    dsn=os.environ['DSH_TEST_DATABASE_URL']
    with psycopg.connect(dsn) as conn:
        conn.execute((Path(__file__).resolve().parents[2]/'migrations/DSH_001_snapshots.sql').read_text())
    return PgSnapshotStore(lambda:psycopg.connect(dsn))

@pytest.fixture
def snap():
    root=Path(__file__).resolve().parents[3]
    value=PlanningSnapshot.model_validate(json.loads((root/'data/scenarios/prep_T1.json').read_text(encoding='utf-8')))
    return value.model_copy(update={'snapshot_id':'snap_test_'+uuid4().hex})

def test_roundtrip_and_conflicts(store,snap):
    store.save_snapshot(snap,expected_previous_version=None)
    store.save_snapshot(snap,expected_previous_version=None)
    assert store.get_snapshot(snap.snapshot_id,1)==snap
    with pytest.raises(SnapshotVersionConflict): store.get_snapshot(snap.snapshot_id,2)
    with pytest.raises(KeyError): store.get_snapshot('snap_missing_'+uuid4().hex,1)
    with pytest.raises(SnapshotVersionConflict):
        store.save_snapshot(snap.model_copy(update={'rule_version':'changed'}),expected_previous_version=None)
    assert store.get_snapshot(snap.snapshot_id,1)==snap

def test_compare_and_swap_concurrent(store,snap):
    store.save_snapshot(snap,expected_previous_version=None)
    def write(rule):
        try:
            store.save_snapshot(snap.model_copy(update={'version':2,'rule_version':rule}),expected_previous_version=1)
            return 'success'
        except SnapshotVersionConflict: return 'conflict'
    with ThreadPoolExecutor(max_workers=2) as pool:
        assert sorted(pool.map(write,['rule-a','rule-b']))==['conflict','success']
    assert store.get_snapshot(snap.snapshot_id,2).rule_version in ('rule-a','rule-b')
    with pytest.raises(SnapshotVersionConflict): store.get_snapshot(snap.snapshot_id,1)
