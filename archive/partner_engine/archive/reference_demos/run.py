"""Run independent probes and save measured results. No network or model calls."""
import argparse
import json
import platform
from datetime import datetime, timezone
from importlib.metadata import version
from pathlib import Path
from time import perf_counter
import warehouse
import transport
import exception_replan
from validation import warehouse_errors, transport_errors


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('module', nargs='?', choices=['all', 'warehouse', 'transport', 'exception'], default='all')
    args = parser.parse_args()
    results = dict(metadata=dict(recorded_at=datetime.now(timezone.utc).isoformat(), python=platform.python_version(),
                                platform=platform.platform(), ortools=version('ortools'), simpy=version('simpy'),
                                scope='tiny synthetic probes; not an end-to-end cold-chain system'))
    for name in ['warehouse', 'transport', 'exception']:
        if args.module not in ('all', name):
            continue
        start = perf_counter()
        if name == 'warehouse':
            data = warehouse.scenario()
            result = warehouse.solve(data)
            result['validation_errors'] = warehouse_errors(data, result)
        elif name == 'transport':
            data = transport.scenario()
            result = transport.solve(data)
            result['validation_errors'] = transport_errors(data, result)
        else:
            result = exception_replan.run()
        result['elapsed_seconds_single_run'] = round(perf_counter() - start, 6)
        if result['validation_errors']:
            raise RuntimeError(f'{name}: {result["validation_errors"]}')
        if name == 'exception' and not result['rejected_candidate_errors']:
            raise RuntimeError('Invalid candidate was not rejected')
        results[name] = result
        print(f'{name}: PASS, {result["elapsed_seconds_single_run"]:.4f}s')
    output = Path(__file__).parent / 'results' / f'{args.module}.json'
    output.parent.mkdir(exist_ok=True)
    output.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding='utf-8')
    print(f'Result: {output}')


if __name__ == '__main__':
    main()
