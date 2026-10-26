"""Live OR-Tools regression: the same order can choose exactly one of two trucks.

Run on Windows with `python -m pytest -q backend/tests/transport/`.
Skipped only when the optional native OR-Tools dependency is absent.
"""
import json
from pathlib import Path
import pytest

from app.adapters.routing.ortools_solver import OrToolsRoutingSolver, pywrapcp
from app.contracts.entities import PlanningSnapshot
from app.contracts.planning import RoutingRequest
from app.domain.transport_rules import validate_transport


@pytest.mark.skipif(pywrapcp is None, reason="OR-Tools is not installed")
def test_one_required_order_with_two_compatible_vehicles_is_feasible():
    root = Path(__file__).resolve().parents[3]
    original = json.loads((root / "data/scenarios/two_warehouses_20_orders.json").read_text(encoding="utf-8"))
    first_order = next(o for o in original["orders"] if o["warehouse_id"] == "wh_1" and o["temperature_zone"] == "chilled")
    truck = next(v for v in original["vehicles"] if v["warehouse_id"] == "wh_1" and v["temperature_zone"] == "chilled")
    duplicate_truck = json.loads(json.dumps(truck))
    duplicate_truck["vehicle_id"] = "veh_test2"
    original["orders"] = [first_order]
    original["vehicles"] = [truck, duplicate_truck]
    original["operations"] = []
    original["stock_lots"] = [lot for lot in original["stock_lots"] if lot["batch_id"] == first_order["batch_id"]]
    snapshot = PlanningSnapshot.model_validate(original)
    request = RoutingRequest.model_validate({
        "snapshot": snapshot,
        "order_ids": [first_order["order_id"]],
        "warehouse_handoffs": [{
            "order_id": first_order["order_id"],
            "warehouse_id": "wh_1",
            "ready_at_s": 0,
            "loading_window": {"start_s": 0, "end_s": 32000},
        }],
        "budget": {"remaining_ms": 3000, "max_workers": 1, "random_seed": 17},
    })
    solved = OrToolsRoutingSolver().solve(request)
    assert solved.metadata.has_solution, solved.metadata.raw_status
    served = [oid for route in solved.routes for stop in route.stops for oid in stop.order_ids]
    assert served == [first_order["order_id"]]
    assert validate_transport(
        request=request.model_dump(mode="python"),
        result=solved.model_dump(mode="python"),
    ).passed
