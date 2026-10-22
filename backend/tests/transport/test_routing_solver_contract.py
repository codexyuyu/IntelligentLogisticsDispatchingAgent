from pathlib import Path


def test_routing_solver_uses_versioned_matrix_adapter_and_service_time():
    source = Path(__file__).resolve().parents[2] / "app/adapters/routing/ortools_solver.py"
    text = source.read_text(encoding="utf-8")
    assert "FixedTravelMatrixProvider.from_snapshot" in text
    assert "get_matrix(snapshot.matrix.matrix_id, snapshot.matrix.version)" in text
    assert "service_duration_s" in text
    assert "AddDimension" in text
    assert "RoutingModel" in text


def test_cost_is_sidecar_until_shared_contract_gains_cost_field():
    source = Path(__file__).resolve().parents[2] / "app/adapters/routing/metrics.py"
    text = source.read_text(encoding="utf-8")
    assert "shared RoutingResult contract" in text


def test_required_orders_use_disjunction_when_multiple_compatible_vehicle_copies_exist():
    source = Path(__file__).resolve().parents[2] / "app/adapters/routing/ortools_solver.py"
    text = source.read_text(encoding="utf-8")
    marker = "# Every physical copy is a routing node. Required orders must choose"
    assert marker in text
    assert "routing.AddDisjunction(" in text
    assert "if order.required:\n                solver.Add(sum(active_vars) == 1)" in text


def test_r14_inactive_vehicle_copies_are_not_forced_active():
    # R12/R13 fixed VehicleVar for every copy, but an inactive copy must have
    # vehicle=-1. That contradicts the disjunction when two trucks are eligible.
    # R20 replaced the arithmetic form with the native two-value domain, because the
    # arithmetic form also stopped the local search from ever activating another
    # vehicle's copy (measured: 3100 m returned where 2200 m exists).
    source = Path(__file__).resolve().parents[2] / "app/adapters/routing/ortools_solver.py"
    text = source.read_text(encoding="utf-8")
    assert "routing.VehicleVar(index).SetValues([vehicle_idx, -1])" in text
    assert "routing.VehicleVar(index).SetValue(vehicle_idx)" not in text
    assert "routing.VehicleVar(index) == (vehicle_idx + 1) * active - 1" not in text


def test_r14_capacity_precheck_excludes_optional_orders():
    source = Path(__file__).resolve().parents[2] / "app/adapters/routing/ortools_solver.py"
    text = source.read_text(encoding="utf-8")
    assert "if o.required and o.temperature_zone == zone" in text
