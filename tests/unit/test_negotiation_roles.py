"""Real domain objects; hand-calculated positive/negative R08 window cases."""
import json
from dataclasses import replace
from datetime import UTC, datetime
from pathlib import Path
from uuid import UUID

import pytest

from logistics_agents.contract_net import Award, CallForProposals, ContractNet, NegotiationPolicy, TaskSpec
from logistics_agents.negotiation_roles import (
    ExceptionRecoveryRole,
    RecoveryDeclaration,
    TransportBinding,
    TransportWindowRole,
    WarehouseWindowRole,
)
from logistics_contracts import entities
from logistics_contracts.planning import TravelMatrixDTO
from logistics_domain.planning import (
    OperationAssignment,
    PlanningScope,
    PlanningSnapshot,
    ResourceRequirement,
    ResourceRevision,
    WarehouseTask,
    content_hash,
)
from logistics_domain.primitives import CalendarInterval, EntityRef, ResourceCalendar, TimeWindow
from logistics_domain.resources import OperationKind, ResourceBundle, ResourceCalendarBinding
from logistics_domain.states import EntityKind, EntityState, ResourceKind

EPOCH = datetime(2026, 1, 1, tzinfo=UTC)


def scenario(intervals=((0, 50, 1), (60, 600, 1))):
    data = json.loads((Path(__file__).resolve().parents[2] / 'data/scenarios/tiny_master.json').read_text())
    groups = {}
    for name, dto in (('orders', entities.OrderDTO), ('cargo', entities.CargoDTO),
                      ('vehicles', entities.VehicleDTO), ('drivers', entities.DriverDTO),
                      ('warehouses', entities.WarehouseDTO), ('zones', entities.ZoneDTO),
                      ('locations', entities.StorageLocationDTO), ('docks', entities.DockDTO),
                      ('workers', entities.WorkerDTO), ('equipment', entities.EquipmentDTO)):
        groups[name] = tuple(dto.model_validate(v).to_domain() for v in data[name])
    groups['orders'] = tuple(replace(o, pickup_window=TimeWindow(100, 3000),
        pickup_node_id=groups['warehouses'][0].node_id, service_s=30) for o in groups['orders'][:2])
    order_ids = {o.id for o in groups['orders']}
    groups['cargo'] = tuple(c for c in groups['cargo'] if c.order_id in order_ids)
    calendar = ResourceCalendar(EPOCH, tuple(CalendarInterval(*i) for i in intervals), 1)
    dock = replace(groups['docks'][0], calendar=calendar,
                   supported_operations=(OperationKind.LOAD,))
    groups['docks'] = (dock, replace(dock, id=UUID(int=8202), code='R08-second-dock'))
    calendars = tuple(ResourceCalendarBinding(r.id, r.calendar, content_hash(r.calendar), r.calendar)
                      for name in ('warehouses', 'locations', 'docks', 'workers', 'equipment')
                      for r in groups[name])
    bundle = ResourceBundle(**{n: groups[n] for n in (
        'warehouses', 'zones', 'locations', 'docks', 'workers', 'equipment')}, calendars=calendars)
    revisions = tuple(ResourceRevision(EntityRef(EntityKind(kind), r.id, r.row_version), r.row_version)
                      for name, kind in (('orders', 'order'), ('cargo', 'cargo'), ('vehicles', 'vehicle'),
                          ('drivers', 'driver'), ('warehouses', 'warehouse'), ('zones', 'zone'),
                          ('locations', 'location'), ('docks', 'dock'), ('workers', 'worker'),
                          ('equipment', 'equipment')) for r in groups[name])
    snapshot = PlanningSnapshot.create(id=UUID(int=8200), scope=PlanningScope(
        tuple(o.id for o in groups['orders']), tuple(w.id for w in groups['warehouses']),
        tuple(v.id for v in groups['vehicles']), EPOCH, 86400),
        **{n: groups[n] for n in ('orders', 'cargo', 'vehicles', 'drivers')}, resources=bundle,
        inventory=(), revisions=revisions,
        matrices=tuple(TravelMatrixDTO.model_validate(m['payload']).to_domain() for m in data['matrices']))
    tasks = tuple(WarehouseTask(id=UUID(int=8300+i), status=EntityState.PENDING,
        created_at=EPOCH, updated_at=EPOCH, row_version=0, schema_version='2.0.0', created_by=UUID(int=1),
        order_id=order.id, warehouse_id=dock.warehouse_id, kind=OperationKind.LOAD, duration_s=30,
        window=TimeWindow(0, 600), predecessor_ids=(), requirements=(
            ResourceRequirement(ResourceKind.DOCK, (groups['docks'][i].id,), 1),), setup_class='load')
        for i, order in enumerate(groups['orders']))
    assignments = tuple(OperationAssignment(t.id, groups['docks'][i].id, 0, 30, 1)
                        for i, t in enumerate(tasks))
    return snapshot, tasks, assignments


def cfp(snapshot, task, assignments, start=0, end=600):
    resources = tuple(str(a.resource_id) for a in assignments if a.task_id == task.id)
    spec = TaskSpec(str(task.id), str(task.warehouse_id), start, end,
                    exclusive_resource_ids=resources + tuple(str(v.id) for v in snapshot.vehicles))
    return CallForProposals('cfp', 1, 0, 60, spec)


@pytest.mark.parametrize(('intervals', 'start', 'end', 'expected'), [
    (((0, 50, 1), (60, 600, 1)), 0, 100, (0, 30)),
    (((0, 20, 1), (60, 100, 1)), 0, 100, (60, 90)),
    (((0, 60, 0), (60, 100, 1)), 0, 100, (60, 90)),
    (((0, 20, 1), (20, 100, 2)), 0, 100, (0, 30)),
    (((0, 20, 1), (60, 100, 1)), 0, 89, None),
    (((0, 100, 1),), 80, 100, None),
    (((0, 100, 1),), 70, 100, (70, 100)),
])
def test_warehouse_earliest_slot_gaps_capacity_and_task_bounds(intervals, start, end, expected):
    snapshot, tasks, assignments = scenario(intervals)
    bid = WarehouseWindowRole(snapshot, tasks, assignments).bid(cfp(snapshot, tasks[0], assignments, start, end))
    assert ((bid.valid_from_s, bid.valid_to_s) if bid else None) == expected
    if bid:
        assert bid.exclusive_resource_ids == (str(assignments[0].resource_id),)


def test_warehouse_missing_resource_or_predecessor_does_not_invent_offer():
    snapshot, tasks, assignments = scenario()
    assert WarehouseWindowRole(snapshot, tasks, ()).bid(cfp(snapshot, tasks[0], assignments)) is None
    tasks = (replace(tasks[0], predecessor_ids=(UUID(int=999),)),)
    assert WarehouseWindowRole(snapshot, tasks, assignments).bid(cfp(snapshot, tasks[0], assignments)) is None


@pytest.mark.parametrize(('shift', 'available', 'ready', 'end', 'expected'), [
    ((100, 500), 120, 200, 600, (200, 230)),
    ((100, 500), 250, 200, 600, (250, 280)),
    ((300, 500), 120, 200, 600, (300, 330)),
    ((100, 220), 120, 200, 600, None),
    ((100, 500), 120, 200, 229, None),
    ((100, 500), 120, 600, 600, None),
])
def test_transport_shift_available_at_and_task_specific_handoff(shift, available, ready, end, expected):
    snapshot, tasks, assignments = scenario()
    binding = TransportBinding(str(tasks[0].id), str(tasks[0].warehouse_id), snapshot.vehicles[0].id,
                               TimeWindow(*shift), available, ready, 30)
    role = TransportWindowRole(snapshot.vehicles, (binding,))
    bid = role.bid(cfp(snapshot, tasks[0], assignments, end=end))
    assert ((bid.valid_from_s, bid.valid_to_s) if bid else None) == expected
    assert role.bid(cfp(snapshot, tasks[1], assignments)) is None


def test_transport_calendar_gap_is_not_available_shift_time():
    snapshot, tasks, assignments = scenario()
    vehicle = replace(snapshot.vehicles[0], calendar=ResourceCalendar(EPOCH, (
        CalendarInterval(0, 200, 0), CalendarInterval(250, 500, 1)), 1))
    binding = TransportBinding(str(tasks[0].id), str(tasks[0].warehouse_id), vehicle.id,
                               TimeWindow(100, 500), 120, 150, 30)
    bid = TransportWindowRole((vehicle,), (binding,)).bid(cfp(snapshot, tasks[0], assignments))
    assert (bid.valid_from_s, bid.valid_to_s) == (250, 280)


@pytest.mark.parametrize(('disruption', 'duration', 'end', 'expected'), [
    (None, 20, 100, None), (0, 20, 100, (0, 20)), (80, 20, 100, (80, 100)),
    (81, 20, 100, None), (101, 20, 100, None),
])
def test_exception_requires_declared_disruption_and_contained_recovery(disruption, duration, end, expected):
    snapshot, tasks, assignments = scenario()
    declaration = RecoveryDeclaration(str(tasks[0].id), str(assignments[0].resource_id), disruption, duration)
    role = ExceptionRecoveryRole((declaration,))
    bid = role.bid(cfp(snapshot, tasks[0], assignments, end=end))
    assert ((bid.valid_from_s, bid.valid_to_s) if bid else None) == expected
    assert role.bid(cfp(snapshot, tasks[1], assignments, end=end)) is None


def test_real_roles_two_tasks_confirmation_revoke_and_deterministic_digest():
    snapshot, tasks, assignments = scenario()
    def build():
        return ContractNet([
            WarehouseWindowRole(snapshot, tasks, assignments),
            TransportWindowRole(snapshot.vehicles, tuple(TransportBinding(str(t.id), str(t.warehouse_id),
                snapshot.vehicles[0].id, TimeWindow(0, 600), 0, 100, 30) for t in tasks)),
            ExceptionRecoveryRole(tuple(RecoveryDeclaration(str(t.id), str(a.resource_id), 0, 20)
                                        for t, a in zip(tasks, assignments, strict=True))),
        ])
    specs = tuple(cfp(snapshot, t, assignments).task for t in tasks)
    coordinator = build()
    result = coordinator.negotiate(specs, 0)
    assert result == build().negotiate(specs, 0)
    assert result.status == 'confirmed'
    assert {a.task_id for a in result.awards} == {str(t.id) for t in tasks}
    assert {m.role for m in result.transcript if m.kind == 'bid'} == {'warehouse', 'transport', 'exception'}
    assert [m.kind for m in result.transcript].count('confirm') == 2
    revoked = coordinator.revoke(str(tasks[0].id), 120)
    assert revoked.outcome_of(str(tasks[0].id)) == 'revoked'
    assert revoked.digest != result.digest


def test_real_role_conflict_survives_rounds_and_separate_calls_until_revoked():
    snapshot, tasks, assignments = scenario()
    # Both named recoveries need the same actual dock. Other roles lack binding evidence.
    resource = str(assignments[0].resource_id)
    specs = tuple(TaskSpec(str(t.id), str(t.warehouse_id), 1000, 1100,
                           exclusive_resource_ids=(resource,)) for t in tasks)
    role = ExceptionRecoveryRole(tuple(RecoveryDeclaration(s.task_id, resource, 1000, 20) for s in specs))
    coordinator = ContractNet([WarehouseWindowRole(snapshot, tasks, ()),
                              TransportWindowRole(snapshot.vehicles, ()), role],
                             NegotiationPolicy(max_rounds=3))
    result = coordinator.negotiate(specs, 0)
    assert result.status == 'partial' and len(result.awards) == 1
    assert len(result.conflicts) == 3
    assert result.outcome_of(specs[1].task_id) == 'conflicted'
    again = coordinator.negotiate((specs[1],), 0, 'another-call')
    assert not again.awards and again.conflicts
    coordinator.revoke(specs[0].task_id, 180)
    assert coordinator.negotiate((specs[1],), 180, 'after-revoke').status == 'confirmed'


def test_role_does_not_confirm_unknown_or_expired_offer():
    role = ExceptionRecoveryRole((RecoveryDeclaration('task', 'dock', 0, 20),))
    award = Award('award', 'task', 'missing', 'exception', 1, 60)
    assert not role.confirm(award)
    bid = role.bid(CallForProposals('cfp', 1, 0, 60,
                   TaskSpec('task', 'wh', 0, 100, exclusive_resource_ids=('dock',))))
    assert role.confirm(replace(award, bid_id=bid.bid_id))
    assert not role.confirm(replace(award, bid_id=bid.bid_id, awarded_at_s=361))
