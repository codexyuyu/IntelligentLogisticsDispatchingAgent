from pathlib import Path
from copy import deepcopy
import json
import pytest
from pydantic import ValidationError
from app.contracts.planning import RoutingRequest, RoutingResult
from app.contracts.common import ValidationReport, TimeWindow, SolveMetadata
from app.adapters.routing.ortools_solver import OrToolsRoutingSolver

ROOT = Path(__file__).resolve().parents[2]


def fixture():
    return json.loads((ROOT / 'contracts/examples/routing_request.json').read_text(encoding='utf-8'))


def test_shared_routing_fixture():
    request = RoutingRequest.model_validate(fixture())
    assert len(request.snapshot.orders) == 20
    assert len(request.snapshot.warehouses) == 2
    assert len(request.snapshot.vehicles) == 4


def test_extra_field_rejected_instead_of_silent_alias():
    value = fixture()
    value['snapshot']['vehicles'][0]['truck_id'] = 'veh_wrong'
    with pytest.raises(ValidationError):
        RoutingRequest.model_validate(value)


@pytest.mark.parametrize('bad', ['100', -1, 1.5, True])
def test_quantity_never_silently_coerced(bad):
    value = fixture()
    value['snapshot']['orders'][0]['weight_kg'] = bad
    with pytest.raises(ValidationError):
        RoutingRequest.model_validate(value)


def test_invalid_time_window():
    with pytest.raises(ValidationError):
        TimeWindow(start_s=10, end_s=2)


def test_non_square_matrix_rejected():
    value = fixture()
    value['snapshot']['matrix']['duration_s'][0].pop()
    with pytest.raises(ValidationError):
        RoutingRequest.model_validate(value)


def test_unimplemented_result_is_not_success():
    text = (ROOT / 'contracts/examples/routing_result_not_implemented.json').read_text(encoding='utf-8')
    result = RoutingResult.model_validate_json(text)
    assert result.metadata.status == 'unsupported'
    assert result.metadata.has_solution is False


def test_metadata_rejects_false_feasible():
    with pytest.raises(ValidationError):
        SolveMetadata(status='feasible', raw_status='none', engine='test', engine_version='0',
                      has_solution=False, proof_scope='none', solve_ms=0)


def test_validation_cannot_pass_without_checking_rules():
    with pytest.raises(ValidationError):
        ValidationReport(status='passed', validator_version='0', checked_rule_ids=(), violations=())


def test_b_multi_warehouse_scope_is_rejected_before_solver():
    with pytest.raises(ValueError, match="multi_warehouse_routing_not_supported"):
        OrToolsRoutingSolver().solve(RoutingRequest.model_validate(fixture()))
