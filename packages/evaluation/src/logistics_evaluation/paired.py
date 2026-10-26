"""Paired-seed experiments with retained failures and deterministic bootstrap."""
from copy import deepcopy
from dataclasses import asdict, dataclass
from random import Random
from statistics import mean
from time import monotonic_ns

from logistics_domain.planning import content_hash
from logistics_evaluation.complete import MetricReport


@dataclass(frozen=True)
class TrialResult:
    status: str
    metrics: MetricReport | None
    evidence_refs: tuple[str, ...]
    reason: str = ''


def quantile(values, probability):
    if not values:
        return None
    values = sorted(values)
    position = (len(values)-1)*probability
    lo = int(position)
    hi = min(lo+1, len(values)-1)
    return values[lo] + (values[hi]-values[lo])*(position-lo)


def compare_reports(left: MetricReport, right: MetricReport):
    def identity(r):
        return (r.scope_id, r.source, r.window_start_s, r.window_end_s, r.definition_version)
    if identity(left) != identity(right):
        raise ValueError('INCOMPARABLE_METRICS')
    a, b = ({m.code: m for m in report.values} for report in (left, right))
    if set(a) != set(b) or any((a[k].unit, a[k].definition_version, a[k].source) !=
                             (b[k].unit, b[k].definition_version, b[k].source) for k in a):
        raise ValueError('INCOMPARABLE_METRICS')
    return {k: b[k].value-a[k].value if a[k].value is not None and b[k].value is not None else None for k in a}


def run_paired(case, strategies, *, seeds=tuple(range(10)), budget_ms=2000, bootstrap_seed=0,
               bootstrap_samples=1000, hardware_id='local', rule_version='1.0.0'):
    """A strategy runs the same immutable case, seed and budget, including validation.

    Missing models/inputs must return not_checked. No strategy outcome is inferred from
    another strategy, and no failure is removed from the success-rate denominator.
    """
    if len(seeds) < 10 or len(set(seeds)) != len(seeds) or len(strategies) < 2:
        raise ValueError('at least 10 distinct paired seeds and 2 strategies required')
    if budget_ms <= 0 or bootstrap_samples < 100 or not hardware_id or not rule_version:
        raise ValueError('invalid experiment controls')
    case_hash = content_hash(case)
    trials = []
    results = {}
    for seed in seeds:
        for label, strategy in strategies.items():
            start = monotonic_ns()
            try:
                isolated_case = deepcopy(case)
                result = strategy(isolated_case, seed, budget_ms)
                if not isinstance(result, TrialResult):
                    raise ValueError('strategy must return TrialResult')
                if result.status == 'passed' and (result.metrics is None or not result.evidence_refs):
                    raise ValueError('passed trial requires metrics and validated solver evidence')
                if content_hash(isolated_case) != case_hash:
                    raise ValueError('strategy mutated shared input')
            except Exception as error:
                result = TrialResult('failed', None, (), f'{type(error).__name__}: {error}')
            elapsed = (monotonic_ns()-start)/1_000_000
            results[(label, seed)] = result
            trials.append({'strategy': label, 'seed': seed, 'budget_ms': budget_ms,
                           'elapsed_including_validation_ms': elapsed, **asdict(result)})
    labels = list(strategies)
    summary = {}
    for label in labels:
        rows = [r for r in trials if r['strategy'] == label]
        times = [r['elapsed_including_validation_ms'] for r in rows]
        summary[label] = {'success_rate': sum(r['status'] == 'passed' for r in rows)/len(seeds),
                          'median_elapsed_ms': quantile(times, .5), 'p95_elapsed_ms': quantile(times, .95)}
    comparisons = []
    for label in labels[1:]:
        deltas = {}
        incomparable = []
        for seed in seeds:
            left, right = results[(labels[0], seed)], results[(label, seed)]
            if left.status != 'passed' or right.status != 'passed':
                continue
            try:
                pair = compare_reports(left.metrics, right.metrics)
            except ValueError:
                incomparable.append(seed)
                continue
            for code, value in pair.items():
                if value is not None:
                    deltas.setdefault(code, []).append((seed, value))
        estimates = {}
        for code, pairs in sorted(deltas.items()):
            rng = Random(bootstrap_seed)
            values = [v for _, v in pairs]
            sampled = [mean(rng.choices(values, k=len(values))) for _ in range(bootstrap_samples)]
            estimates[code] = {'paired_count': len(values), 'paired_seeds': [s for s, _ in pairs],
                              'mean_difference': mean(values), 'median_difference': quantile(values, .5),
                              'bootstrap_95_ci': [quantile(sampled, .025), quantile(sampled, .975)]}
        comparisons.append({'base': labels[0], 'candidate': label, 'metrics': estimates,
                            'incomparable_seeds': incomparable})
    return {'case_hash': case_hash, 'seeds': list(seeds), 'budget_ms': budget_ms,
            'rule_version': rule_version, 'hardware_id': hardware_id,
            'quantile_method': 'linear (n-1)*p', 'bootstrap_seed': bootstrap_seed,
            'bootstrap_samples': bootstrap_samples, 'trials': trials,
            'summary': summary, 'comparisons': comparisons}
