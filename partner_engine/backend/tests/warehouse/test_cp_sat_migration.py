import json
from pathlib import Path

from app.adapters.warehouse.validator import WarehouseScheduleValidator
from app.contracts.planning import WarehouseScheduleRequest, WarehouseScheduleResult
from app.contracts.common import SolveMetadata
from app.contracts.planning import WarehouseHandoff
from app.contracts.entities import ScheduledOperation

ROOT = Path(__file__).resolve().parents[3]
SCENARIO = ROOT / 'data/scenarios/two_warehouses_20_orders.json'


def request_fixture() -> WarehouseScheduleRequest:
    raw = json.loads(SCENARIO.read_text(encoding='utf-8'))
    from app.contracts.entities import PlanningSnapshot
    snapshot = PlanningSnapshot.model_validate(raw)
    return WarehouseScheduleRequest(
        snapshot=snapshot,
        order_ids=tuple(o.order_id for o in snapshot.orders),
        vehicle_arrivals=(),
        budget={'remaining_ms': 1000, 'max_workers': 1, 'random_seed': 17},
    )


def result_fixture(request: WarehouseScheduleRequest) -> WarehouseScheduleResult:
    ops = []
    for op in request.snapshot.operations:
        start = op.release_at_s
        ops.append(ScheduledOperation(
            operation_id=op.operation_id,
            resource_id=op.resource_id,
            start_s=start,
            end_s=start + op.duration_s,
        ))
    return WarehouseScheduleResult(
        snapshot_id=request.snapshot.snapshot_id,
        snapshot_version=request.snapshot.version,
        metadata=SolveMetadata(
            status='feasible',
            raw_status='TEST',
            engine='test',
            engine_version='0',
            has_solution=True,
            proof_scope='test',
            solve_ms=0,
        ),
        operations=tuple(ops),
        warehouse_handoffs=(),
    )


def test_validator_detects_resource_overlap():
    request = request_fixture()
    result = result_fixture(request)
    report = WarehouseScheduleValidator().validate(request, result)
    assert report.status == 'failed'
    assert any(v.rule_id == 'warehouse.resource_non_overlap' for v in report.violations)
