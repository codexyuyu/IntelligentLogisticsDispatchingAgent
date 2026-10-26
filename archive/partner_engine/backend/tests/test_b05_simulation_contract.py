from datetime import datetime, timezone
import pytest

from app.adapters.simulation.event_sources import build_events
from app.adapters.simulation.simpy_simulator import SimPySimulator, baseline_order_ids
from app.adapters.simulation.state_projection import project_state
from app.contracts.events import DispatchEvent, EventPayload, SimulationRequest
from app.contracts.entities import PlanningSnapshot, Order, Vehicle, Warehouse, WarehouseResource, StockLot, Operation, TravelMatrix
from app.contracts.common import Source, TimeWindow


def source():
    return Source(source_kind="user", source_ref="test", observed_at=datetime.now(timezone.utc), rule_version="test")

def minimal_snapshot():
    return PlanningSnapshot(
        snapshot_id="snap_sim_test", version=1, origin_at=datetime.now(timezone.utc), simulation_time_s=0,
        rule_version="test",
        orders=(Order(order_id="ord_001", version=1, warehouse_id="wh_1", batch_id="bat_1",
            delivery_node_id="node_c", quantity_units=1, weight_kg=1, volume_l=1, temperature_zone="chilled",
            service_window=TimeWindow(start_s=0, end_s=1000), service_duration_s=1, freshness_deadline_s=1000, source=source()),),
        vehicles=(Vehicle(vehicle_id="veh_1", version=1, warehouse_id="wh_1", start_node_id="node_w", end_node_id="node_w",
            current_node_id="node_w", capacity_weight_kg=1, capacity_volume_l=1, remaining_weight_kg=1, remaining_volume_l=1,
            temperature_zone="chilled", shift_window=TimeWindow(start_s=0, end_s=2000), available_at_s=0, source=source()),),
        warehouses=(Warehouse(warehouse_id="wh_1", version=1, node_id="node_w", temperature_zones=("chilled",)),),
        resources=(), stock_lots=(), operations=(), frozen_operations=(),
        matrix=TravelMatrix(matrix_id="mat_1", version=1, node_ids=("node_w", "node_c"),
            duration_s=((0, 10), (10, 0)), distance_m=((0, 100), (100, 0)), source=source()),
    )


def test_build_events_is_deterministic():
    snap=minimal_snapshot()
    events=(
        DispatchEvent(event_id="evt_b", event_type="departure_delayed", snapshot_id=snap.snapshot_id, expected_snapshot_version=1, object_id="veh_1", occurred_at_s=900, received_at=datetime.now(timezone.utc), source=source(), payload=EventPayload(delay_s=10)),
        DispatchEvent(event_id="evt_a", event_type="departure_delayed", snapshot_id=snap.snapshot_id, expected_snapshot_version=1, object_id="veh_1", occurred_at_s=300, received_at=datetime.now(timezone.utc), source=source(), payload=EventPayload(delay_s=10)),
    )
    req=SimulationRequest(snapshot=snap, events=events, horizon_s=1000, random_seed=17)
    assert [e.event_id for e in build_events(req)] == ["evt_a", "evt_b"]


def test_project_state_advances_only_clock():
    snap=minimal_snapshot()
    projected=project_state(snap, 123)
    assert projected.simulation_time_s == 123
    assert projected.snapshot_id == snap.snapshot_id
    assert projected.vehicles[0].available_at_s == 0


# --- R20: the replayed event stream covers every B-04 event type -----------------------

def _event(event_type, *, object_id="veh_1", occurred_at_s=0, payload=None, event_id="evt_x"):
    return DispatchEvent(event_id=event_id, event_type=event_type,
                         snapshot_id="snap_sim_test", expected_snapshot_version=1,
                         object_id=object_id, occurred_at_s=occurred_at_s,
                         received_at=datetime.now(timezone.utc), source=source(),
                         payload=payload or EventPayload())


def test_baseline_scope_uses_the_order_hint_only_for_departure_delays():
    snap = minimal_snapshot()
    extra = snap.orders[0].model_copy(update={"order_id": "ord_002", "batch_id": "bat_2"})
    two = snap.model_copy(update={"orders": snap.orders + (extra,)})
    delay = _event("departure_delayed", payload=EventPayload(affected_order_ids=("ord_001",)))
    quarantine = _event("cargo_quarantined", object_id="bat_1",
                        payload=EventPayload(affected_order_ids=("ord_001",)))
    dock = _event("dock_unavailable", object_id="wh_1",
                  payload=EventPayload(unavailable_until_s=600))

    # A departure delay names orders that share one route, so it may narrow the baseline.
    assert baseline_order_ids(two, (delay,)) == ("ord_001",)
    # A quarantine names blocked orders and a dock outage names a warehouse: narrowing the
    # baseline to those would simulate a plan that never contained the other orders.
    assert baseline_order_ids(two, (quarantine,)) == ("ord_001", "ord_002")
    assert baseline_order_ids(two, (dock,)) == ("ord_001", "ord_002")


def test_unsupported_event_types_are_rejected_before_any_solving(monkeypatch):
    snap = minimal_snapshot()
    weather = _event("weather_changed", object_id="mat_1")
    request = SimulationRequest(snapshot=snap, events=(weather,), horizon_s=1000, random_seed=17)

    def explode(*args, **kwargs):
        raise AssertionError("the baseline must not be solved for an unsupported event type")
    monkeypatch.setattr("app.adapters.simulation.simpy_simulator.coordinate", explode)
    with pytest.raises(ValueError, match="simulation_unsupported_event_types:weather_changed"):
        SimPySimulator().simulate(request)


def test_supported_event_types_pass_the_precheck(monkeypatch):
    snap = minimal_snapshot()
    events = (
        _event("departure_delayed", payload=EventPayload(delay_s=10), event_id="evt_delay"),
        _event("dock_unavailable", object_id="wh_1",
               payload=EventPayload(unavailable_until_s=600), event_id="evt_dock"),
        _event("cargo_quarantined", object_id="bat_1",
               payload=EventPayload(affected_order_ids=("ord_001",)), event_id="evt_quar"),
    )
    request = SimulationRequest(snapshot=snap, events=events, horizon_s=1000, random_seed=17)
    reached = {}

    def stop_here(*args, **kwargs):
        reached["baseline"] = True
        raise RuntimeError("stop-after-precheck")
    monkeypatch.setattr("app.adapters.simulation.simpy_simulator.coordinate", stop_here)
    with pytest.raises(RuntimeError, match="stop-after-precheck"):
        SimPySimulator().simulate(request)
    assert reached.get("baseline") is True
