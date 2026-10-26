from decimal import Decimal

import pytest

from app.adapters.routing.metrics import route_cost_by_vehicle, total_transport_cost


def test_explicit_vehicle_rates_are_used():
    routes = [
        {"vehicle_id": "veh_a", "distance_m": 12500},
        {"vehicle_id": "veh_b", "distance_m": 5000},
    ]
    costs = route_cost_by_vehicle(routes, {"veh_a": Decimal("2.5"), "veh_b": Decimal("3")})
    assert costs == {"veh_a": Decimal("31.250"), "veh_b": Decimal("15")}
    assert total_transport_cost(routes, {"veh_a": Decimal("2.5"), "veh_b": Decimal("3")}) == Decimal("46.250")


def test_missing_rate_is_not_silently_defaulted():
    with pytest.raises(ValueError, match="missing_cost_rate:veh_a"):
        route_cost_by_vehicle([{"vehicle_id": "veh_a", "distance_m": 1000}], {})
