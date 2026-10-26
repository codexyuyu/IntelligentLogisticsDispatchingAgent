"""R08 four-role contract-net negotiation tests.

Two layers: scripted roles for the protocol itself (bid validity, conflicts,
confirmation/revocation, termination, idempotency, transcript) and the concrete
warehouse/transport/exception roles driven by real shared-contract objects.
"""
from __future__ import annotations

import datetime as dt

import pytest

from app.application.contract_net import (
    Bid,
    ContractNet,
    ExceptionRecoveryRole,
    NegotiationError,
    NegotiationPolicy,
    TaskSpec,
    TransportWindowRole,
    WarehouseWindowRole,
)
from app.contracts.entities import (
    Operation,
    Order,
    PlanningSnapshot,
    TravelMatrix,
    Vehicle,
    Warehouse,
    WarehouseResource,
)
from app.contracts.planning import WarehouseHandoff

ORIGIN = dt.datetime(2026, 10, 24, 0, 0, tzinfo=dt.timezone.utc)
SOURCE = {
    'source_kind': 'simulation',
    'source_ref': 'tests/negotiation/test_contract_net.py',
    'observed_at': '2026-10-24T00:00:00Z',
    'rule_version': 'r08-test',
}
DT = dt.timezone.utc


class ScriptedRole:
    """Deterministic role used to exercise the protocol, not the domain."""

    def __init__(self, role: str, cost: int | None = None, *, confirm_ok: bool = True,
                 offset: int = 0, expires_delta: int = 300, resources: tuple = ('dock_1',),
                 absolute_window: tuple[int, int] | None = None):
        self.role = role
        self.cost = cost
        self.confirm_ok = confirm_ok
        self.offset = offset
        self.expires_delta = expires_delta
        self.resources = resources
        self.absolute_window = absolute_window
        self.confirm_calls = 0

    def bid(self, cfp):
        if self.cost is None:
            return None
        task = cfp.task
        start, end = self.absolute_window or (task.window_start_s + self.offset,
                                             task.window_end_s + self.offset)
        return Bid(
            bid_id=f'bid_{cfp.round_no}_{self.role}_{task.task_id}', cfp_id=cfp.cfp_id,
            task_id=task.task_id, round_no=cfp.round_no, role=self.role,
            valid_from_s=start, valid_to_s=end,
            expires_at_s=cfp.respond_by_s + self.expires_delta,
            cost=self.cost, exclusive_resource_ids=self.resources,
        )

    def confirm(self, award):
        self.confirm_calls += 1
        return self.confirm_ok


def net(warehouse=None, transport=None, exception=None, **policy):
    return ContractNet(
        [warehouse or ScriptedRole('warehouse', 30),
         transport or ScriptedRole('transport', 20),
         exception or ScriptedRole('exception', 40)],
        NegotiationPolicy(**policy) if policy else None,
    )


def task(task_id='op_1', start=0, end=100, resources=('dock_1',)):
    return TaskSpec(task_id=task_id, warehouse_id='wh_1', window_start_s=start,
                    window_end_s=end, exclusive_resource_ids=resources)


# --------------------------------------------------------------------------- #
# Award, ranking and transcript
# --------------------------------------------------------------------------- #

def test_cheapest_bid_wins_and_is_confirmed():
    result = net().negotiate([task()], now_s=0)

    assert result.status == 'confirmed'
    assert result.reason == 'all_tasks_confirmed'
    assert [award.role for award in result.awards] == ['transport']
    assert [message.kind for message in result.transcript] == [
        'cfp', 'bid', 'bid', 'bid', 'award', 'confirm', 'close',
    ]
    assert [message.seq for message in result.transcript] == list(range(1, 8))
    assert result.outcome_of('op_1') == 'confirmed'
    assert result.conflicts == ()


def test_rank_by_earliest_prefers_the_sooner_window():
    early = ScriptedRole('warehouse', 50, absolute_window=(0, 20))
    late = ScriptedRole('transport', 10, absolute_window=(10, 30))
    result = net(warehouse=early, transport=late, exception=ScriptedRole('exception', None),
                 rank_by='earliest').negotiate([task()], now_s=0)

    assert result.status == 'confirmed'
    assert [award.role for award in result.awards] == ['warehouse']


def test_digest_is_deterministic_for_identical_inputs():
    first = net().negotiate([task()], now_s=0)
    second = net().negotiate([task()], now_s=0)

    assert first.digest == second.digest
    assert first.awards == second.awards


def test_digest_changes_when_bids_change():
    cheap = net(transport=ScriptedRole('transport', 20)).negotiate([task()], now_s=0)
    pricey = net(transport=ScriptedRole('transport', 25)).negotiate([task()], now_s=0)

    assert cheap.digest != pricey.digest


# --------------------------------------------------------------------------- #
# Bid validity
# --------------------------------------------------------------------------- #

def test_expired_bid_is_rejected_and_recorded():
    class ExpiredRole(ScriptedRole):
        def bid(self, cfp):
            fresh = super().bid(cfp)
            return Bid(**{**fresh.__dict__, 'expires_at_s': 0})

    stale = ExpiredRole('warehouse', 10)
    result = net(warehouse=stale, transport=ScriptedRole('transport', None),
                 exception=ScriptedRole('exception', None),
                 max_rounds=1).negotiate([task()], now_s=10)

    assert result.status == 'infeasible'
    assert result.reason == 'no_acceptable_bid'
    bid_messages = [m for m in result.transcript if m.kind == 'bid']
    assert bid_messages and bid_messages[0].detail == 'bid_expired'
    assert result.awards == ()


def test_bid_outside_the_task_window_is_rejected():
    outside = ScriptedRole('warehouse', 10, absolute_window=(0, 150))
    result = net(warehouse=outside, transport=ScriptedRole('transport', None),
                 exception=ScriptedRole('exception', None),
                 max_rounds=1).negotiate([task()], now_s=0)

    details = [m.detail for m in result.transcript if m.kind == 'bid']
    assert details == ['bid_outside_task_window']
    assert result.status == 'infeasible'


def test_stale_round_bid_is_rejected():
    class StaleRole(ScriptedRole):
        def bid(self, cfp):
            fresh = super().bid(cfp)
            return Bid(**{**fresh.__dict__, 'round_no': cfp.round_no + 1})

    result = net(warehouse=StaleRole('warehouse', 10),
                 transport=ScriptedRole('transport', None),
                 exception=ScriptedRole('exception', None),
                 max_rounds=1).negotiate([task()], now_s=0)

    assert [m.detail for m in result.transcript if m.kind == 'bid'] == ['stale_round']
    assert result.status == 'infeasible'


# --------------------------------------------------------------------------- #
# Conflicts
# --------------------------------------------------------------------------- #

def test_cross_task_resource_overlap_is_reported_as_conflict():
    roles = [ScriptedRole('warehouse', 10, absolute_window=(0, 50), resources=('dock_1',)),
             ScriptedRole('transport', None),
             ScriptedRole('exception', None)]
    net_ = ContractNet(roles, NegotiationPolicy(max_rounds=1))
    result = net_.negotiate([task('op_1', 0, 100), task('op_2', 0, 100)], now_s=0)

    assert len(result.conflicts) == 1
    conflict = result.conflicts[0]
    assert conflict.resource_ids == ('dock_1',)
    assert {conflict.blocking_bid_id, conflict.rejected_bid_id} == {
        'bid_1_warehouse_op_1', 'bid_1_warehouse_op_2'}
    assert result.outcome_of('op_2') == 'conflicted'
    assert result.status == 'partial'
    assert any(m.kind == 'conflict' for m in result.transcript)


def test_non_overlapping_bids_on_the_same_resource_do_not_conflict():
    roles = [ScriptedRole('warehouse', 10, resources=('dock_1',)),
             ScriptedRole('transport', None),
             ScriptedRole('exception', None)]
    result = ContractNet(roles).negotiate(
        [task('op_1', 0, 100), task('op_2', 200, 300)], now_s=0,
    )

    assert result.conflicts == ()
    assert result.status == 'confirmed'
    assert {award.task_id for award in result.awards} == {'op_1', 'op_2'}


# --------------------------------------------------------------------------- #
# Confirmation, revocation, termination
# --------------------------------------------------------------------------- #

def test_refused_confirmation_revokes_and_retries_next_round():
    class FlakyRole(ScriptedRole):
        calls = 0

        def confirm(self, award):
            type(self).calls += 1
            return type(self).calls > 1

    flaky = FlakyRole('warehouse', 10)

    result = net(warehouse=flaky, transport=ScriptedRole('transport', 50),
                 exception=ScriptedRole('exception', 60)).negotiate([task()], now_s=0)

    assert result.status == 'confirmed'
    assert result.rounds_used == 2
    kinds = [m.kind for m in result.transcript]
    assert kinds.count('revoke') == 1
    assert kinds.count('cfp') == 2
    assert result.transcript[kinds.index('revoke')].detail == 'confirmation_refused'


def test_permanent_refusal_exhausts_rounds_without_fake_award():
    stubborn = ScriptedRole('warehouse', 10, confirm_ok=False)
    result = net(warehouse=stubborn, transport=ScriptedRole('transport', 50),
                 exception=ScriptedRole('exception', 60), max_rounds=2).negotiate([task()], now_s=0)

    assert result.status == 'exhausted'
    assert result.reason == 'confirmation_refused'
    assert result.awards == ()
    assert result.rounds_used == 2
    assert result.outcome_of('op_1') == 'award_retracted'


def test_no_bids_is_infeasible():
    none = ScriptedRole('warehouse', None)
    result = net(warehouse=none, transport=ScriptedRole('transport', None),
                 exception=ScriptedRole('exception', None)).negotiate([task()], now_s=0)

    assert result.status == 'infeasible'
    assert result.reason == 'no_bids'
    assert result.rounds_used == 1


def test_deadline_stops_further_rounds():
    stubborn = ScriptedRole('warehouse', 10, confirm_ok=False)
    result = net(warehouse=stubborn, transport=ScriptedRole('transport', 50),
                 exception=ScriptedRole('exception', 60),
                 max_rounds=5, respond_timeout_s=60, deadline_s=60).negotiate([task()], now_s=0)

    assert result.status == 'expired'
    assert result.reason == 'deadline_exceeded'
    assert result.rounds_used == 1


# --------------------------------------------------------------------------- #
# Idempotency and revocation after confirmation
# --------------------------------------------------------------------------- #

def test_replayed_idempotency_key_returns_identical_result_without_new_messages():
    coordinator = net()
    first = coordinator.negotiate([task()], now_s=0, idempotency_key='req-1')
    transcript_after_first = len(coordinator.transcript())

    replay = coordinator.negotiate([task()], now_s=0, idempotency_key='req-1')

    assert replay == first
    assert len(coordinator.transcript()) == transcript_after_first


def test_second_key_on_awarded_task_reports_already_awarded():
    coordinator = net()
    coordinator.negotiate([task()], now_s=0, idempotency_key='req-1')
    again = coordinator.negotiate([task()], now_s=0, idempotency_key='req-2')

    assert again.status == 'already_awarded'
    assert again.awards == ()
    assert coordinator.award_of('op_1') is not None


def test_revoke_after_confirmation_releases_the_award():
    coordinator = net()
    coordinator.negotiate([task()], now_s=0)
    assert coordinator.award_of('op_1') is not None

    revoked = coordinator.revoke('op_1', now_s=120, reason='operator_revoked')

    assert revoked.status == 'revoked'
    assert revoked.outcome_of('op_1') == 'revoked'
    assert coordinator.award_of('op_1') is None
    assert [m.kind for m in revoked.transcript][-1] == 'revoke'


def test_revoke_unknown_task_is_explicit_not_silent():
    revoked = net().revoke('op_missing', now_s=0)

    assert revoked.status == 'revoked'
    assert revoked.reason == 'nothing_to_revoke'
    assert revoked.outcome_of('op_missing') == 'not_awarded'


# --------------------------------------------------------------------------- #
# Construction guards
# --------------------------------------------------------------------------- #

def test_missing_role_is_rejected():
    with pytest.raises(NegotiationError, match='missing_roles:exception'):
        ContractNet([ScriptedRole('warehouse', 10), ScriptedRole('transport', 10)])


def test_duplicate_role_is_rejected():
    with pytest.raises(NegotiationError, match='duplicate_role:warehouse'):
        ContractNet([ScriptedRole('warehouse', 10), ScriptedRole('warehouse', 20),
                     ScriptedRole('transport', 10), ScriptedRole('exception', 10)])


def test_policy_rejects_deadline_shorter_than_response_timeout():
    with pytest.raises(NegotiationError, match='deadline_shorter_than_response_timeout'):
        NegotiationPolicy(respond_timeout_s=60, deadline_s=30)


# --------------------------------------------------------------------------- #
# Concrete roles on real contract objects
# --------------------------------------------------------------------------- #

def _snapshot(resource_windows=(('start_s', 0, 'end_s', 50), ('start_s', 60, 'end_s', 200)),
              operation_window=(0, 200)) -> PlanningSnapshot:
    return PlanningSnapshot(
        snapshot_id='snap_r08', version=1, origin_at=ORIGIN, simulation_time_s=0,
        rule_version='r08-test',
        orders=(Order(order_id='ord_1', version=1, warehouse_id='wh_1', batch_id='bat_1',
                      delivery_node_id='node_2', quantity_units=1, weight_kg=10, volume_l=10,
                      temperature_zone='chilled',
                      service_window={'start_s': 0, 'end_s': 600},
                      service_duration_s=10, freshness_deadline_s=600, source=SOURCE),),
        vehicles=(Vehicle(vehicle_id='veh_1', version=1, warehouse_id='wh_1',
                          start_node_id='node_1', end_node_id='node_1', current_node_id='node_1',
                          capacity_weight_kg=100, capacity_volume_l=100,
                          remaining_weight_kg=100, remaining_volume_l=100,
                          temperature_zone='chilled',
                          shift_window={'start_s': 100, 'end_s': 500},
                          available_at_s=120, source=SOURCE),),
        warehouses=(Warehouse(warehouse_id='wh_1', version=1, node_id='node_1',
                              temperature_zones=('chilled',)),),
        resources=(WarehouseResource(
            resource_id='res_dock1', warehouse_id='wh_1', version=1, resource_kind='dock',
            capacity_units=1,
            available_windows=tuple({'start_s': a, 'end_s': b} for _, a, _, b in resource_windows),
        ),),
        stock_lots=(),
        operations=(Operation(operation_id='op_1', order_ids=('ord_1',), warehouse_id='wh_1',
                              resource_id='res_dock1', operation_kind='load', duration_s=30,
                              release_at_s=operation_window[0],
                              deadline_at_s=operation_window[1]),),
        matrix=TravelMatrix(matrix_id='matrix_r08', version=1,
                            node_ids=('node_1', 'node_2'),
                            duration_s=((0, 60), (60, 0)),
                            distance_m=((0, 1000), (1000, 0)), source=SOURCE),
    )


def test_warehouse_role_bids_the_earliest_calendar_slot():
    snapshot = _snapshot()
    role = WarehouseWindowRole(snapshot, 'res_dock1')
    result = net(warehouse=role, transport=ScriptedRole('transport', None),
                 exception=ScriptedRole('exception', None)).negotiate([task()], now_s=0)

    assert result.status == 'confirmed'
    award = result.awards[0]
    assert award.role == 'warehouse'
    bid_message = next(m for m in result.transcript if m.kind == 'bid')
    assert bid_message.detail.startswith('cost=30;window=[0,30)')


def test_warehouse_role_skips_an_unavailable_gap():
    narrow = _snapshot(resource_windows=(('start_s', 100, 'end_s', 200),))
    role = WarehouseWindowRole(narrow, 'res_dock1')
    result = net(warehouse=role, transport=ScriptedRole('transport', None),
                 exception=ScriptedRole('exception', None)).negotiate([task('op_1', 0, 200)], now_s=0)

    bid_message = next(m for m in result.transcript if m.kind == 'bid')
    assert 'window=[100,130)' in bid_message.detail


def test_transport_role_respects_shift_and_handoff():
    snapshot = _snapshot()
    handoff = WarehouseHandoff(order_id='ord_1', warehouse_id='wh_1', ready_at_s=200,
                               loading_window={'start_s': 200, 'end_s': 600})
    role = TransportWindowRole(snapshot.vehicles[0], handoffs=(handoff,))
    result = net(warehouse=ScriptedRole('warehouse', None), transport=role,
                 exception=ScriptedRole('exception', None)).negotiate([task('op_1', 0, 600)], now_s=0)

    bid_message = next(m for m in result.transcript if m.kind == 'bid' and m.role == 'transport')
    assert bid_message.detail == 'cost=300;window=[200,500)'
    assert result.awards[0].role == 'transport'


def test_exception_role_declines_when_recovery_overruns_the_window():
    too_slow = ExceptionRecoveryRole(disruption_at_s=0, recovery_s=200, resource_id='dock_1')
    result = net(warehouse=ScriptedRole('warehouse', None), transport=ScriptedRole('transport', None),
                 exception=too_slow).negotiate([task('op_1', 0, 100)], now_s=0)

    assert result.status == 'infeasible'
    assert not [m for m in result.transcript if m.kind == 'bid' and m.role == 'exception']


def test_three_real_roles_confirm_two_independent_tasks():
    snapshot = _snapshot()
    handoff = WarehouseHandoff(order_id='ord_1', warehouse_id='wh_1', ready_at_s=150,
                               loading_window={'start_s': 150, 'end_s': 600})
    net_ = ContractNet([
        WarehouseWindowRole(snapshot, 'res_dock1'),
        TransportWindowRole(snapshot.vehicles[0], handoffs=(handoff,)),
        ExceptionRecoveryRole(disruption_at_s=0, recovery_s=20, resource_id='res_dock2'),
    ])
    result = net_.negotiate(
        [task('op_1', 0, 600, resources=('res_dock1',)),
         task('op_2', 0, 600, resources=('res_dock2',))],
        now_s=0,
    )

    assert result.status == 'confirmed'
    assert len(result.awards) == 2
    assert {award.task_id for award in result.awards} == {'op_1', 'op_2'}
    # Both tasks see the exception role's res_dock2 offer; only one may hold it.
    assert len(result.conflicts) == 1
    assert result.conflicts[0].resource_ids == ('res_dock2',)





