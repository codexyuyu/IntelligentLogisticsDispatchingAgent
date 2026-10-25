"""Preparation bundle (data/preparation/competition-2026) through the real R30 solvers.

Oracle values come from docs/spec/TEST_FIXTURES.md, hand-computed independently of
OR-Tools/CP-SAT. A failure here means the solver, the importer, or the spec disagree.
"""
import json
from pathlib import Path

import pytest

from app.application.coordinator import coordinate
from app.contracts.entities import PlanningSnapshot

ROOT = Path(__file__).resolve().parents[2]


def load(scenario: str) -> PlanningSnapshot:
    path = ROOT / 'data' / 'scenarios' / f'prep_{scenario}.json'
    return PlanningSnapshot.model_validate(json.loads(path.read_text(encoding='utf-8')))


def plan(scenario: str, mode: str = 'sequential'):
    snap = load(scenario)
    oids = tuple(o.order_id for o in snap.orders)
    return snap, coordinate(snapshot=snap, order_ids=oids, budget_ms=20000,
                            max_coordination_rounds=3, coordination_mode=mode)


def test_t1_matches_hand_computed_route():
    _, p = plan('T1')
    assert p.validation.status == 'passed'
    assert len(p.routing.routes) == 1
    route = p.routing.routes[0]
    # TEST_FIXTURES T1: unique minimum D-A-B-D = 9000 m.
    assert route.distance_m == 9000
    deliveries = [s for s in route.stops if s.stop_kind == 'delivery']
    # Fixture A/B are generated with codes C1/C2.
    assert [s.node_id for s in deliveries] == ['node_T1_C1', 'node_T1_C2']
    # A arrival/start 300 depart 360; B arrival/start 560 depart 620.
    assert (deliveries[0].arrival_at_s, deliveries[0].departure_at_s) == (300, 360)
    assert (deliveries[1].arrival_at_s, deliveries[1].departure_at_s) == (560, 620)


def test_a8_serves_all_eight_and_never_mixes_zones():
    snap, p = plan('A8')
    assert p.validation.status == 'passed'
    assert not p.routing.unserved_orders
    zone_of_order = {o.order_id: o.temperature_zone for o in snap.orders}
    zone_of_vehicle = {v.vehicle_id: v.temperature_zone for v in snap.vehicles}
    for route in p.routing.routes:
        for stop in route.stops:
            for oid in stop.order_ids:
                assert zone_of_order[oid] == zone_of_vehicle[route.vehicle_id]


@pytest.mark.parametrize('mode', ['sequential', 'deep'])
def test_b20_two_warehouses_joint_plan_validates(mode):
    snap, p = plan('B20', mode)
    assert p.validation.status == 'passed'
    assert len({o.warehouse_id for o in snap.orders}) == 2
    assert len(p.warehouse.operations) == 100
    assert not p.routing.unserved_orders


def test_importer_output_matches_bundle():
    import subprocess
    import sys
    result = subprocess.run([sys.executable, str(ROOT / 'scripts' / 'import_preparation_bundle.py'), '--check'],
                            capture_output=True, text=True)
    assert result.returncode == 0, result.stdout + result.stderr
