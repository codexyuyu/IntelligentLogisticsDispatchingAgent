"""Regression cases for shared candidates, role confirmation and metric semantics."""
from dataclasses import asdict, replace
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from tests.integration.test_partner_pipeline import synthetic_import
from tests.unit.test_contract_net_roles import WarehouseWindowRole, cfp_for, facts, task
from tests.unit.test_new_api_services import EPOCH, _plan

from logistics_agents.contract_net import Award
from logistics_backend.application.budgets import solver_budget
from logistics_backend.application.candidates import build_candidate
from logistics_backend.application.jobs import Deadline
from logistics_contracts.planning import CandidatePlanDTO
from logistics_domain.errors import InvalidInputError
from logistics_domain.metrics import MetricSource
from logistics_domain.planning import SolveBudget, content_hash
from logistics_evaluation.metrics import compare_metrics, transport_plan_metrics


def test_candidate_cost_is_not_doubled_and_all_stops_contribute():
    plan, pickup = _plan(uuid4())
    delivery = replace(pickup, id=uuid4(), sequence=1, arrival_s=80, service_start_s=80, departure_s=90)
    candidate = build_candidate(schedule_id=uuid4(), snapshot=synthetic_import().snapshot.to_domain(),
        plan=plan, stops=(pickup, delivery), actor_id=uuid4(), now=EPOCH)
    assert candidate.warehouse_plan.cost.total_cents == 0
    assert candidate.objective.business_cost_cents == plan.cost.total_cents == 1800
    assert len(candidate.task_assignments) == 1
    task_value = candidate.task_assignments[0]
    assert (task_value.planned_start_s, task_value.planned_end_s) == (10, 90)
    assert CandidatePlanDTO.model_validate(asdict(candidate)).to_domain() == candidate
    body = {k: v for k, v in asdict(candidate).items() if k not in ('id', 'base_version_id', 'content_hash')}
    assert candidate.content_hash == content_hash(body)
    with pytest.raises(InvalidInputError, match='route'):
        build_candidate(schedule_id=uuid4(), snapshot=synthetic_import().snapshot.to_domain(),
            plan=plan, stops=(replace(pickup, route_id=uuid4()),), actor_id=uuid4(), now=EPOCH)


def test_legacy_role_uses_real_offer_confirmation():
    calendar, operation, _ = facts()
    role = WarehouseWindowRole((operation,), calendar)
    bid = role.bid(cfp_for(task()))
    award = Award('a', bid.task_id, bid.bid_id, bid.role, bid.round_no, 0)
    assert role.confirm(award)
    assert not role.confirm(replace(award, bid_id='invented'))
    assert not role.confirm(replace(award, task_id='other'))
    assert not role.confirm(replace(award, awarded_at_s=bid.expires_at_s + 1))


@pytest.mark.parametrize('change', [
    {'unit': 'km'}, {'source': MetricSource.ACTUAL}, {'definition_version': 'old'},
])
def test_metric_comparison_rejects_incompatible_evidence(change):
    plan, _ = _plan(uuid4())
    metric = transport_plan_metrics(plan, 1, 1)[0]
    with pytest.raises(ValueError, match='INCOMPARABLE_METRICS'):
        compare_metrics('base', 'candidate', (metric,), (replace(metric, **change),))


def test_solver_budget_rejects_expired_deadline():
    with pytest.raises(InvalidInputError, match='expired'):
        solver_budget(Deadline(datetime.now(UTC) - timedelta(seconds=1)))
    budget = solver_budget(Deadline(datetime.now(UTC) + timedelta(seconds=2)))
    assert 0 < budget.wall_time_ms <= 2000


def test_solver_budget_also_honors_the_callers_deadline():
    now = datetime.now(UTC).replace(microsecond=0)
    requested = SolveBudget(5000, now + timedelta(seconds=2), 1, 7, worker_count=1)
    budget = solver_budget(Deadline(now + timedelta(seconds=50)), requested)
    assert budget.deadline_utc == requested.deadline_utc
    assert 0 < budget.wall_time_ms <= 2000
    assert budget.seed == 7
    with pytest.raises(InvalidInputError, match='expired'):
        solver_budget(Deadline(now + timedelta(seconds=50)),
                      replace(requested, deadline_utc=now - timedelta(seconds=1)))
