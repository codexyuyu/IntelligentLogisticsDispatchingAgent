# B-02 Runtime Compatibility Fix — 2026-09-11

## Symptom
A real planning job reached the Routing stage and failed with:

`Protocol message RoutingSearchParameters has no "random_seed" field.`

## Cause
The B-02 OR-Tools adapter assigned `request.budget.random_seed` directly to `pywrapcp.DefaultRoutingSearchParameters()`.
The installed OR-Tools 9.15 Python `RoutingSearchParameters` contract does not expose that field.

## Fix
Removed only the unsupported assignment. The existing Routing search strategy and the request budget's `time_limit` remain unchanged.

## User action
Replace the backend code with this package, restart Uvicorn, re-import the scenario, and submit a fresh planning job with a new `Idempotency-Key`.
