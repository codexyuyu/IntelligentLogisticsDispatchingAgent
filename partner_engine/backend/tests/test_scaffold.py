"""Skeleton behavior only; no claim about unfinished business services."""
from fastapi.testclient import TestClient
from app.main import app
from app.contracts.common import CONTRACT_VERSION

client = TestClient(app)


def test_real_health_marks_skeleton():
    result = client.get('/api/v1/health')
    assert result.status_code == 200
    assert result.json() == {'status': 'ok', 'mode': 'skeleton', 'contract_version': CONTRACT_VERSION}


def test_unknown_job_returns_controlled_error():
    result = client.get('/api/v1/jobs/job_demo')
    assert result.status_code == 404
    assert result.json()['code'] == 'not_found'
    assert result.headers['x-trace-id'] == result.json()['trace_id']


def test_validation_errors_use_same_envelope():
    result = client.post('/api/v1/planning-jobs', json={})
    assert result.status_code == 422
    assert set(result.json()) == {'code','message','field_errors','trace_id','retryable'}
    assert result.json()['code'] == 'invalid_input'


def test_idempotency_header_is_required_before_business():
    body = {'snapshot_id':'snap_demo','expected_snapshot_version':1,'order_ids':['ord_demo']}
    assert client.post('/api/v1/planning-jobs', json=body).status_code == 422


def test_unique_operation_ids_and_declared_errors():
    operations = [op for path in app.openapi()['paths'].values() for method, op in path.items() if method in ('get','post')]
    assert len(operations) == 11
    ids = [op['operationId'] for op in operations]
    assert len(ids) == len(set(ids))
    assert all('200' in op['responses'] or '201' in op['responses'] or '202' in op['responses'] or '422' in op['responses'] for op in operations)
