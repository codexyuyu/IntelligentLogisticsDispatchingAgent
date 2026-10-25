"""Isolated paired runs. Callbacks must not publish plans or write business data."""
import hashlib
import json
import platform
import random
from pathlib import Path
from time import perf_counter_ns
from app.contracts.planning import CandidatePlan
from app.evaluation.metrics import planned_metrics


def run_paired(snapshot, strategies, seeds, budget_ms, out_dir):
    """callback(snapshot, seed, budget_ms) -> CandidatePlan.

    Budget is passed equally, not a process hard timeout. Overrun is recorded,
    never silently dropped. Strategy order rotates to reduce fixed order effects.
    """
    seeds = list(seeds)
    if len(seeds) < 10 or len(set(seeds)) != len(seeds) or any(type(s) is not int or s < 0 for s in seeds):
        raise ValueError("at_least_10_unique_nonnegative_seeds_required")
    if type(budget_ms) is not int or budget_ms <= 0 or len(strategies) < 2:
        raise ValueError("invalid_experiment_configuration")
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=False)
    horizon = max([snapshot.simulation_time_s+1] + [v.shift_window.end_s for v in snapshot.vehicles] + [o.service_window.end_s+o.service_duration_s for o in snapshot.orders])
    payload = snapshot.model_dump(mode="json")
    serialized = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    (out/"snapshot.json").write_text(serialized, encoding="utf-8")
    from importlib.metadata import version
    backend = Path(__file__).resolve().parents[2]
    sources = {str(p.relative_to(backend)): hashlib.sha256(p.read_bytes()).hexdigest()
               for p in sorted((backend/'app').rglob('*.py'))}
    manifest = {"source_hashes": sources,
                "dependencies": {name: version(name) for name in ('ortools','pydantic','simpy')},"snapshot_sha256": hashlib.sha256(serialized.encode()).hexdigest(), "seeds": seeds,
                "strategies": list(strategies), "budget_ms": budget_ms,
                "python": platform.python_version(), "platform": platform.platform(),
                "budget_scope": "callback receives budget; end_to_end_ms includes callback validation; no hard kill"}
    (out/"manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    rows = []
    names = list(strategies)
    for index, seed in enumerate(seeds):
        order = names[index % len(names):] + names[:index % len(names)]
        for name in order:
            started = perf_counter_ns()
            row = {"strategy": name, "seed": seed, "status": "failed"}
            try:
                plan = strategies[name](snapshot.model_copy(deep=True), seed, budget_ms)
                if not isinstance(plan, CandidatePlan):
                    raise TypeError("strategy_must_return_CandidatePlan")
                row["plan"] = plan.model_dump(mode="json")
                row["metrics"] = {k:v.to_dict() for k,v in planned_metrics(snapshot, plan, window_start=0,window_end=horizon,scope_id=snapshot.snapshot_id).items()}
                row["status"] = "succeeded" if row["metrics"]["demand_satisfaction"]["value"] is not None else "invalid"
            except Exception as error:
                # Experiment failure is an output, not a fabricated successful plan.
                row["error_type"] = type(error).__name__
                row["error"] = str(error)
            row["end_to_end_ms"] = (perf_counter_ns()-started)/1_000_000
            row["budget_exceeded"] = row["end_to_end_ms"] > budget_ms
            rows.append(row)
            with (out/"runs.jsonl").open("a", encoding="utf-8") as stream:
                stream.write(json.dumps(row, ensure_ascii=False)+"\n")
    import math
    import statistics
    performance = {}
    for name in names:
        selected = [r for r in rows if r["strategy"] == name]
        times = sorted(r["end_to_end_ms"] for r in selected)
        performance[name] = {"runs": len(selected),
                             "succeeded": sum(r["status"] == "succeeded" for r in selected),
                             "failed_or_invalid": sum(r["status"] != "succeeded" for r in selected),
                             "budget_exceeded": sum(r["budget_exceeded"] for r in selected),
                             "median_end_to_end_ms": statistics.median(times),
                             "p95_end_to_end_ms": times[math.ceil(.95*len(times))-1],
                             "percentile_method": "nearest-rank", "population": "all attempts including failures"}
    (out/"performance.json").write_text(json.dumps(performance,indent=2),encoding="utf-8")
    return rows


def paired_summary(rows, left, right, metric, bootstrap_seed=17, samples=2000):
    if left == right or samples < 1:
        raise ValueError("invalid_comparison")
    indexed = {}
    for row in rows:
        key = (row["strategy"],row["seed"])
        if key in indexed:
            raise ValueError("duplicate_strategy_seed")
        indexed[key] = row
    seeds = sorted({r["seed"] for r in rows if r["strategy"] in (left,right)})
    differences = []
    for seed in seeds:
        pair = [indexed.get((name,seed)) for name in (left,right)]
        if any(r is None or r["status"] != "succeeded" or r.get("budget_exceeded") for r in pair):
            continue
        a,b = (r["metrics"][metric] for r in pair)
        fields = ("source","scope_id","window_start","window_end","definition_version","unit")
        if any(a[k] != b[k] for k in fields):
            raise ValueError("INCOMPARABLE_METRICS")
        if a["value"] is not None and b["value"] is not None:
            differences.append(b["value"]-a["value"])
    result = {"total_seeds": len(seeds), "complete_pairs": len(differences),
              "excluded_pairs": len(seeds)-len(differences), "difference": "right-minus-left",
              "mean_paired_difference": None, "bootstrap_ci95": None,
              "bootstrap_seed": bootstrap_seed, "samples": samples, "percentile_method": "nearest-rank"}
    if len(differences) >= 10:
        rng = random.Random(bootstrap_seed)
        means = sorted(sum(rng.choices(differences,k=len(differences)))/len(differences) for _ in range(samples))
        import math
        result.update(mean_paired_difference=sum(differences)/len(differences),
                      bootstrap_ci95=[means[max(0,math.ceil(samples*.025)-1)],means[math.ceil(samples*.975)-1]])
    return result
