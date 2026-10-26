# 910 merged baseline

This package intentionally preserves two layers:

1. `algorithm-service/` — legacy B-01 CP-SAT V1.2 service from `910_CP_SAT_V1.2_completed.zip`.
   It remains intact and runnable as the current historical B-01 implementation.
2. `backend/` — the team's current shared architecture baseline, where B-02 Routing is implemented
   under `backend/app/adapters/routing/`, with matrix adapters and transport rules under B ownership.

Do not delete or overwrite `algorithm-service/` until AC integrates an equivalent B-01 scheduler into
its shared `WarehouseScheduler` port. The shared architecture currently reserves `adapters/warehouse`
for AC, so this merge does not silently move B-01 into that ownership boundary.

Current B work status:
- B-01 CP-SAT V1.2: preserved in `algorithm-service/`.
- B-02 Routing: implemented in `backend/app/adapters/routing/ortools_solver.py`.
- B matrix adapter: `backend/app/adapters/matrix/`.
- B simulation scaffolding: `backend/app/adapters/simulation/`.

The shared contracts/ports remain the team's source of truth. No public DTO aliases are introduced by
this merge.
