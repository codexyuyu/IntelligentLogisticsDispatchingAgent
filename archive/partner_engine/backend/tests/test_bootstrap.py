"""Composition-root tests: real graph, explicit injection, no adapter imports.

The point of these tests is that ``bootstrap`` builds the *real* adapters once,
and that every application entry point can be given an alternative graph instead
of constructing adapters itself. Nothing here installs a double globally.
"""
from __future__ import annotations

import datetime as dt
import inspect
from pathlib import Path

import pytest

from app.api.dependencies import get_services
from app.application import http_services
from app.application.coordinator import coordinate
from app.bootstrap import Services, build_services, describe_services
from app.contracts.entities import (
    Order,
    Operation,
    PlanningSnapshot,
    TravelMatrix,
    Vehicle,
    Warehouse,
    WarehouseResource,
)
from app.contracts.events import SimulationRequest, SimulationResult

ROOT = Path(__file__).resolve().parents[2]
ORIGIN = dt.datetime(2026, 10, 24, 0, 0, tzinfo=dt.timezone.utc)
SOURCE = {
    'source_kind': 'simulation',
    'source_ref': 'tests/test_bootstrap.py',
    'observed_at': '2026-10-24T00:00:00Z',
    'rule_version': 'bootstrap-test',
}


def _snapshot() -> PlanningSnapshot:
    return PlanningSnapshot(
        snapshot_id='snap_boot', version=1, origin_at=ORIGIN, simulation_time_s=0,
        rule_version='bootstrap-test',
        orders=(Order(order_id='ord_1', version=1, warehouse_id='wh_1', batch_id='bat_1',
                      delivery_node_id='node_2', quantity_units=1, weight_kg=10, volume_l=10,
                      temperature_zone='chilled',
                      service_window={'start_s': 0, 'end_s': 600},
                      service_duration_s=10, freshness_deadline_s=600, source=SOURCE),),
        vehicles=(Vehicle(vehicle_id='veh_1', version=1, warehouse_id='wh_1',
                          start_node_id='node_1', end_node_id='node_1',
                          current_node_id='node_1', capacity_weight_kg=100,
                          capacity_volume_l=100, remaining_weight_kg=100,
                          remaining_volume_l=100, temperature_zone='chilled',
                          shift_window={'start_s': 0, 'end_s': 600},
                          available_at_s=0, source=SOURCE),),
        warehouses=(Warehouse(warehouse_id='wh_1', version=1, node_id='node_1',
                              temperature_zones=('chilled',)),),
        resources=(WarehouseResource(resource_id='res_dock1', warehouse_id='wh_1', version=1,
                                     resource_kind='dock', capacity_units=1,
                                     available_windows=({'start_s': 0, 'end_s': 600},)),),
        stock_lots=(),
        operations=(Operation(operation_id='op_1', order_ids=('ord_1',), warehouse_id='wh_1',
                              resource_id='res_dock1', operation_kind='load',
                              duration_s=30, release_at_s=0, deadline_at_s=600),),
        matrix=TravelMatrix(matrix_id='matrix_boot', version=1,
                            node_ids=('node_1', 'node_2'),
                            duration_s=((0, 60), (60, 0)),
                            distance_m=((0, 1000), (1000, 0)), source=SOURCE),
    )


class FakeScheduler:
    """Double used only inside this test, never installed into bootstrap."""

    def __init__(self):
        self.calls = 0

    def schedule(self, request):
        self.calls += 1
        raise RuntimeError('FAKE_SCHEDULER_CALLED')


class FakeSimulator:
    def __init__(self, snapshot):
        self.snapshot = snapshot
        self.calls = 0

    def simulate(self, request):
        self.calls += 1
        return SimulationResult(simulation_id='sim_fake', base_snapshot_id=request.snapshot.snapshot_id,
                                final_snapshot=self.snapshot, emitted_events=())


class FakeServices(Services):
    def __init__(self, *, scheduler=FakeScheduler(), simulator=None):
        object.__setattr__(self, 'routing', object())
        object.__setattr__(self, 'warehouse_scheduler', scheduler)
        object.__setattr__(self, 'warehouse_validator', object())
        object.__setattr__(self, 'simulator', simulator or object())


# --------------------------------------------------------------------------- #
# The real graph
# --------------------------------------------------------------------------- #

def test_build_services_returns_the_real_adapters():
    services = build_services()

    assert type(services.routing).__name__ == 'OrToolsRoutingSolver'
    assert type(services.warehouse_scheduler).__name__ == 'CpSatWarehouseScheduler'
    assert type(services.warehouse_validator).__name__ == 'WarehouseScheduleValidator'
    assert type(services.simulator).__name__ == 'SimPySimulator'
    for component in ('solve',):
        assert hasattr(services.routing, component)
    assert hasattr(services.warehouse_scheduler, 'schedule')
    assert hasattr(services.warehouse_validator, 'validate')
    assert hasattr(services.simulator, 'simulate')


def test_build_services_is_cached_for_the_process():
    assert build_services() is build_services()


def test_build_services_takes_no_test_double_switch():
    # A composition root with an override parameter invites doubles into startup.
    assert inspect.signature(build_services).parameters == {}


def test_describe_services_lists_components_without_secrets():
    described = describe_services()

    assert described == {
        'routing': 'OrToolsRoutingSolver',
        'warehouse_scheduler': 'CpSatWarehouseScheduler',
        'warehouse_validator': 'WarehouseScheduleValidator',
        'simulator': 'SimPySimulator',
    }


def test_http_dependency_returns_the_same_graph():
    assert get_services() is build_services()


# --------------------------------------------------------------------------- #
# Injection: the application layer accepts an alternative graph
# --------------------------------------------------------------------------- #

def test_coordinate_uses_the_injected_scheduler_instead_of_building_adapters():
    scheduler = FakeScheduler()
    services = FakeServices(scheduler=scheduler)

    with pytest.raises(RuntimeError, match='FAKE_SCHEDULER_CALLED'):
        coordinate(snapshot=_snapshot(), order_ids=('ord_1',), budget_ms=1000,
                   services=services)

    assert scheduler.calls == 1


def test_submit_simulation_uses_the_injected_simulator():
    snapshot = _snapshot()
    simulator = FakeSimulator(snapshot)
    fake = FakeServices(simulator=simulator)
    body = SimulationRequest(snapshot=snapshot, events=(), horizon_s=3600)

    accepted = http_services.submit_simulation(body, 'boot-test-1', fake)

    assert simulator.calls == 1
    assert accepted.simulation_id == 'sim_fake'
    job = http_services.get_job(accepted.job_id)
    assert job.status == 'succeeded'


# --------------------------------------------------------------------------- #
# The architecture rule this refactor exists for
# --------------------------------------------------------------------------- #

def test_application_layer_imports_no_adapter():
    offenders = [
        path.name for path in (ROOT / 'backend' / 'app' / 'application').glob('*.py')
        if 'app.adapters' in path.read_text(encoding='utf-8')
    ]
    assert offenders == []


def test_application_and_domain_never_name_an_adapter_class():
    offenders = []
    for folder in ('backend/app/application', 'backend/app/domain'):
        for path in (ROOT / folder).rglob('*.py'):
            if 'app.adapters' in path.read_text(encoding='utf-8'):
                offenders.append(path.name)
    assert offenders == []


def test_api_route_adapter_debt_is_recorded_not_silently_ignored():
    """The local PostgreSQL / Agent demo subapp still imports adapters directly.

    Those routes are a separate demo surface outside this task's scope; the list
    is pinned so the debt stays visible and shrinks deliberately, not by accident.
    """
    offenders = sorted({
        path.name for path in (ROOT / 'backend' / 'app' / 'api').rglob('*.py')
        if 'app.adapters' in path.read_text(encoding='utf-8')
    })
    assert offenders == ['agent_demo.py', 'postgres_demo.py']

