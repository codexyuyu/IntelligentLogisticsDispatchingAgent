# Batch benchmark added

- Frontend-only addition; backend architecture/contracts are unchanged.
- Supports S20 / S50 / S100 and up to 8 deterministic scenario seeds.
- Each run imports a synthetic stress scenario derived from the existing S20 template, runs the existing Planning Job (CP-SAT + Routing), computes the deterministic rule baseline, and keeps per-seed results.
- Summary averages exclude failed runs and retain failure reasons.
- Seed controls scenario generation (time-window and quantity perturbations). The existing backend solver contract is unchanged; its internal planner seed remains controlled by the current backend.
