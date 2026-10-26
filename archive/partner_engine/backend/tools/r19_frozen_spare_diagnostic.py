"""R19 diagnostic (NOT part of the three-arm comparison): why B-04 failed on a delayed sole vehicle.

Found in the R19 v1 stress family: `b04_routing_failed:wh_1:ROUTING_NO_SOLUTION` in ~2-140 ms.
`app/application/handle_event.py` freezes every route whose vehicle is not the affected one, and
`OrToolsRoutingSolver._apply_frozen_routes` used to pin `NextVar(start) = end` for a frozen route
with no delivery, which forbade that vehicle from carrying anything. An idle spare vehicle was
therefore frozen out of exactly the recovery it exists for.

FIXED in `ortools_solver._apply_frozen_routes` (empty frozen routes are skipped). This script is
kept as the reproducer/verifier: after the fix the "includes idle spares" row must also solve.

Run from the backend directory (defaults to the newest R19 run):
    python -m tools.r19_frozen_spare_diagnostic
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from app.adapters.routing.ortools_solver import OrToolsRoutingSolver
from app.application.handle_event import _derive_snapshot_for_event
from app.contracts.events import DispatchEvent
from app.contracts.planning import CandidatePlan, RoutingRequest

from tools.r17_joint_ablation import load_snapshot

DELAY_S = 14400


def newest_run(root: Path) -> Path:
    runs = sorted(root.glob('run_*'))
    if not runs:
        raise SystemExit(f'no R19 run directory under {root}')
    return runs[-1]


def main(argv=None):
    parser = argparse.ArgumentParser(description='Diagnose B-04 frozen-route lockout (diagnostic only)')
    parser.add_argument('--run-dir', type=Path)
    parser.add_argument('--case', default='s12_seed17')
    parser.add_argument('--family', default='stress')
    parser.add_argument('--budget-ms', type=int, default=20000)
    args = parser.parse_args(argv)
    run_dir = args.run_dir or newest_run(Path('../benchmarks/b04/r19_runs'))
    raw = json.loads((run_dir / 'raw' / f'{args.case}__{args.family}_arms.json').read_text(encoding='utf8'))
    snapshot, _ = load_snapshot(run_dir / raw['scenario_file'])
    baseline = CandidatePlan.model_validate(raw['baseline']['candidate_plan'])
    rung = next(r for r in raw['rungs'] if r['delay_s'] == DELAY_S)
    event = DispatchEvent.model_validate(rung['event'])
    derived = _derive_snapshot_for_event(snapshot, event)
    handoffs = {h.order_id: h for h in baseline.warehouse.warehouse_handoffs}
    affected = {event.object_id}
    print(f'run={run_dir.name} case={args.case}@{args.family} delay={DELAY_S}s affected={event.object_id}')

    for warehouse_id in sorted({o.warehouse_id for o in derived.orders}):
        ids = tuple(sorted(o.order_id for o in derived.orders if o.warehouse_id == warehouse_id))
        routes = [r for r in baseline.routing.routes
                  if any(v.vehicle_id == r.vehicle_id and v.warehouse_id == warehouse_id
                         for v in derived.vehicles)]
        frozen_all = tuple(r for r in routes if r.vehicle_id not in affected)
        frozen_nonempty = tuple(r for r in frozen_all if any(s.stop_kind == 'delivery' for s in r.stops))
        print(f'--- {warehouse_id}: frozen_all={[r.vehicle_id for r in frozen_all]} '
              f'frozen_nonempty={[r.vehicle_id for r in frozen_nonempty]}')
        for label, frozen in (('freeze_includes_idle_spares', frozen_all),
                              ('freeze_excludes_idle_spares', frozen_nonempty)):
            request = RoutingRequest(
                snapshot=derived, order_ids=ids,
                warehouse_handoffs=tuple(handoffs[o] for o in ids), frozen_routes=frozen,
                budget={'remaining_ms': args.budget_ms, 'max_workers': 1, 'random_seed': 17},
            )
            result = OrToolsRoutingSolver().solve(request)
            served = sorted(oid for r in result.routes for s in r.stops
                            if s.stop_kind == 'delivery' for oid in s.order_ids)
            used = {r.vehicle_id: len([s for s in r.stops if s.stop_kind == 'delivery'])
                    for r in result.routes}
            print(f'    {label:32} has_solution={result.metadata.has_solution} '
                  f'raw={result.metadata.raw_status.split(":")[0]} served={len(served)} '
                  f'used={ {k: v for k, v in used.items() if v} }')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
