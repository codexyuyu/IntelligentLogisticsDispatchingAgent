"""R17 equal-budget B-03 comparison. Execute from the backend directory.

python -m tools.r17_joint_ablation --scenario ../data/scenarios/two_warehouses_20_orders.json --budget-ms 90000 --output r17_joint_evidence.json

Neither solver results nor numerical improvements are hardcoded.  Each arm
solves the same immutable snapshot and independently verifies its plan.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from time import perf_counter
from datetime import datetime, timezone

from app.application.coordinator import coordinate
from app.contracts.entities import PlanningSnapshot


def load_snapshot(filename: Path) -> tuple[PlanningSnapshot, str]:
    raw_bytes = filename.read_bytes()
    content = json.loads(raw_bytes)
    if isinstance(content, dict) and isinstance(content.get("snapshot"), dict):
        content = content["snapshot"]
    elif isinstance(content, dict) and isinstance(content.get("plan"), dict) and isinstance(content.get("scenario"), dict):
        content = content["scenario"]
    return PlanningSnapshot.model_validate(content), hashlib.sha256(raw_bytes).hexdigest()


def run_comparison(*, snapshot: PlanningSnapshot, snapshot_sha256: str,
                   budget_ms: int, order_ids: tuple[str, ...]):
    results = []
    for mode in ("sequential", "deep"):
        started = perf_counter()
        try:
            plan = coordinate(
                snapshot=snapshot, order_ids=order_ids,
                budget_ms=budget_ms,
                max_coordination_rounds=3 if mode == "deep" else 1,
                coordination_mode=mode,
            )
            results.append({
                "mode": mode, "status": "succeeded", "wall_ms": int((perf_counter() - started) * 1000),
                "distance_m": sum(r.distance_m for r in plan.routing.routes),
                "unserved_orders": [u.order_id for u in plan.routing.unserved_orders],
                "validation": plan.validation.model_dump(mode="json"),
                "coordination": plan.coordination.model_dump(mode="json") if plan.coordination else None,
                "candidate_plan": plan.model_dump(mode="json"),
            })
        except Exception as exc:
            results.append({"mode": mode, "status": "failed",
                            "wall_ms": int((perf_counter() - started) * 1000),
                            "error_type": type(exc).__name__, "error": str(exc)})
    return {
        "benchmark_version": "r17-b03-equal-total-budget-1.0",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "scenario_sha256": snapshot_sha256,
        "snapshot_id": snapshot.snapshot_id,
        "snapshot_version": snapshot.version,
        "order_count": len(order_ids),
        "order_ids": list(order_ids),
        "per_mode_total_budget_ms": budget_ms,
        "warning": "Only equal-budget paired trials support claims about B-03 mode performance; a single snapshot is not statistical evidence. Warehouse holding time is an operational proxy, not proven cost savings.",
        "results": results,
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description="Compare sequential and deep B-03 coordination on the same snapshot and budget")
    parser.add_argument("--scenario", type=Path, default=Path("../data/scenarios/two_warehouses_20_orders.json"))
    parser.add_argument("--budget-ms", type=int, default=90000)
    parser.add_argument("--output", type=Path, default=Path("r17_joint_evidence.json"))
    args = parser.parse_args(argv)
    if args.budget_ms < 1000:
        parser.error("--budget-ms must be >= 1000")
    snapshot, fingerprint = load_snapshot(args.scenario)
    ids = tuple(o.order_id for o in snapshot.orders)
    report = run_comparison(snapshot=snapshot, snapshot_sha256=fingerprint,
                            budget_ms=args.budget_ms, order_ids=ids)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    # newline="\n" keeps the evidence byte-identical across platforms; Windows text
    # mode emitted CRLF, which broke published hashes (see R18 acceptance freeze note).
    args.output.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n",
                           encoding="utf8", newline="\n")
    print(f"Scenario SHA256: {fingerprint} / {len(ids)} orders / budget per arm {args.budget_ms}ms")
    for row in report["results"]:
        if row["status"] == "succeeded":
            print(f"  {row['mode']}: PASSED, {row['distance_m']}m, wall {row['wall_ms']}ms, "
                  f"selected round {row['coordination']['selected_round']}")
        else:
            print(f"  {row['mode']}: FAILED ({row['error_type']}): {row['error']}")
    print(f"Evidence JSON: {args.output.resolve()}")
    return 0 if all(row["status"] == "succeeded" for row in report["results"]) else 1


if __name__ == "__main__":
    sys.exit(main())
