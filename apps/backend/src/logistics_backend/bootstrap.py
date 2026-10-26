"""Only composition root: configuration, database adapters and application services."""
import asyncio
import ipaddress
import os
from contextlib import asynccontextmanager
from dataclasses import dataclass
from uuid import UUID, uuid4

from fastapi import FastAPI, Request
from pydantic import BaseModel, ConfigDict, Field, SecretStr, model_validator
from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError
from starlette.concurrency import run_in_threadpool

from logistics_domain.states import (
    ActorRole,
    ErrorCode,
    JobKind,
    JobOptimizationMode,
    RuntimeMode,
)
from logistics_contracts.http import HealthResponse, ReadinessResponse
from logistics_backend.persistence.resource_models import TABLES
from logistics_backend.persistence.uow import UnitOfWork
from logistics_backend.persistence.jobs import JobRepository
from logistics_backend.persistence.snapshots import PlanningSnapshotStore
from logistics_backend.persistence.version_store import PlanCommitStore
from logistics_backend.application.master_data import MasterDataService
from logistics_backend.application.jobs import HandlerRegistry, JobService
from logistics_backend.application.optimization import (
    TransportJobHandler,
    TransportOptimizationService,
    TransportResultStore,
)
from logistics_backend.application.warehouse import (
    WarehouseJobHandler,
    WarehouseOptimizationService,
    WarehouseResultStore,
)
from logistics_backend.application.events import EventService
from logistics_backend.application.exceptions import ExceptionService
from logistics_backend.application.simulation import (
    SimulationJobHandler,
    SimulationResultStore,
    SimulationService,
)
from logistics_agents.llm import DeepSeekProvider, LLMSettings
from logistics_agents.service import AgentChatService
from logistics_backend.application.agent import AgentRunService
from logistics_backend.application.tools import ToolService
from logistics_backend.application.decision import DecisionService
from logistics_backend.application.experiment import ExperimentService
from logistics_backend.application.metrics import MetricsService
from logistics_backend.application.schedule import ScheduleService
from logistics_backend.application.integration import IntegrationService
from logistics_backend.api.errors import install_handlers, response

SecretValue = SecretStr

class CredentialGrant(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    actor_id: UUID
    role: ActorRole
    token_sha256: str = Field(pattern="^[0-9a-f]{64}$", repr=False)

class Settings(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    mode: RuntimeMode
    database_url: SecretValue
    scope_id: UUID
    credentials: tuple[CredentialGrant, ...]
    bind_host: str = "127.0.0.1"
    bind_port: int = Field(default=8000, ge=1, le=65535)
    max_body_bytes: int = Field(default=2097152, ge=1, le=2097152)
    request_timeout_s: int = Field(default=10, ge=1, le=10)

    @model_validator(mode="after")
    def valid_configuration(self):
        if not self.database_url.get_secret_value().startswith("postgresql+psycopg://"):
            raise ValueError("database_url must use postgresql+psycopg")
        if self.mode in (RuntimeMode.DEVELOPMENT, RuntimeMode.TEST):
            if self.bind_host != "localhost" and not ipaddress.ip_address(self.bind_host).is_loopback:
                raise ValueError("development/test binding must be loopback")
        hashes = [c.token_sha256 for c in self.credentials]
        if not hashes or len(set(hashes)) != len(hashes):
            raise ValueError("explicit unique credentials required")
        return self

    @classmethod
    def from_env(cls):
        return cls.model_validate_json(os.environ["LOGISTICS_SETTINGS_JSON"])


@dataclass(frozen=True)
class Services:
    master_data: MasterDataService
    jobs: JobService
    snapshots: PlanningSnapshotStore
    commits: PlanCommitStore
    transport: TransportOptimizationService
    results: TransportResultStore
    warehouse: WarehouseOptimizationService
    warehouse_results: WarehouseResultStore
    events: EventService
    exceptions: ExceptionService
    simulations: SimulationService
    simulation_results: SimulationResultStore
    agents: AgentRunService
    tools: ToolService
    decisions: DecisionService
    experiments: ExperimentService
    metrics: MetricsService
    schedules: ScheduleService
    integration: IntegrationService


def compose(settings: Settings, registry: HandlerRegistry | None = None) -> tuple[object, Services]:
    engine = create_engine(settings.database_url.get_secret_value(), pool_pre_ping=True,
        connect_args={"connect_timeout": 3, "options": "-c statement_timeout=9000"})
    factory = lambda **options: UnitOfWork(engine, **options)
    repository = JobRepository(factory)
    if registry is None:
        registry = HandlerRegistry()
        registry.register(JobKind.OPTIMIZATION, TransportJobHandler(),
                          mode=JobOptimizationMode.TRANSPORT)
        registry.register(JobKind.OPTIMIZATION, WarehouseJobHandler(),
                          mode=JobOptimizationMode.WAREHOUSE)
        registry.register(JobKind.SIMULATION, SimulationJobHandler())
    jobs = JobService(repository, registry)
    snapshots = PlanningSnapshotStore(factory, settings.scope_id)
    commits = PlanCommitStore(factory, settings.scope_id)
    agents = AgentRunService(factory,
        AgentChatService(DeepSeekProvider(LLMSettings.from_env())), settings.scope_id)
    services = Services(
        master_data=MasterDataService(factory, TABLES),
        jobs=jobs,
        snapshots=snapshots,
        commits=commits,
        transport=TransportOptimizationService(snapshots, jobs),
        results=TransportResultStore(),
        warehouse=WarehouseOptimizationService(snapshots, jobs),
        warehouse_results=WarehouseResultStore(),
        events=EventService(factory, settings.scope_id),
        exceptions=ExceptionService(factory, settings.scope_id),
        simulations=SimulationService(jobs),
        simulation_results=SimulationResultStore(),
        agents=agents,
        tools=ToolService(jobs, agents, factory, settings.scope_id),
        decisions=DecisionService(factory, settings.scope_id),
        experiments=ExperimentService(factory, settings.scope_id),
        metrics=MetricsService(factory, settings.scope_id),
        schedules=ScheduleService(factory, settings.scope_id, snapshots, commits, jobs),
        integration=IntegrationService(factory, settings.scope_id),
    )
    return engine, services


def create_app(settings: Settings | None = None, registry: HandlerRegistry | None = None) -> FastAPI:
    settings = settings if settings is not None else Settings.from_env()
    engine, services = compose(settings, registry)

    @asynccontextmanager
    async def lifespan(app):
        yield
        engine.dispose()

    app = schema_app(lifespan=lifespan)
    app.state.engine = engine
    app.state.settings = settings
    app.state.master_data = services.master_data
    app.state.jobs = services.jobs
    app.state.snapshots = services.snapshots
    app.state.commits = services.commits
    app.state.transport = services.transport
    app.state.results = services.results
    app.state.warehouse = services.warehouse
    app.state.warehouse_results = services.warehouse_results
    app.state.events = services.events
    app.state.exceptions = services.exceptions
    app.state.simulations = services.simulations
    app.state.simulation_results = services.simulation_results
    app.state.agents = services.agents
    app.state.tools = services.tools
    app.state.decisions = services.decisions
    app.state.experiments = services.experiments
    app.state.metrics = services.metrics
    app.state.schedules = services.schedules
    app.state.integration = services.integration
    install_handlers(app)

    @app.middleware("http")
    async def request_boundary(request: Request, call_next):
        try:
            request.state.trace_id = UUID(request.headers.get("X-Request-ID", ""))
        except ValueError:
            request.state.trace_id = uuid4()
        # Count streamed bytes as well as declared length before invoking a write operation.
        chunks, total = [], 0
        async for chunk in request.stream():
            total += len(chunk)
            if total > settings.max_body_bytes:
                return response(request, ErrorCode.REQUEST_TOO_LARGE, "request exceeds body limit")
            chunks.append(chunk)
        request._body = b"".join(chunks)
        try:
            result = await asyncio.wait_for(call_next(request), settings.request_timeout_s)
        except TimeoutError:
            return response(request, ErrorCode.DEPENDENCY_UNAVAILABLE, "request deadline exceeded")
        result.headers["X-Request-ID"] = str(request.state.trace_id)
        return result

    return app


def schema_app(lifespan=None) -> FastAPI:
    """Register actual routes without opening connections; used by schema export."""
    app = FastAPI(title="Logistics Dispatching API", version="2.0.0", lifespan=lifespan)
    @app.get("/api/v1/health", response_model=HealthResponse, operation_id="health")
    def health():
        return HealthResponse(schema_version="2.0.0")

    def probe(engine):
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))

    @app.get("/api/v1/ready", response_model=ReadinessResponse, operation_id="ready")
    async def ready(request: Request):
        from fastapi.responses import JSONResponse
        available = True
        try:
            await asyncio.wait_for(run_in_threadpool(probe, request.app.state.engine), 4)
        except (SQLAlchemyError, TimeoutError):
            available = False
        body = ReadinessResponse(schema_version="2.0.0", status="ready" if available else "not_ready",
            database="available" if available else "unavailable", trace_id=request.state.trace_id)
        return JSONResponse(body.model_dump(mode="json"), status_code=200 if available else 503)

    from logistics_backend.api.router import router
    app.include_router(router, prefix="/api/v1")
    return app
