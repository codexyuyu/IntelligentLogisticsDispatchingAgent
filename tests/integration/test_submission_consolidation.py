"""Real PostgreSQL concurrency and rollback regression checks for submission."""
import hashlib
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from sqlalchemy import create_engine, func, select
from tests.unit.test_new_api_services import _plan

from logistics_backend.application.jobs import HandlerRegistry, JobService
from logistics_backend.application.simulation import SimulationJobHandler, SimulationService
from logistics_backend.errors import ServiceError
from logistics_backend.persistence.jobs import JobRepository
from logistics_backend.persistence.runtime_models import idempotency, jobs, requests
from logistics_backend.persistence.uow import UnitOfWork
from logistics_contracts.mapping import plan_dto, route_stop_dto
from logistics_contracts.runtime import JobRequest, RequestRef, SimulationJobPayload
from logistics_contracts.simulation import SimulationRequestDTO
from logistics_domain.runtime import ActorContext
from logistics_domain.states import ActorRole, JobKind

pytestmark = pytest.mark.requires_postgres


def test_concurrent_retries_share_one_job_and_conflicts_leave_no_orphan_input(database_url):
    engine = create_engine(database_url)
    actor = ActorContext(actor_id=uuid4(), role=ActorRole.OPERATOR, scope_id=uuid4())
    repository = JobRepository(lambda **kw: UnitOfWork(engine, **kw))
    registry = HandlerRegistry()
    registry.register(JobKind.SIMULATION, SimulationJobHandler())
    service = SimulationService(JobService(repository, registry))
    plan, stop = _plan(uuid4())
    request = SimulationRequestDTO(plan=plan_dto(plan), stops=(route_stop_dto(stop),), seed=0, until_s=100)
    try:
        with ThreadPoolExecutor(max_workers=4) as pool:
            receipts = list(pool.map(lambda _: service.submit(request, actor, 'same-request', uuid4()), range(4)))
        assert len({r.job_id for r in receipts}) == 1
        assert all(r == receipts[0] for r in receipts)
        with pytest.raises(ServiceError, match='different request'):
            service.submit(request.model_copy(update={'seed': 1}), actor, 'same-request', uuid4())
        with engine.connect() as connection:
            for table in (requests, jobs, idempotency):
                assert connection.scalar(select(func.count()).select_from(table).where(table.c.scope_id == actor.scope_id)) == 1

        def invalid_deadline():
            content = b'{}'
            ref = RequestRef(request_id=uuid4(), version=1, schema_version='2.0.0',
                hash=hashlib.sha256(content).hexdigest(), family=JobKind.SIMULATION)
            command = JobRequest(schema_version='2.0.0', kind=JobKind.SIMULATION,
                payload=SimulationJobPayload(family='simulation', request_ref=ref),
                deadline_utc=datetime.now(UTC).replace(microsecond=0) - timedelta(seconds=1))
            return command, content

        with pytest.raises(ServiceError, match='deadline'):
            repository.submit_once(actor, 'invalid', uuid4(), 'test-rollback', 'b'*64, invalid_deadline)
        with engine.connect() as connection:
            for table in (requests, jobs, idempotency):
                assert connection.scalar(select(func.count()).select_from(table).where(table.c.scope_id == actor.scope_id)) == 1
    finally:
        # Inputs are append-only. Cancel unclaimed jobs instead of deleting audit history.
        with engine.connect() as connection:
            pending = connection.execute(select(jobs.c.id, jobs.c.row_version).where(
                jobs.c.scope_id == actor.scope_id, jobs.c.status == 'queued')).all()
        for job_id, revision in pending:
            repository.cancel(job_id, revision, actor.scope_id)
        engine.dispose()
