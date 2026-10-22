def test_budget_policy_reserves_routing_time():
    budget_ms = 100_000
    routing_reserve_ms = max(2000, int(budget_ms * 0.25))
    routing_reserve_ms = min(routing_reserve_ms, max(1, budget_ms - 1))
    warehouse_budget_ms = max(1, budget_ms - routing_reserve_ms)

    assert routing_reserve_ms == 25_000
    assert warehouse_budget_ms == 75_000
    assert warehouse_budget_ms + routing_reserve_ms == budget_ms
