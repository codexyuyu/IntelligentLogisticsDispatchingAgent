"""Real PostgreSQL transaction/readback/CAS tests; requires migrated isolated DB."""
from uuid import UUID, uuid4

import pytest
from sqlalchemy import create_engine, delete
from tests.integration.test_partner_pipeline import synthetic_import

from logistics_backend.application.artifacts import ResultArtifactStore
from logistics_backend.application.integration import IntegrationJobHandler, IntegrationService
from logistics_backend.application.jobs import HandlerRegistry, JobService
from logistics_backend.errors import ServiceError
from logistics_backend.persistence.integration_models import integration_runs, integration_scenarios
from logistics_backend.persistence.jobs import JobRepository
from logistics_backend.persistence.uow import UnitOfWork
from logistics_backend.worker import Worker
from logistics_contracts.integration import IntegrationRun, RevokeInput
from logistics_domain.runtime import ActorContext
from logistics_domain.states import ActorRole, JobKind, JobOptimizationMode

pytestmark = pytest.mark.requires_postgres


def test_import_run_refresh_idempotency_revoke_and_scope_isolation(database_url, tmp_path):
    engine = create_engine(database_url)
    scope = uuid4()
    actor = ActorContext(actor_id=uuid4(), role=ActorRole.OPERATOR, scope_id=scope)
    def factory(**options):
        return UnitOfWork(engine, **options)
    registry = HandlerRegistry()
    result_store = ResultArtifactStore(tmp_path / 'results')
    registry.register(JobKind.OPTIMIZATION, IntegrationJobHandler(result_store), mode=JobOptimizationMode.JOINT)
    job_service = JobService(JobRepository(factory), registry)
    service = IntegrationService(factory, scope, job_service, result_store)
    try:
        command = synthetic_import()
        receipt = service.import_scenario(command, actor)
        assert receipt['status'] == 'checked'
        assert service.import_scenario(command, actor) == receipt
        assert service.list_scenarios(actor)['items'][0]['source_kind'] == 'synthetic'
        request = IntegrationRun(scenario_id=UUID(receipt['scenario_id']), budget_ms=4000)
        pending = service.run(request, actor, 'fixed-key', wait=False)
        assert pending['status'] == 'queued'
        assert service.run(request, actor, 'fixed-key', wait=False) == pending
        Worker(job_service.repository, registry).run_once()
        first = service.get(UUID(pending['run_id']), actor)
        assert first['status'] == 'checked'
        assert service.run(request, actor, 'fixed-key') == first
        fresh_service = IntegrationService(factory, scope, job_service, result_store)
        identity = UUID(first['run_id'])
        assert fresh_service.get(identity, actor) == first
        with pytest.raises(ServiceError):
            service.run(request.model_copy(update={'seed': 3}), actor, 'fixed-key')
        result = first['negotiation']['result']
        revoke = RevokeInput(task_id=UUID(result['awards'][0]['task_id']), now_s=1000, expected_digest=result['digest'])
        after = fresh_service.revoke(identity, revoke, actor)
        assert after['negotiation']['result']['status'] == 'revoked'
        assert after['negotiation']['result']['digest'] != result['digest']
        assert service.get(identity, actor) == after
        with pytest.raises(ServiceError):
            service.revoke(identity, revoke, actor)
        other = ActorContext(actor_id=uuid4(), role=ActorRole.OPERATOR, scope_id=uuid4())
        with pytest.raises(ServiceError):
            IntegrationService(factory, other.scope_id).get(identity, other)
    finally:
        with engine.begin() as connection:
            connection.execute(delete(integration_runs).where(integration_runs.c.scope_id == scope))
            connection.execute(delete(integration_scenarios).where(integration_scenarios.c.scope_id == scope))
        engine.dispose()
