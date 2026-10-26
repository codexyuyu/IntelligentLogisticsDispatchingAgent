# R12 Routing scale fix

## Root cause
B02 Routing creates one internal copy of each order for every compatible vehicle. In the previous implementation, required orders were constrained to `sum(active_vars) == 1`, but their copies were not placed in a routing disjunction. OR-Tools therefore treated every required copy as mandatory. This is invisible in S20 when each temperature zone has only one compatible vehicle, but becomes infeasible in S50/S100 after the benchmark generator creates multiple compatible vehicles per zone.

## Fix
Required orders now also place their compatible copies in `routing.AddDisjunction(..., 0, 1)`, while keeping `sum(active_vars) == 1`. This means exactly one compatible copy is active, so exactly one compatible vehicle serves the required order.

Optional orders keep the existing penalty-based disjunction and `sum(active_vars) <= 1` behavior.

## Scope
Only `backend/app/adapters/routing/ortools_solver.py` and its regression test were changed. The FastAPI/OpenAPI architecture, CP-SAT model, warehouse coordination, SimPy, and existing contracts were not changed.

## Regression
`pytest -q backend/tests` => 37 passed.
