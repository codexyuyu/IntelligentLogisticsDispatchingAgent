# Current Baseline

Current formal development baseline for B:

- B-01 CP-SAT migrated into `backend/app/adapters/warehouse/` while legacy `algorithm-service/` remains as regression reference.
- B-02 Routing V1.1 implemented in `backend/app/adapters/routing/ortools_solver.py`.
- Matrix adapter: `backend/app/adapters/matrix/fixed.py`.
- Independent transport validation: `backend/app/domain/transport_rules.py`.
- Explicit transport cost sidecar: `backend/app/adapters/routing/metrics.py`.
- Shared contracts/ports were not changed in B02 V1.1.
- Database was not changed.


## R15 experiment evidence refresh
See `../R15_EXPERIMENT_EVIDENCE_GUIDE.md`. Original R14 outcomes are historical only and not revalidated under the new scenario generation and fairness checks.


## R17: real B-03 transport-feedback warehouse coordination
- Explicit `coordination_mode="deep"` (default is `"sequential"`, preserving B-06/R16).
- OR-Tools route departure -> CP-SAT JIT operation scheduling -> Routing re-solve -> independent three-layer validation -> lexicographic safe selection / fallback.
- `CandidatePlan.coordination` carries deterministic per-round audit and metrics; OpenAPI/schema regenerated.
- Competition UI has dual-mode selector and evidence JSON export; equal-total-budget comparison tool provided.
- Reference `../R17_B03_DEEP_JOINT_OPTIMIZATION_GUIDE.md` for limitations and Windows tests.
