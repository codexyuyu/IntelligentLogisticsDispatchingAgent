"""Validate imported facts and explicitly supplied R05 backfill; never invent limits."""
from dataclasses import fields
from uuid import UUID, uuid5

from logistics_contracts.integration import ScenarioImport
from logistics_contracts.mapping import snapshot_dto
from logistics_domain.planning import PlanningSnapshot, content_hash

IMPORT_NAMESPACE = UUID('0a3f2eed-cb24-43c7-94f5-650b5af9311e')


def prepare_scenario(command: ScenarioImport):
    snapshot = command.snapshot.to_domain()
    cold = command.coldchain_fields.to_domain() if command.coldchain_fields else snapshot.coldchain
    errors = []
    tasks = tuple(t.to_domain() for t in command.warehouse_tasks)
    task_ids = {t.id for t in tasks}
    resources = {r.id for r in (*snapshot.resources.docks, *snapshot.resources.workers, *snapshot.resources.equipment)}
    if not tasks or len(task_ids) != len(tasks):
        errors.append('warehouse_tasks:empty_or_duplicate')
    if set(command.available_at_s) != {v.id for v in snapshot.vehicles} or any(v < 0 for v in command.available_at_s.values()):
        errors.append('available_at_s:exact_vehicle_coverage_required')
    for task in tasks:
        if any(p not in task_ids for p in task.predecessor_ids):
            errors.append(f'warehouse_tasks.{task.id}:unknown_predecessor')
        if any(not set(req.eligible_ids) <= resources for req in task.requirements):
            errors.append(f'warehouse_tasks.{task.id}:unknown_resource')
    if cold is None:
        errors.append('coldchain:required_fields_missing')
    else:
        if cold.horizon_s != snapshot.scope.horizon_s:
            errors.append('coldchain.horizon_s:scope_mismatch')
        if not cold.rule_version or not cold.zones or not cold.storage_locations or not cold.occupancies:
            errors.append('coldchain:zones_locations_occupancies_required')
        zone_ids = {z.id for z in snapshot.resources.zones}
        location_ids = {location.id for location in snapshot.resources.locations}
        batches = {c.batch_ref for c in snapshot.cargo}
        if not {z.zone_id for z in cold.zones} <= zone_ids:
            errors.append('coldchain.zones:unknown_master_id')
        if not {location.location_id for location in cold.storage_locations} <= location_ids:
            errors.append('coldchain.storage_locations:unknown_master_id')
        metadata = {b.batch_id for b in cold.batch_compatibility}
        limits = {b.batch_id for b in cold.exposure_limits}
        for occupancy in cold.occupancies:
            if occupancy.batch_id not in batches & metadata & limits:
                errors.append(f'coldchain.occupancies.{occupancy.occupancy_id}:batch_or_exposure_evidence_missing')
            if any(t is not None and t not in task_ids for t in (occupancy.inbound_operation_id, occupancy.outbound_operation_id)):
                errors.append(f'coldchain.occupancies.{occupancy.occupancy_id}:unknown_operation')
        for req in cold.precool_requirements:
            if not {req.precool_operation_id, *req.loading_operation_ids} <= task_ids or not set(req.eligible_resource_ids) <= resources:
                errors.append(f'coldchain.precool.{req.requirement_id}:unknown_operation_or_resource')
    if errors:
        return {'status': 'not_checked', 'issues': sorted(set(errors)), 'source_kind': command.source_kind}
    body = {f.name: getattr(snapshot, f.name) for f in fields(snapshot) if f.name not in ('hash', 'id')}
    body['coldchain'] = cold
    snapshot = PlanningSnapshot.create(id=uuid5(IMPORT_NAMESPACE, content_hash(body)), **body)
    normalized = command.model_copy(update={'snapshot': snapshot_dto(snapshot), 'coldchain_fields': None})
    return {'status': 'checked', 'issues': [], 'source_kind': command.source_kind,
            'source_verified': False, 'snapshot_hash': snapshot.hash,
            'backfilled_fields': ['snapshot.coldchain'] if command.coldchain_fields else [],
            'payload': normalized.model_dump(mode='json'), 'input_hash': content_hash(normalized.model_dump(mode='json'))}
