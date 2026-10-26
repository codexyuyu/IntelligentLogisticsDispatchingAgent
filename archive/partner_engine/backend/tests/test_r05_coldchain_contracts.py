"""R05 cold-chain contract freeze (contract 0.2.0) — shape and semantic guards.

These tests pin the *contract* boundary only.  They do not run CP-SAT, do not
build an occupancy timeline and do not claim any business rule was validated;
the independent R05 rules belong to domain/joint_validation.py (DSH) and their
positive/negative cases are a separate, later deliverable.
"""
from pathlib import Path

import pytest
from pydantic import ValidationError

from app.contracts.coldchain import (
    BatchCompatibility,
    CapacityAmount,
    ChangeoverRule,
    ColdChainPlan,
    ColdChainSnapshot,
    CompatibilityPolicy,
    ExposureLimit,
    ExposureSegment,
    PrecoolRequirement,
    ResourceAssignment,
    ResourceRequirement,
    ScheduledChangeover,
    ScheduledOccupancy,
    SetupPolicy,
    StorageLocation,
    StorageOccupancy,
    WarehouseZone,
)
from app.contracts.common import RuleEvidence, ValidationReport, Violation
from app.contracts.entities import Operation, ScheduledOperation, WarehouseResource

ROOT = Path(__file__).resolve().parents[2]
EXAMPLES = ROOT / 'contracts' / 'examples'

WEIGHT = {'unit': 'weight_g', 'amount': 10}


def _occupancy(**overrides):
    payload = {
        'occupancy_id': 'occ_1',
        'batch_id': 'bat_1',
        'location_id': 'loc_1',
        'capacity_use': [WEIGHT],
        'origin': 'initial_stock',
    }
    payload.update(overrides)
    return StorageOccupancy.model_validate(payload)


# --------------------------------------------------------------------------- #
# Published examples must stay valid — they are the shared reading material.
# --------------------------------------------------------------------------- #

def test_r05_example_snapshot_validates():
    snapshot = ColdChainSnapshot.model_validate_json(
        (EXAMPLES / 'r05_coldchain_snapshot.json').read_text(encoding='utf-8')
    )
    assert snapshot.horizon_s == 7200
    assert len(snapshot.occupancies) == 2
    initial = next(item for item in snapshot.occupancies if item.origin == 'initial_stock')
    assert initial.declared_start_s is None
    assert initial.outbound_operation_id == 'op_1-load'


def test_r05_example_plan_validates():
    plan = ColdChainPlan.model_validate_json(
        (EXAMPLES / 'r05_coldchain_plan.json').read_text(encoding='utf-8')
    )
    assert plan.occupancies[0].end_s == 1200
    assert plan.occupancies[1].start_s == 1200  # half-open: release then occupy
    assert plan.exposure_segments[1].scope == 'loading'


# --------------------------------------------------------------------------- #
# Capacity dimensions never mix.
# --------------------------------------------------------------------------- #

def test_capacity_units_must_be_unique_per_location():
    with pytest.raises(ValidationError, match='unique units'):
        StorageLocation(
            location_id='loc_1', warehouse_id='wh_1', zone_id='zone_1', version=1,
            capacities=(CapacityAmount(unit='weight_g', amount=10),
                        CapacityAmount(unit='weight_g', amount=20)),
        )


def test_capacity_units_cannot_be_empty():
    with pytest.raises(ValidationError, match='non-empty'):
        WarehouseZone(zone_id='zone_1', warehouse_id='wh_1', version=1,
                      temperature_zone='chilled', setpoint_decic=40, capacities=())


def test_unknown_capacity_unit_rejected():
    with pytest.raises(ValidationError):
        CapacityAmount(unit='pallets', amount=3)


def test_occupancy_rejects_mixed_duplicate_units():
    with pytest.raises(ValidationError, match='unique units'):
        _occupancy(capacity_use=[WEIGHT, {'unit': 'weight_g', 'amount': 5}])


# --------------------------------------------------------------------------- #
# Occupancy provenance: initial stock is not an inbound move.
# --------------------------------------------------------------------------- #

def test_initial_stock_cannot_have_inbound_operation():
    with pytest.raises(ValidationError, match='inbound operation'):
        _occupancy(inbound_operation_id='op_1-unload')


def test_initial_stock_starts_at_horizon_start():
    with pytest.raises(ValidationError, match='starts at 0'):
        _occupancy(declared_start_s=60)


def test_planned_inbound_requires_provenance():
    with pytest.raises(ValidationError, match='inbound_operation_id or declared_start_s'):
        _occupancy(origin='planned_inbound')


def test_planned_inbound_accepts_operation_reference():
    occupancy = _occupancy(origin='planned_inbound', inbound_operation_id='op_1-unload')
    assert occupancy.origin == 'planned_inbound'


def test_scheduled_occupancy_requires_positive_interval():
    with pytest.raises(ValidationError, match='end_s must be after start_s'):
        ScheduledOccupancy(occupancy_id='occ_1', batch_id='bat_1', location_id='loc_1',
                           capacity_use=(CapacityAmount(**WEIGHT),), start_s=10, end_s=10)


# --------------------------------------------------------------------------- #
# Multi-resource requirements.
# --------------------------------------------------------------------------- #

def test_fixed_requirement_names_exactly_one_resource():
    with pytest.raises(ValidationError, match='exactly one resource'):
        ResourceRequirement(requirement_id='req_1', requirement_kind='dock',
                            eligible_resource_ids=('res_1', 'res_2'), selection='fixed')


def test_choose_one_requirement_allows_alternatives():
    requirement = ResourceRequirement(requirement_id='req_1', requirement_kind='dock',
                                      eligible_resource_ids=('res_1', 'res_2'),
                                      selection='choose_one')
    assert requirement.selection == 'choose_one'


def test_requirement_needs_an_eligible_resource():
    with pytest.raises(ValidationError, match='at least one eligible resource'):
        ResourceRequirement(requirement_id='req_1', requirement_kind='dock',
                            eligible_resource_ids=())


def test_requirement_kind_is_required_and_not_defaulted():
    # requirement_kind is an opaque string like operation_kind; what matters is
    # that a missing kind is an error rather than a silent empty default.
    with pytest.raises(ValidationError):
        ResourceRequirement(requirement_id='req_1', eligible_resource_ids=('res_1',))


def _operation(**overrides):
    payload = {
        'operation_id': 'op_1-load',
        'order_ids': ('ord_1',),
        'warehouse_id': 'wh_1',
        'resource_id': 'res_1',
        'operation_kind': 'load',
        'duration_s': 60,
        'release_at_s': 0,
        'deadline_at_s': 3600,
    }
    payload.update(overrides)
    return Operation.model_validate(payload)


def test_single_resource_operation_stays_backward_compatible():
    operation = _operation()
    assert operation.requirements == ()
    assert operation.primary_requirement_id is None
    assert operation.setup_class is None


def test_requirements_require_a_primary_requirement():
    with pytest.raises(ValidationError, match='primary_requirement_id'):
        _operation(requirements=[{'requirement_id': 'req_1', 'requirement_kind': 'dock',
                                  'eligible_resource_ids': ['res_1']}])


def test_primary_requirement_must_be_declared():
    with pytest.raises(ValidationError, match='must be one of the requirements'):
        _operation(
            requirements=[{'requirement_id': 'req_1', 'requirement_kind': 'dock',
                           'eligible_resource_ids': ['res_1']}],
            primary_requirement_id='req_2',
        )


def test_requirement_ids_unique_per_operation():
    with pytest.raises(ValidationError, match='unique per operation'):
        _operation(
            requirements=[
                {'requirement_id': 'req_1', 'requirement_kind': 'dock',
                 'eligible_resource_ids': ['res_1']},
                {'requirement_id': 'req_1', 'requirement_kind': 'worker',
                 'eligible_resource_ids': ['res_2']},
            ],
            primary_requirement_id='req_1',
        )


def test_primary_requirement_without_requirements_rejected():
    with pytest.raises(ValidationError, match='requires requirements'):
        _operation(primary_requirement_id='req_1')


def test_resource_assignment_is_explicit_not_derived():
    assignment = ResourceAssignment(requirement_id='req_1', resource_id='res_1')
    assert assignment.quantity_units == 1


# --------------------------------------------------------------------------- #
# Setup / changeover: missing rule means unknown, never free.
# --------------------------------------------------------------------------- #

def _policy(**overrides):
    payload = {
        'policy_id': 'pol_1',
        'version': '1',
        'rule_version': 'r05-freeze-0.2.0',
        'rendering': 'gap',
        'rules': [{'from_class': 'class_a', 'to_class': 'class_b', 'duration_s': 1800}],
    }
    payload.update(overrides)
    return SetupPolicy.model_validate(payload)


def test_setup_policy_has_no_zero_default():
    policy = _policy()
    assert policy.default_duration_s is None
    assert policy.rendering == 'gap'


def test_setup_policy_rejects_duplicate_pairs():
    with pytest.raises(ValidationError, match='unique per class pair'):
        _policy(rules=[
            {'from_class': 'class_a', 'to_class': 'class_b', 'duration_s': 1800},
            {'from_class': 'class_a', 'to_class': 'class_b', 'duration_s': 600},
        ])


def test_setup_class_zero_duration_is_explicit_not_implicit():
    rule = ChangeoverRule(from_class='class_a', to_class='class_a', duration_s=0)
    assert rule.duration_s == 0


def test_resource_with_setup_policy_must_declare_initial_class():
    with pytest.raises(ValidationError, match='initial_setup_class'):
        WarehouseResource(resource_id='res_1', warehouse_id='wh_1', version=1,
                          resource_kind='dock', capacity_units=1,
                          available_windows=({'start_s': 0, 'end_s': 3600},),
                          setup_policy_id='pol_1')


def test_initial_class_without_policy_rejected():
    with pytest.raises(ValidationError, match='requires setup_policy_id'):
        WarehouseResource(resource_id='res_1', warehouse_id='wh_1', version=1,
                          resource_kind='dock', capacity_units=1,
                          available_windows=({'start_s': 0, 'end_s': 3600},),
                          initial_setup_class='class_a')


def test_setup_operation_must_reference_its_task():
    with pytest.raises(ValidationError, match='must reference the task'):
        ScheduledOperation(operation_id='op_1-setup', resource_id='res_1',
                           start_s=0, end_s=600, scheduled_kind='setup')


def test_task_cannot_reference_setup_target():
    with pytest.raises(ValidationError, match='only setup operations'):
        ScheduledOperation(operation_id='op_1-load', resource_id='res_1', start_s=0,
                           end_s=600, setup_for_operation_id='op_2-load')


def test_task_operation_is_the_default_kind():
    scheduled = ScheduledOperation(operation_id='op_1-load', resource_id='res_1',
                                   start_s=0, end_s=600)
    assert scheduled.scheduled_kind == 'task'


# --------------------------------------------------------------------------- #
# Pre-cooling, exposure and compatibility.
# --------------------------------------------------------------------------- #

def test_precool_requires_eligible_resource():
    with pytest.raises(ValidationError, match='at least one eligible resource'):
        PrecoolRequirement(requirement_id='pre_1', batch_id='bat_1', warehouse_id='wh_1',
                           precool_operation_id='op_1-precool', min_duration_s=1800,
                           target_temperature_zone='chilled', eligible_resource_ids=())


def test_exposure_limit_needs_scopes():
    with pytest.raises(ValidationError, match='at least one scope'):
        ExposureLimit(limit_id='exp_1', batch_id='bat_1', max_exposure_s=3600, scopes=(),
                      rule_version='v1',
                      source={'source_kind': 'simulation', 'source_ref': 'x',
                              'observed_at': '2026-10-23T00:00:00Z', 'rule_version': 'v1'})


def test_exposure_segment_must_be_forward_in_time():
    with pytest.raises(ValidationError, match='end_s must be after start_s'):
        ExposureSegment(segment_id='seg_1', batch_id='bat_1', scope='waiting',
                        start_s=100, end_s=100, source_kind='planned')


def test_exposure_scopes_cannot_duplicate():
    with pytest.raises(ValidationError, match='scopes must be unique'):
        ExposureLimit(limit_id='exp_1', batch_id='bat_1', max_exposure_s=3600,
                      scopes=('loading', 'loading'), rule_version='v1',
                      source={'source_kind': 'simulation', 'source_ref': 'x',
                              'observed_at': '2026-10-23T00:00:00Z', 'rule_version': 'v1'})


def test_batch_temperature_range_is_ordered():
    with pytest.raises(ValidationError, match='must not exceed'):
        BatchCompatibility(batch_id='bat_1', warehouse_id='wh_1', temperature_zone='chilled',
                           min_temperature_decic=60, max_temperature_decic=20)


def test_compatibility_policy_is_symmetric():
    policy = CompatibilityPolicy(policy_id='pol_1', version='1', rule_version='v1',
                                 incompatible_class_pairs=(('class_a', 'class_b'),))
    assert policy.forbidden('class_a', 'class_b') is True
    assert policy.forbidden('class_b', 'class_a') is True
    assert policy.forbidden('class_a', 'class_c') is False


# --------------------------------------------------------------------------- #
# Cold-chain ids are unique where the model indexes them.
# --------------------------------------------------------------------------- #

def test_snapshot_rejects_duplicate_occupancy_ids():
    one = {'occupancy_id': 'occ_1', 'batch_id': 'bat_1', 'location_id': 'loc_1',
           'capacity_use': [WEIGHT], 'origin': 'initial_stock'}
    two = dict(one, batch_id='bat_2')
    with pytest.raises(ValidationError, match='unique occupancy_id'):
        ColdChainSnapshot(rule_version='v1', horizon_s=3600, occupancies=(one, two))


def test_plan_rejects_duplicate_segment_ids():
    segment = {'segment_id': 'seg_1', 'batch_id': 'bat_1', 'scope': 'waiting',
               'start_s': 0, 'end_s': 60, 'source_kind': 'planned'}
    with pytest.raises(ValidationError, match='unique segment_id'):
        ColdChainPlan(rule_version='v1', exposure_segments=(segment, dict(segment)))


def test_changeover_records_both_neighbours():
    changeover = ScheduledChangeover(
        changeover_id='chg_1', resource_id='res_1', from_class='class_a',
        to_class='class_b', duration_s=1800, after_operation_id='op_1-load',
        before_operation_id='op_2-unload')
    assert changeover.setup_operation_id is None


# --------------------------------------------------------------------------- #
# ValidationReport: missing data is never a pass (R05 point 8).
# --------------------------------------------------------------------------- #

def test_passed_report_cannot_carry_unchecked_rules():
    with pytest.raises(ValidationError, match='unchecked rules'):
        ValidationReport(status='passed', validator_version='0.2',
                         checked_rule_ids=('r05.peak_capacity',), violations=(),
                         not_checked_rule_ids=('r05.exposure',))


def test_failed_report_requires_violations():
    with pytest.raises(ValidationError, match='at least one violation'):
        ValidationReport(status='failed', validator_version='0.2',
                         checked_rule_ids=('r05.peak_capacity',), violations=())


def test_violation_carries_interval_and_capacity_evidence():
    violation = Violation(
        rule_id='r05.peak_capacity', object_ids=('loc_1', 'bat_2'),
        message='peak occupancy 11 exceeds capacity 10',
        evidence=RuleEvidence(
            rule_version='r05-freeze-0.2.0', capacity_unit='weight_g',
            observed_value=11, limit_value=10, interval_start_s=5, interval_end_s=10))
    assert violation.evidence.observed_value == 11


def test_evidence_interval_needs_both_ends():
    with pytest.raises(ValidationError, match='both start and end'):
        RuleEvidence(rule_version='v1', interval_start_s=5)


def test_capacity_evidence_needs_unit_and_limit():
    with pytest.raises(ValidationError, match='observed and limit together'):
        RuleEvidence(rule_version='v1', observed_value=11)
    with pytest.raises(ValidationError, match='capacity unit'):
        RuleEvidence(rule_version='v1', observed_value=11, limit_value=10)


def test_violation_stays_compatible_without_evidence():
    violation = Violation(rule_id='warehouse.scope', object_ids=('op_1',),
                          message='operation is outside requested scope')
    assert violation.evidence is None


# --------------------------------------------------------------------------- #
# Strict models: no silent aliases or extra fields.
# --------------------------------------------------------------------------- #

@pytest.mark.parametrize('extra', ['quantities', 'capacity', 'zone'])
def test_coldchain_models_forbid_extra_fields(extra):
    with pytest.raises(ValidationError):
        StorageLocation.model_validate({
            'location_id': 'loc_1', 'warehouse_id': 'wh_1', 'zone_id': 'zone_1',
            'version': 1, 'capacities': [WEIGHT], extra: 1,
        })


def test_capacity_amount_is_not_coerced_from_string():
    with pytest.raises(ValidationError):
        CapacityAmount(unit='weight_g', amount='10')
