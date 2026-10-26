"""R05 -> R08 -> R09 minimal business loop for the 2026-10-26 demo.

Owner: PARTNER (乙方). Reproducible by design: one scenario, one seed, one
budget, and the same JSON evidence every run.

What it does, in order:

1. loads a scenario and attaches a deterministic, clearly-labelled synthetic R05
   cold-chain layer (storage locations, occupancies, exposure limits, setup
   policy, per-op resource requirement) so the CP-SAT model has cold-chain work;
2. solves it for real through ``coordinate`` (CP-SAT warehouse + OR-Tools
   routing, both independently validated);
3. runs the R08 four-role negotiation over the *solved* plan (tasks and roles
   bound to the operations, resources and vehicles the solver produced);
4. observes the result for R09 (coverage, waits, capacity peaks, exposure
   unions, negotiation digest) and prints/writes the evidence.

Run it from the repository root:

    python backend/tools/r09_demo_loop.py --max-orders 6 --budget-ms 8000

The R05 layer is synthetic demo enrichment, not enterprise data: every occupancy
and limit is derived from the scenario's own orders and marked ``simulation``.
"""
from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'backend'))

from app.application.coordinator import coordinate  # noqa: E402
from app.application.negotiation_link import negotiate_plan  # noqa: E402
from app.application.plan_observations import observe_plan  # noqa: E402
from app.contracts.entities import PlanningSnapshot  # noqa: E402

SOURCE = {
    'source_kind': 'simulation',
    'source_ref': 'backend/tools/r09_demo_loop.py',
    'observed_at': '2026-10-24T00:00:00Z',
    'rule_version': 'r05-demo-1.0',
}
CLASS = 'demo_class'


def enrich_coldchain(raw: dict) -> dict:
    """Attach a deterministic synthetic R05 layer derived from the orders."""
    scenario = json.loads(json.dumps(raw))
    orders = scenario['orders']
    resources = scenario['resources']
    horizon = max(int(order['service_window']['end_s']) for order in orders)
    warehouses = {warehouse['warehouse_id'] for warehouse in scenario['warehouses']}
    total_weight_g = sum(int(order['weight_kg']) * 1000 for order in orders)

    zones = []
    locations = []
    for warehouse_id in sorted(warehouses):
        zones.append({
            'zone_id': f'zone_{warehouse_id}', 'warehouse_id': warehouse_id, 'version': 1,
            'temperature_zone': 'chilled', 'setpoint_decic': 40,
            'capacities': [{'unit': 'weight_g', 'amount': max(total_weight_g, 1)}],
        })
        locations.append({
            'location_id': f'loc_{warehouse_id}', 'warehouse_id': warehouse_id,
            'zone_id': f'zone_{warehouse_id}', 'version': 1,
            'capacities': [{'unit': 'weight_g', 'amount': max(total_weight_g, 1)}],
            'available_windows': [{'start_s': 0, 'end_s': horizon}],
        })

    loading_by_order = {}
    for operation in scenario['operations']:
        if 'load' in operation['operation_kind']:
            for order_id in operation['order_ids']:
                loading_by_order.setdefault(order_id, operation)

    occupancies = []
    batch_profiles = []
    exposure_limits = []
    for index, order in enumerate(sorted(orders, key=lambda item: item['order_id']), start=1):
        operation = loading_by_order.get(order['order_id'])
        occupancies.append({
            'occupancy_id': f'occ_{index:03d}', 'batch_id': order['batch_id'],
            'location_id': f'loc_{order["warehouse_id"]}',
            'capacity_use': [{'unit': 'weight_g', 'amount': int(order['weight_kg']) * 1000}],
            'origin': 'initial_stock',
            'outbound_operation_id': operation['operation_id'] if operation else None,
        })
        batch_profiles.append({
            'batch_id': order['batch_id'], 'warehouse_id': order['warehouse_id'],
            'temperature_zone': order['temperature_zone'],
            'min_temperature_decic': 0, 'max_temperature_decic': 80,
            'compatibility_class': CLASS,
        })
        exposure_limits.append({
            'limit_id': f'exp_{index:03d}', 'batch_id': order['batch_id'],
            'max_exposure_s': horizon, 'scopes': ['in_warehouse', 'loading'],
            'rule_version': SOURCE['rule_version'], 'source': SOURCE,
        })

    for resource in resources:
        resource['setup_policy_id'] = 'pol_demo'
        resource['initial_setup_class'] = CLASS

    docks_by_warehouse: dict[str, list[str]] = {}
    for resource in resources:
        docks_by_warehouse.setdefault(resource['warehouse_id'], []).append(resource['resource_id'])

    precool_requirements = []
    precool_operations = []
    for operation in sorted(scenario['operations'], key=lambda item: item['operation_id']):
        if 'load' not in operation['operation_kind']:
            continue
        docks = sorted(docks_by_warehouse.get(operation['warehouse_id'], []))
        if not docks:
            continue
        precool_id = f'pre_{operation["operation_id"]}'
        precool_operations.append({
            'operation_id': precool_id,
            'order_ids': operation['order_ids'],
            'warehouse_id': operation['warehouse_id'],
            'resource_id': docks[0],
            'operation_kind': 'precool',
            'duration_s': 60,
            'release_at_s': operation['release_at_s'],
            'deadline_at_s': operation['deadline_at_s'],
        })
        operation['predecessor_ids'] = sorted(set(operation.get('predecessor_ids', ())) | {precool_id})
        precool_requirements.append({
            'requirement_id': f'preq_{operation["operation_id"]}',
            'batch_id': next(order['batch_id'] for order in orders
                             if order['order_id'] == operation['order_ids'][0]),
            'warehouse_id': operation['warehouse_id'],
            'precool_operation_id': precool_id,
            'loading_operation_ids': [operation['operation_id']],
            'min_duration_s': 60,
            'target_temperature_zone': 'chilled',
            'eligible_resource_ids': docks,
        })

    scenario['coldchain'] = {
        'rule_version': SOURCE['rule_version'],
        'horizon_s': horizon,
        'zones': zones,
        'storage_locations': locations,
        'occupancies': occupancies,
        'setup_policies': [{
            'policy_id': 'pol_demo', 'version': '1', 'rule_version': SOURCE['rule_version'],
            'rendering': 'gap', 'rules': [], 'default_duration_s': None,
        }],
        'precool_requirements': precool_requirements,
        'exposure_limits': exposure_limits,
        'batch_compatibility': batch_profiles,
        'compatibility_policy': {
            'policy_id': 'pol_mix', 'version': '1', 'rule_version': SOURCE['rule_version'],
            'incompatible_class_pairs': [],
        },
    }
    scenario['operations'].extend(precool_operations)

    # Every loading operation declares its dock requirement so R05 multi-resource
    # checking is exercised; the eligible set is the docks of that warehouse.
    docks = {}
    for resource in resources:
        docks.setdefault(resource['warehouse_id'], []).append(resource['resource_id'])
    for operation in scenario['operations']:
        if 'load' not in operation['operation_kind']:
            continue
        eligible = sorted(docks.get(operation['warehouse_id'], []))
        if not eligible:
            continue
        operation['requirements'] = [{
            'requirement_id': f'req_{operation["operation_id"]}',
            'requirement_kind': 'dock',
            'eligible_resource_ids': eligible,
            'quantity_units': 1,
            'selection': 'choose_one',
        }]
        operation['primary_requirement_id'] = operation['requirements'][0]['requirement_id']
    return scenario


def run(scenario_path: Path, budget_ms: int, max_orders: int | None) -> dict:
    raw = json.loads(scenario_path.read_text(encoding='utf-8'))
    enriched = enrich_coldchain(raw)
    snapshot = PlanningSnapshot.model_validate(enriched)
    order_ids = tuple(order['order_id'] for order in enriched['orders'])
    if max_orders is not None:
        order_ids = order_ids[:max_orders]

    plan = coordinate(snapshot=snapshot, order_ids=order_ids, budget_ms=budget_ms,
                      max_coordination_rounds=1, coordination_mode='sequential')
    observations = observe_plan(plan, order_ids)
    negotiations = negotiate_plan(plan, snapshot, now_s=0)

    transcript: list[str] = []
    for outcome in negotiations:
        transcript.append(f'--- {outcome.order_id} / {outcome.operation_id} / {outcome.vehicle_id}')
        transcript.extend(outcome.transcript_lines())

    return {
        'scenario': scenario_path.name,
        'rule_version': SOURCE['rule_version'],
        'order_ids': list(order_ids),
        'plan_id': plan.plan_id,
        'plan_hash': plan.plan_hash,
        'validation_status': plan.validation.status,
        'observations': asdict(observations),
        'negotiations': [
            {
                'order_id': item.order_id,
                'operation_id': item.operation_id,
                'vehicle_id': item.vehicle_id,
                'resource_id': item.resource_id,
                'status': item.result.status,
                'awarded_role': item.awarded_role,
                'digest': item.result.digest,
            }
            for item in negotiations
        ],
        'negotiation_transcript': transcript,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description='R05 -> R08 -> R09 demo loop')
    parser.add_argument('--scenario', default=str(ROOT / 'data/scenarios/single_warehouse_20_orders.json'))
    parser.add_argument('--budget-ms', type=int, default=8000)
    parser.add_argument('--max-orders', type=int, default=None)
    parser.add_argument('--out-dir', default=None)
    args = parser.parse_args(argv)

    evidence = run(Path(args.scenario), args.budget_ms, args.max_orders)
    observations = evidence['observations']
    print(f"scenario      {evidence['scenario']}")
    print(f"plan          {evidence['plan_id']}  validation={evidence['validation_status']}")
    requested = len(observations['requested_order_ids'])
    print(f"coverage      {len(observations['served_order_ids'])}/{requested} served")
    print(f"cold-chain    evidence={observations['coldchain_evidence']} "
          f"peaks={len(observations['capacity_peaks'])} exposures={len(observations['exposure_totals'])} "
          f"changeovers={observations['changeover_count']}")
    print(f"handoff waits measured={len(observations['handoff_wait_s']) - len([w for w in observations['handoff_wait_s'] if w[1] is None])}"
          f" unmeasured={len([w for w in observations['handoff_wait_s'] if w[1] is None])}")
    print(f"negotiation   {len(evidence['negotiations'])} orders, "
          + ', '.join(f"{item['status']}/{item['awarded_role']}" for item in evidence['negotiations'][:4]))
    print('')
    print('\n'.join(evidence['negotiation_transcript'][:40]))

    if args.out_dir:
        out = Path(args.out_dir)
        out.mkdir(parents=True, exist_ok=True)
        target = out / 'r09_demo_loop.json'
        target.write_text(json.dumps(evidence, ensure_ascii=False, indent=2, sort_keys=True) + '\n',
                          encoding='utf-8')
        print(f'\nwrote {target}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())


