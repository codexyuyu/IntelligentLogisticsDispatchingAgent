"""Synthetic import -> real solvers -> independent joint validation -> R08 -> R09."""
from dataclasses import replace
from uuid import UUID

from tests.integration.test_partner_coldchain import cold_problem, rebuild

from logistics_backend.application.integration import solve_imported
from logistics_backend.application.scenario_import import prepare_scenario
from logistics_contracts.integration import IntegrationRun, ScenarioImport
from logistics_contracts.mapping import snapshot_dto, warehouse_task_dto
from logistics_domain.coldchain import ReuseRule


def synthetic_import():
    problem = cold_problem()
    snapshot = problem.snapshot
    location = snapshot.resources.locations[0]
    zone = next(z for z in snapshot.resources.zones if z.id == location.zone_id)
    cold = snapshot.coldchain
    cold = replace(cold,
        zones=(replace(cold.zones[0], zone_id=zone.id, warehouse_id=zone.warehouse_id),),
        storage_locations=(replace(cold.storage_locations[0], location_id=location.id,
                                    zone_id=zone.id, warehouse_id=zone.warehouse_id),),
        occupancies=tuple(replace(o, location_id=location.id) for o in cold.occupancies))
    cargo = tuple(replace(c, batch_ref='initial' if c.order_id == snapshot.orders[0].id else 'incoming')
                  for c in snapshot.cargo)
    full = rebuild(snapshot, cargo=cargo, coldchain=cold)
    plain = rebuild(full, coldchain=None)
    return ScenarioImport(name='合成冷链双订单验收样本', source_kind='synthetic',
        source_ref='tiny_master.json + explicit synthetic capacity/stock/limit fixtures',
        snapshot=snapshot_dto(plain), coldchain_fields=snapshot_dto(full).coldchain,
        warehouse_tasks=tuple(warehouse_task_dto(t) for t in problem.tasks),
        available_at_s={v.id: 0 for v in snapshot.vehicles})


def test_import_backfills_only_declared_fields_and_preserves_provenance():
    command = synthetic_import()
    result = prepare_scenario(command)
    assert result['status'] == 'checked', result
    assert result['source_kind'] == 'synthetic' and result['source_verified'] is False
    assert result['backfilled_fields'] == ['snapshot.coldchain']
    snapshot = ScenarioImport.model_validate(result['payload']).snapshot.to_domain()
    assert snapshot.coldchain == command.coldchain_fields.to_domain()
    assert snapshot.hash != command.snapshot.hash
    assert prepare_scenario(command) == result


def test_missing_policy_or_vehicle_release_is_not_checked():
    command = synthetic_import()
    for invalid in (command.model_copy(update={'coldchain_fields': None}),
                    command.model_copy(update={'available_at_s': {}}),
                    command.model_copy(update={'coldchain_fields': command.coldchain_fields.model_copy(update={'exposure_limits': ()})})):
        result = prepare_scenario(invalid)
        assert result['status'] == 'not_checked' and result['issues']
        assert 'payload' not in result


def test_imported_pipeline_has_real_evidence_handoffs_negotiation_and_fourteen_metrics():
    result = solve_imported(synthetic_import(), IntegrationRun(scenario_id=UUID(int=1), budget_ms=4000), UUID(int=2))
    assert result['status'] == 'checked', result.get('reason')
    assert result['joint_validation']['valid']
    assert result['warehouse_solution']['solver_evidence']
    assert result['transport_solution']['solver_evidence']
    assert result['negotiation']['result']['status'] == 'confirmed'
    assert len(result['negotiation']['result']['awards']) == 2
    assert len(result['observations']['metrics']['values']) == 14
    assert result['observations']['coldchain']['occupancies']
    assert all(h['pickup_start_s'] >= h['warehouse_ready_s'] for h in result['observations']['handoffs'])
    missing = {m['code']: m for m in result['observations']['metrics']['values'] if m['value'] is None}
    assert missing['exception_detection_ms']['reason'] == 'missing_data'
    assert result['source_kind'] == 'synthetic'


def test_coldchain_observations_use_real_r05_capped_storage_intervals():
    command = synthetic_import()
    cold = command.coldchain_fields.to_domain()
    location = cold.storage_locations[0]
    cold = replace(cold, reuse_rules=(ReuseRule(location.location_id, 3600, 0),))
    snapshot = rebuild(command.snapshot.to_domain(), coldchain=cold)
    command = command.model_copy(update={'coldchain_fields': snapshot_dto(snapshot).coldchain})

    result = solve_imported(command, IntegrationRun(scenario_id=UUID(int=3), budget_ms=4000), UUID(int=2))
    assert result['status'] == 'checked', result.get('reason')
    solved = {entry['cargo_id']: entry for entry in result['warehouse_solution']['storage_allocations']}
    displayed = {entry['occupancy_id']: entry for entry in result['observations']['coldchain']['occupancies']}
    assert solved.keys() == displayed.keys()
    assert any(entry['end_s'] < cold.horizon_s for entry in solved.values())
    for occupancy_id, allocation in solved.items():
        observed = displayed[occupancy_id]
        assert (observed['start_s'], observed['end_s'], observed['location_id']) == (
            allocation['start_s'], allocation['end_s'], allocation['location_id'])
