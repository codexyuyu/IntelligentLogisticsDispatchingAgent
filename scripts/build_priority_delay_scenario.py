"""Generate a reproducible *integrated* synthetic scenario (not a claimed winning run).

The generated fixture has distinct drop-off locations and soft due dates,
so a genuine S1/S4 run can expose time-versus-distance decisions. Positive
savings must be calculated from the persisted candidate, never asserted here.
"""
from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path
from uuid import UUID, uuid5

ROOT = Path(__file__).resolve().parents[1]
NAMESPACE = UUID('e1516d0c-5a82-4d45-a914-d91e5fca003a')

def generate() -> dict:
    original = json.loads((ROOT / 'data/scenarios/coldchain_chain_10.json').read_text(encoding='utf-8'))
    doc = deepcopy(original)
    doc['name'] = '县域冷链多收货点时效约束联动场景（合成）'
    doc['source_ref'] = 'priority-delay-v1 derived from coldchain_chain_10; deterministic synthetic scenario'
    original_orders = original['snapshot']['orders']
    original_matrix = original['snapshot']['matrices'][0]['node_ids']
    # Keep existing geographical matrix identities; only regenerate business
    # records changed by the fixture so independent imports cannot overwrite
    # same-UUID orders, cargo or warehouse scheduling tasks.
    ids = {str(item['id']) for group in (original['snapshot']['orders'],
                                         original['snapshot']['cargo'], original['warehouse_tasks'])
           for item in group}
    for occ in original['coldchain_fields']['occupancies']:
        ids.add(str(occ['occupancy_id']))
    mapping = {key: str(uuid5(NAMESPACE, key)) for key in ids}
    id_snapshot = original['snapshot']['id']
    mapping[id_snapshot] = str(uuid5(NAMESPACE, id_snapshot))

    def replace(value):
        if isinstance(value, str):
            return mapping.get(value, value)
        if isinstance(value, list):
            return [replace(item) for item in value]
        if isinstance(value, dict):
            return {mapping.get(k, k): replace(v) for k, v in value.items()}
        return value

    doc = replace(doc)
    snapshot = doc['snapshot']
    # Three distinct destination locations (2, 3, 4 in the existing matrix),
    # with deliberately nonuniform soft due dates and more urgent orders at
    # the third location. Do not change hard feasibility windows.
    destinations = [2, 2, 2, 2, 3, 3, 3, 4, 4, 4]
    deadlines = [1950, 2030, 2110, 2190, 1550, 1660, 1770, 1200, 1300, 1400]
    for i, order in enumerate(snapshot['orders']):
        order['delivery_node_id'] = original_matrix[destinations[i]]
        order['soft_due_at_s'] = deadlines[i]
        order['external_ref'] = f'PRIO-O{i+1:02d}'
    # Rebuild the canonical domain digest from the authoritative DTOs rather
    # than hashing raw JSON (which is NOT the same canonical representation).
    from dataclasses import replace as dc_replace
    from logistics_contracts.integration import ScenarioImport
    from logistics_contracts.mapping import snapshot_dto
    from logistics_domain.planning import PlanningSnapshot
    prior = ScenarioImport.model_validate(original).snapshot.to_domain()
    order_ids = {UUID(key): UUID(value) for key, value in mapping.items() if key in {o['id'] for o in original_orders}}
    cargo_ids = {UUID(key): UUID(value) for key, value in mapping.items() if key in {c['id'] for c in original['snapshot']['cargo']}}
    changed_orders = []
    for i, order in enumerate(prior.orders):
        changed_orders.append(dc_replace(order, id=order_ids[order.id],
            delivery_node_id=UUID(original_matrix[destinations[i]]), soft_due_at_s=deadlines[i],
            external_ref=f'PRIO-O{i+1:02d}', cargo_ids=tuple(cargo_ids[c] for c in order.cargo_ids)))
    changed_cargo = tuple(dc_replace(cargo, id=cargo_ids[cargo.id],
        order_id=order_ids[cargo.order_id]) for cargo in prior.cargo)
    changed_inventory = tuple(dc_replace(item, cargo_id=cargo_ids[item.cargo_id]) for item in prior.inventory)
    changed_revisions = tuple(dc_replace(revision, entity_ref=dc_replace(revision.entity_ref,
        id=order_ids.get(revision.entity_ref.id, cargo_ids.get(revision.entity_ref.id, revision.entity_ref.id))))
        for revision in prior.revisions)
    new_snapshot = PlanningSnapshot.create(
        id=UUID(mapping[id_snapshot]), scope=dc_replace(prior.scope, order_ids=tuple(order_ids[x] for x in prior.scope.order_ids)),
        orders=tuple(changed_orders), cargo=changed_cargo, vehicles=prior.vehicles, drivers=prior.drivers,
        resources=prior.resources, inventory=changed_inventory, revisions=changed_revisions,
        matrices=prior.matrices, coldchain=None)
    doc['snapshot'] = snapshot_dto(new_snapshot).model_dump(mode='json')
    return doc

if __name__ == '__main__':
    path = ROOT / 'data/scenarios/coldchain_chain_10_priority_delay.json'
    path.write_text(json.dumps(generate(), ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(path)
