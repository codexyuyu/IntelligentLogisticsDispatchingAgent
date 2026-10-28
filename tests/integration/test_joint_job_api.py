"""Joint HTTP compatibility and async execution through the real worker."""
import threading
from uuid import uuid4

from tests.integration import test_warehouse_job_pipeline as warehouse_helpers
from tests.integration.test_partner_pipeline import synthetic_import

from logistics_backend.worker import Worker
from logistics_domain.planning import TaskKind

warehouse_api = warehouse_helpers.warehouse_api


def test_joint_async_result_and_synchronous_compatibility(warehouse_api):
    client, app, _, _ = warehouse_api
    imported = client.post('/api/v1/integration/scenarios',
        json=synthetic_import().model_dump(mode='json'), headers={})
    assert imported.status_code == 200, imported.text
    request = {'scenario_id': imported.json()['scenario_id'], 'budget_ms': 4000}
    key = str(uuid4())
    pending = client.post('/api/v1/integration/runs?wait=false', json=request,
                          headers={'Idempotency-Key': key})
    assert pending.status_code == 200, pending.text
    receipt = pending.json()
    assert receipt['status'] == 'queued'
    outcome = Worker(app.state.jobs.repository, app.state.jobs.registry).run_once()
    assert str(outcome.job_id) == receipt['job_id']
    result = client.get(f"/api/v1/jobs/{receipt['job_id']}/result")
    assert result.status_code == 200, result.text
    assert result.json()['kind'] == 'joint'
    assert result.json()['value']['status'] == 'checked'
    assert {t['task_kind'] for t in result.json()['value']['candidate']['task_assignments']} == {
        TaskKind.TRANSPORT.value, TaskKind.WAREHOUSE.value}
    replay = client.post('/api/v1/integration/runs', json=request, headers={'Idempotency-Key': key})
    assert replay.status_code == 200 and replay.json()['status'] == 'checked', replay.text
    assert replay.json()['job_id'] == receipt['job_id']
    assert client.get(f"/api/v1/integration/runs/{receipt['run_id']}").json() == replay.json()

    stop = threading.Event()
    worker = Worker(app.state.jobs.repository, app.state.jobs.registry)
    thread = threading.Thread(target=worker.run, args=(stop,))
    thread.start()
    try:
        synchronous = client.post('/api/v1/integration/runs', json=request,
                                  headers={'Idempotency-Key': str(uuid4())})
        assert synchronous.status_code == 200, synchronous.text
        assert synchronous.json()['status'] == 'checked'
        assert synchronous.json()['job_id'] != receipt['job_id']
    finally:
        stop.set()
        thread.join(timeout=10)
        assert not thread.is_alive()
