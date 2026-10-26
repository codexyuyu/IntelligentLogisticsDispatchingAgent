from pathlib import Path
import json

import pytest

from app.adapters.matrix.fixed import FixedTravelMatrixProvider
from app.contracts.entities import PlanningSnapshot

ROOT = Path(__file__).resolve().parents[2]
SCENARIO = ROOT / "../data/scenarios/two_warehouses_20_orders.json"


def snapshot():
    return PlanningSnapshot.model_validate(json.loads(SCENARIO.read_text(encoding="utf-8")))


def test_fixed_provider_enforces_matrix_version_and_preserves_unreachable():
    snap = snapshot()
    provider = FixedTravelMatrixProvider.from_snapshot(snap)
    got = provider.get_matrix(snap.matrix.matrix_id, snap.matrix.version)
    assert got.node_ids == snap.matrix.node_ids
    with pytest.raises(ValueError, match="matrix_version_conflict"):
        provider.get_matrix(snap.matrix.matrix_id, snap.matrix.version + 1)


def test_fixed_provider_lookup_is_versioned_and_node_ordered():
    snap = snapshot()
    matrix = snap.matrix
    duration, distance = FixedTravelMatrixProvider.lookup(matrix, "node_wh1", "node_c001")
    assert duration >= 0
    assert distance >= 0
    with pytest.raises(ValueError, match="matrix_unknown_node"):
        FixedTravelMatrixProvider.lookup(matrix, "node_missing", "node_c001")
