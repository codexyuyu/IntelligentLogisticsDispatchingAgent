"""R08 concrete role tests: warehouse, transport and exception bidders.

The roles are driven through the real coordinator (``ContractNet``) and
shared-contract ``TimeWindowDTO`` windows, mirroring the partner R08 delivery
semantics: earliest feasible warehouse slot, shift/handoff-bounded transport
window, and an exception role that stays silent unless a disruption is declared.
"""
from __future__ import annotations

from logistics_agents.contract_net import CallForProposals, TaskSpec
from logistics_agents.contract_net_roles import (
    ExceptionRecoveryRole,
    HandoffFact,
    OperationFact,
    ResourceCalendar,
    TransportWindowRole,
    VehicleAvailability,
    WarehouseWindowRole,
    build_negotiator,
)
from logistics_contracts.entities import TimeWindowDTO


def window(earliest: int, latest: int) -> TimeWindowDTO:
    return TimeWindowDTO(earliest_s=earliest, latest_s=latest)


def task(task_id: str = 'op_load_1', start: int = 0, end: int = 600,
         warehouse: str = 'wh_1') -> TaskSpec:
    return TaskSpec(task_id=task_id, warehouse_id=warehouse,
                    window_start_s=start, window_end_s=end)


def cfp_for(spec: TaskSpec, round_no: int = 1) -> CallForProposals:
    return CallForProposals(cfp_id=f'cfp_{round_no}_{spec.task_id}', round_no=round_no,
                            issued_at_s=0, respond_by_s=60, task=spec)


# --------------------------------------------------------------------------- #
# Warehouse role
# --------------------------------------------------------------------------- #

def test_warehouse_role_bids_the_earliest_feasible_calendar_slot():
    calendar = ResourceCalendar(resource_id='res_1',
                                windows=(window(0, 60), window(300, 600)))
    operation = OperationFact(operation_id='op_load_1', release_at_s=50,
                              deadline_at_s=500, duration_s=40)
    role = WarehouseWindowRole((operation,), calendar)

    bid = role.bid(cfp_for(task()))

    assert bid is not None
    assert (bid.valid_from_s, bid.valid_to_s) == (300, 340)
    assert bid.cost == 40
    assert bid.exclusive_resource_ids == ('res_1',)
    assert bid.role == 'warehouse'


def test_warehouse_role_stays_silent_when_no_calendar_window_fits():
    calendar = ResourceCalendar(resource_id='res_1', windows=(window(0, 50),))
    operation = OperationFact(operation_id='op_load_1', release_at_s=0,
                              deadline_at_s=600, duration_s=120)
    role = WarehouseWindowRole((operation,), calendar)

    assert role.bid(cfp_for(task())) is None


def test_warehouse_role_ignores_tasks_it_does_not_carry():
    calendar = ResourceCalendar(resource_id='res_1', windows=(window(0, 600),))
    role = WarehouseWindowRole((), calendar)

    assert role.bid(cfp_for(task('op_other'))) is None


# --------------------------------------------------------------------------- #
# Transport role
# --------------------------------------------------------------------------- #

def test_transport_window_respects_shift_available_and_handoff():
    vehicle = VehicleAvailability(vehicle_id='veh_1', shift=window(100, 500),
                                  available_at_s=150)
    handoff = HandoffFact(warehouse_id='wh_1', ready_at_s=200)
    role = TransportWindowRole(vehicle, handoffs=(handoff,))

    bid = role.bid(cfp_for(task()))

    assert bid is not None
    assert (bid.valid_from_s, bid.valid_to_s) == (200, 500)
    assert bid.cost == 300
    assert bid.exclusive_resource_ids == ('veh_1',)
    assert bid.role == 'transport'


def test_transport_role_stays_silent_when_shift_misses_the_task_window():
    vehicle = VehicleAvailability(vehicle_id='veh_1', shift=window(700, 800))
    role = TransportWindowRole(vehicle)

    assert role.bid(cfp_for(task(end=600))) is None


# --------------------------------------------------------------------------- #
# Exception role
# --------------------------------------------------------------------------- #

def test_exception_role_is_silent_without_a_declared_disruption():
    role = ExceptionRecoveryRole(disruption_at_s=None, recovery_s=60, resource_id='res_1')

    assert role.bid(cfp_for(task())) is None


def test_exception_role_bids_recovery_window_and_refuses_overruns():
    role = ExceptionRecoveryRole(disruption_at_s=100, recovery_s=60, resource_id='res_1')

    bid = role.bid(cfp_for(task()))

    assert bid is not None
    assert (bid.valid_from_s, bid.valid_to_s) == (100, 160)
    assert bid.cost == 60

    tight = role.bid(cfp_for(task(end=150)))

    assert tight is None


# --------------------------------------------------------------------------- #
# Assembly: build_negotiator drives the full four-role protocol
# --------------------------------------------------------------------------- #

def facts():
    calendar = ResourceCalendar(resource_id='res_1', windows=(window(0, 600),))
    operation = OperationFact(operation_id='op_load_1', release_at_s=0,
                              deadline_at_s=600, duration_s=40)
    vehicle = VehicleAvailability(vehicle_id='veh_1', shift=window(0, 600))
    return calendar, operation, vehicle


def test_build_negotiator_confirms_the_cheapest_role_end_to_end():
    calendar, operation, vehicle = facts()

    net = build_negotiator(calendar=calendar, vehicle=vehicle, operations=(operation,))
    result = net.negotiate([task()], now_s=0)

    assert result.status == 'confirmed'
    assert result.reason == 'all_tasks_confirmed'
    assert [award.role for award in result.awards] == ['warehouse']
    # No disruption was declared, so the exception role never bids.
    kinds = [message.kind for message in result.transcript]
    assert kinds == ['cfp', 'bid', 'bid', 'award', 'confirm', 'close']
    assert [message.role for message in result.transcript
            if message.kind == 'bid'] == ['warehouse', 'transport']


def test_build_negotiator_with_disruption_lets_only_the_exception_role_bid():
    calendar, operation, vehicle = facts()
    # Both the warehouse calendar and the vehicle shift end before the task
    # window opens, so the exception role is the only feasible bidder.
    calendar = ResourceCalendar(resource_id='res_1', windows=(window(0, 100),))
    vehicle = VehicleAvailability(vehicle_id='veh_1', shift=window(0, 100))

    net = build_negotiator(calendar=calendar, vehicle=vehicle, operations=(operation,),
                           disruption_at_s=250, recovery_s=60)
    result = net.negotiate([task(start=200)], now_s=0)

    assert result.status == 'confirmed'
    assert [award.role for award in result.awards] == ['exception']
    assert result.outcome_of('op_load_1') == 'confirmed'


def test_build_negotiator_is_deterministic_across_identical_runs():
    calendar, operation, vehicle = facts()

    first = build_negotiator(calendar=calendar, vehicle=vehicle,
                             operations=(operation,)).negotiate([task()], now_s=0)
    second = build_negotiator(calendar=calendar, vehicle=vehicle,
                              operations=(operation,)).negotiate([task()], now_s=0)

    assert first.digest == second.digest
    assert first.awards == second.awards
