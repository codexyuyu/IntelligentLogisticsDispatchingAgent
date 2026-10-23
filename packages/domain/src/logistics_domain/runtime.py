"""Pure runtime records: durable jobs, scenarios and run-level value types (P02-04).

``runtime`` may import ``planning`` and ``execution`` one way only; neither of those modules
may import ``runtime``. Durable-job records are shared by the persistence and worker
boundaries, scenario values carry their own canonical content hash, and the fixture
expectations stay a separate side file so they can never become part of a production input.
"""
from dataclasses import dataclass
from datetime import datetime
from typing import Literal, TypeAlias
from uuid import UUID

from logistics_domain.execution import (
    EventPayload,
    CargoAnomalyPayload,
    DemandDecreasePayload,
    DemandIncreasePayload,
    EquipmentFailurePayload,
    OrderCancellationPayload,
    TrafficDisruptionPayload,
    TransportDelayPayload,
    VehicleFailurePayload,
    WarehouseResourceUnavailablePayload,
    WeatherChangePayload,
)
from logistics_domain.planning import (
    PlanningSnapshot,
    TransportTask,
    WarehouseTask,
    content_hash,
)
from logistics_domain.primitives import ArtifactRef, require_sha256, require_positive_int, require_non_negative_int, require_utc_seconds, require_uuid, HORIZON_MAX_S
from logistics_domain.errors import InvalidInputError
from logistics_domain.states import (
    ActorRole,
    AttemptOutcome,
    ConstraintCode,
    ErrorCode,
    ExpectationMeasure,
    GenerationPolicy,
    JobKind,
    JobStatus,
    JobOptimizationMode,
)


@dataclass(frozen=True, kw_only=True)
class ActorContext:
    """Trusted caller identity constructed by the HTTP boundary, never by request bodies."""

    actor_id: UUID
    role: ActorRole
    scope_id: UUID

    def __post_init__(self):
        require_uuid(self.actor_id, field="ActorContext.actor_id")
        require_uuid(self.scope_id, field="ActorContext.scope_id")
        if not isinstance(self.role, ActorRole):
            raise InvalidInputError("ActorContext.role must be an ActorRole")


@dataclass(frozen=True, kw_only=True)
class RequestRef:
    request_id: UUID
    version: int
    schema_version: Literal["2.0.0"]
    hash: str
    family: JobKind

    def __post_init__(self):
        require_uuid(self.request_id, field="RequestRef.request_id")
        require_positive_int(self.version, field="RequestRef.version")
        if self.schema_version != "2.0.0":
            raise InvalidInputError("invalid schema_version")
        require_sha256(self.hash, field="RequestRef.hash")
        if not isinstance(self.family, JobKind):
            raise InvalidInputError("RequestRef.family must be a JobKind")


@dataclass(frozen=True, kw_only=True)
class OptimizationJobPayload:
    family: Literal["optimization"]
    request_ref: RequestRef
    mode: JobOptimizationMode

    def __post_init__(self):
        if self.family != "optimization":
            raise InvalidInputError("invalid family")
        if self.request_ref.family.value != self.family:
            raise InvalidInputError("request family mismatch")


@dataclass(frozen=True, kw_only=True)
class SimulationJobPayload:
    family: Literal["simulation"]
    request_ref: RequestRef

    def __post_init__(self):
        if self.family != "simulation":
            raise InvalidInputError("invalid family")
        if self.request_ref.family.value != self.family:
            raise InvalidInputError("request family mismatch")


@dataclass(frozen=True, kw_only=True)
class RescheduleJobPayload:
    family: Literal["reschedule"]
    request_ref: RequestRef

    def __post_init__(self):
        if self.family != "reschedule":
            raise InvalidInputError("invalid family")
        if self.request_ref.family.value != self.family:
            raise InvalidInputError("request family mismatch")


@dataclass(frozen=True, kw_only=True)
class ExperimentJobPayload:
    family: Literal["experiment"]
    request_ref: RequestRef

    def __post_init__(self):
        if self.family != "experiment":
            raise InvalidInputError("invalid family")
        if self.request_ref.family.value != self.family:
            raise InvalidInputError("request family mismatch")


@dataclass(frozen=True, kw_only=True)
class MetricJobPayload:
    family: Literal["metric"]
    request_ref: RequestRef

    def __post_init__(self):
        if self.family != "metric":
            raise InvalidInputError("invalid family")
        if self.request_ref.family.value != self.family:
            raise InvalidInputError("request family mismatch")

JobPayload: TypeAlias = OptimizationJobPayload | SimulationJobPayload | RescheduleJobPayload | ExperimentJobPayload | MetricJobPayload


@dataclass(frozen=True, kw_only=True)
class JobCommand:
    schema_version: Literal["2.0.0"]
    kind: JobKind
    payload: JobPayload
    deadline_utc: datetime

    def __post_init__(self):
        if self.schema_version != "2.0.0":
            raise InvalidInputError("invalid schema_version")
        require_utc_seconds(self.deadline_utc, field="deadline_utc")
        if not isinstance(self.kind, JobKind):
            raise InvalidInputError("JobCommand.kind must be a JobKind")
        if self.kind.value != self.payload.family:
            raise InvalidInputError("job kind/payload mismatch")
        if self.payload.request_ref.family != self.kind:
            raise InvalidInputError("job kind/request_ref family mismatch")
        if self.kind == JobKind.OPTIMIZATION:
            if not isinstance(getattr(self.payload, "mode", None), JobOptimizationMode):
                raise InvalidInputError("optimization payload requires an explicit mode")
        elif hasattr(self.payload, "mode"):
            raise InvalidInputError("only optimization payloads carry a mode")


@dataclass(frozen=True, kw_only=True)
class JobResultRef:
    result_id: UUID
    version: int
    schema_version: Literal["2.0.0"]
    hash: str
    family: JobKind

    def __post_init__(self):
        require_uuid(self.result_id, field="JobResultRef.result_id")
        require_positive_int(self.version, field="JobResultRef.version")
        if self.schema_version != "2.0.0":
            raise InvalidInputError("invalid schema_version")
        require_sha256(self.hash, field="JobResultRef.hash")
        if not isinstance(self.family, JobKind):
            raise InvalidInputError("JobResultRef.family must be a JobKind")


@dataclass(frozen=True, kw_only=True)
class JobFailure:
    code: ErrorCode
    safe_message: str
    trace_id: UUID
    retryable: bool
    diagnostic_ref: ArtifactRef | None

    def __post_init__(self):
        if not isinstance(self.code, ErrorCode):
            raise InvalidInputError("JobFailure.code must be an ErrorCode")
        if not isinstance(self.safe_message, str) or not 1 <= len(self.safe_message) <= 256:
            raise InvalidInputError("JobFailure.safe_message must be 1..256 characters")
        require_uuid(self.trace_id, field="JobFailure.trace_id")
        if not isinstance(self.retryable, bool):
            raise InvalidInputError("JobFailure.retryable must be a bool")
        if self.diagnostic_ref is not None and not isinstance(self.diagnostic_ref, ArtifactRef):
            raise InvalidInputError("JobFailure.diagnostic_ref must be an ArtifactRef or None")


@dataclass(frozen=True, kw_only=True)
class Job:
    id: UUID
    created_at: datetime
    updated_at: datetime
    row_version: int
    schema_version: Literal["2.0.0"]
    created_by: UUID
    status: JobStatus
    kind: JobKind
    command: JobCommand
    request_hash: str
    trace_id: UUID
    actor_id: UUID
    scope_id: UUID
    available_at: datetime
    deadline_utc: datetime
    attempt: int
    max_attempts: int
    cancel_requested: bool
    lease_owner: UUID | None
    lease_epoch: int
    lease_expires_at: datetime | None
    started_at: datetime | None
    finished_at: datetime | None
    result_ref: JobResultRef | None
    failure: JobFailure | None

    def __post_init__(self):
        for field in ("id", "created_by", "trace_id", "actor_id", "scope_id"):
            require_uuid(getattr(self, field), field=f"Job.{field}")
        require_utc_seconds(self.created_at, field="created_at")
        require_utc_seconds(self.updated_at, field="updated_at")
        if self.updated_at < self.created_at:
            raise InvalidInputError("Job.updated_at precedes created_at")
        require_non_negative_int(self.row_version, field="row_version")
        if self.schema_version != "2.0.0":
            raise InvalidInputError("invalid schema_version")
        require_sha256(self.request_hash, field="request_hash")
        require_utc_seconds(self.available_at, field="available_at")
        require_utc_seconds(self.deadline_utc, field="deadline_utc")
        require_non_negative_int(self.attempt, field="attempt")
        require_positive_int(self.max_attempts, field="max_attempts")
        require_non_negative_int(self.lease_epoch, field="lease_epoch")
        if self.lease_expires_at is not None:
            require_utc_seconds(self.lease_expires_at, field="lease_expires_at")
        if self.started_at is not None:
            require_utc_seconds(self.started_at, field="started_at")
        if self.finished_at is not None:
            require_utc_seconds(self.finished_at, field="finished_at")
        if not isinstance(self.status, JobStatus) or not isinstance(self.kind, JobKind):
            raise InvalidInputError("Job.status/kind must use the shared enums")
        if self.kind != self.command.kind:
            raise InvalidInputError("job/command kind mismatch")
        if self.deadline_utc != self.command.deadline_utc or self.attempt > self.max_attempts:
            raise InvalidInputError("job deadline or attempt mismatch")
        if self.status == JobStatus.RUNNING and (self.lease_owner is None or self.lease_expires_at is None):
            raise InvalidInputError("running job requires a lease")
        if self.status != JobStatus.RUNNING and (self.lease_owner is not None or self.lease_expires_at is not None):
            raise InvalidInputError("nonrunning job cannot hold a lease")
        if self.status in (JobStatus.COMPLETED, JobStatus.FAILED, JobStatus.CANCELLED) and self.finished_at is None:
            raise InvalidInputError("terminal job requires finished_at")
        if self.status in (JobStatus.QUEUED, JobStatus.RUNNING) and self.finished_at is not None:
            raise InvalidInputError("non-terminal job cannot have finished_at")
        if self.started_at is not None and self.finished_at is not None and self.finished_at < self.started_at:
            raise InvalidInputError("Job.finished_at precedes started_at")
        if self.status == JobStatus.FAILED and (self.failure is None or self.result_ref is not None):
            raise InvalidInputError("failed job requires failure without result")
        if self.status == JobStatus.COMPLETED and (self.result_ref is None or self.failure is not None):
            raise InvalidInputError("completed job requires a result without failure")
        if self.status == JobStatus.CANCELLED and (self.result_ref is not None or self.failure is not None):
            raise InvalidInputError("cancelled job carries neither result nor failure")
        if self.result_ref is not None and self.result_ref.family != self.kind:
            raise InvalidInputError("result family mismatch")


@dataclass(frozen=True, kw_only=True)
class JobAttempt:
    id: UUID
    created_at: datetime
    updated_at: datetime
    row_version: int
    schema_version: Literal["2.0.0"]
    created_by: UUID
    status: Literal["recorded"]
    job_id: UUID
    attempt_no: int
    lease_owner: UUID
    lease_epoch: int
    started_at: datetime
    finished_at: datetime
    outcome: AttemptOutcome
    failure: JobFailure | None
    result_ref: JobResultRef | None

    def __post_init__(self):
        for field in ("id", "created_by", "job_id", "lease_owner"):
            require_uuid(getattr(self, field), field=f"JobAttempt.{field}")
        require_utc_seconds(self.created_at, field="created_at")
        require_utc_seconds(self.updated_at, field="updated_at")
        if self.updated_at != self.created_at:
            raise InvalidInputError("recorded attempt keeps created_at == updated_at")
        require_non_negative_int(self.row_version, field="row_version")
        if self.row_version != 0:
            raise InvalidInputError("recorded attempt starts at row_version 0")
        if self.schema_version != "2.0.0":
            raise InvalidInputError("invalid schema_version")
        if self.status != "recorded":
            raise InvalidInputError("invalid status")
        require_positive_int(self.attempt_no, field="attempt_no")
        require_positive_int(self.lease_epoch, field="lease_epoch")
        require_utc_seconds(self.started_at, field="started_at")
        require_utc_seconds(self.finished_at, field="finished_at")
        if self.finished_at < self.started_at:
            raise InvalidInputError("JobAttempt.finished_at precedes started_at")
        if not isinstance(self.outcome, AttemptOutcome):
            raise InvalidInputError("JobAttempt.outcome must be an AttemptOutcome")
        if self.outcome == AttemptOutcome.COMPLETED:
            if self.result_ref is None or self.failure is not None:
                raise InvalidInputError("completed attempt requires a result and no failure")
        elif self.outcome in (AttemptOutcome.FAILED, AttemptOutcome.LEASE_LOST):
            if self.failure is None or self.result_ref is not None:
                raise InvalidInputError("failed/lease_lost attempt requires a failure and no result")
        elif self.result_ref is not None or self.failure is not None:
            raise InvalidInputError("cancelled attempt carries neither result nor failure")


# --------------------------------------------------------------------- scenarios (P02-04)

_EVENT_PAYLOAD_TYPES = (
    VehicleFailurePayload,
    TransportDelayPayload,
    TrafficDisruptionPayload,
    WeatherChangePayload,
    CargoAnomalyPayload,
    OrderCancellationPayload,
    DemandIncreasePayload,
    DemandDecreasePayload,
    EquipmentFailurePayload,
    WarehouseResourceUnavailablePayload,
)


def _require_safe_text(value: object, *, field: str, maximum: int = 256) -> str:
    if not isinstance(value, str) or not 1 <= len(value) <= maximum or value != value.strip():
        raise InvalidInputError(f"{field} must be 1..{maximum} unpadded characters")
    return value


def _require_version_text(value: object, *, field: str) -> str:
    if not isinstance(value, str):
        raise InvalidInputError(f"{field} must be a string")
    parts = value.split(".")
    if len(parts) != 3 or any(not part.isdecimal() for part in parts):
        raise InvalidInputError(f"{field} must be an exact major.minor.patch version")
    return value


@dataclass(frozen=True, slots=True)
class ScenarioRef:
    """Immutable reference to one scenario family revision and its content hash."""

    scenario_id: UUID
    dataset_version: int
    schema_version: Literal["2.0.0"]
    content_hash: str

    def __post_init__(self) -> None:
        require_uuid(self.scenario_id, field="ScenarioRef.scenario_id")
        require_positive_int(self.dataset_version, field="ScenarioRef.dataset_version")
        if self.schema_version != "2.0.0":
            raise InvalidInputError("ScenarioRef.schema_version must be 2.0.0")
        require_sha256(self.content_hash, field="ScenarioRef.content_hash")


@dataclass(frozen=True, slots=True)
class ScenarioSize:
    """Declared collection sizes; the bundle checks every count against real collections."""

    orders: int
    cargo: int
    vehicles: int
    drivers: int
    warehouses: int
    zones: int
    storage_locations: int
    docks: int
    workers: int
    equipment: int
    transport_tasks: int
    warehouse_tasks: int
    inventory_entries: int
    matrices: int

    def __post_init__(self) -> None:
        for name in ("orders", "cargo", "vehicles", "drivers", "warehouses", "zones",
                     "storage_locations", "docks", "workers", "equipment", "transport_tasks",
                     "warehouse_tasks", "inventory_entries", "matrices"):
            require_non_negative_int(getattr(self, name), field=f"ScenarioSize.{name}")


@dataclass(frozen=True, slots=True)
class ScenarioEventSpec:
    """One typed event in the scenario; the event id is stable inside the dataset version."""

    event_id: UUID
    payload: EventPayload

    def __post_init__(self) -> None:
        require_uuid(self.event_id, field="ScenarioEventSpec.event_id")
        if not isinstance(self.payload, _EVENT_PAYLOAD_TYPES):
            raise InvalidInputError("ScenarioEventSpec.payload must be one of the ten payloads")


@dataclass(frozen=True, slots=True)
class ScenarioSpec:
    """Dataset identity and generation metadata; the only holder of scenario events."""

    id: UUID
    version: int
    schema_version: Literal["2.0.0"]
    generator_version: str
    seed: int
    epoch_utc: datetime
    horizon_s: int
    size: ScenarioSize
    generation_policy: GenerationPolicy
    event_specs: tuple[ScenarioEventSpec, ...]

    def __post_init__(self) -> None:
        require_uuid(self.id, field="ScenarioSpec.id")
        require_positive_int(self.version, field="ScenarioSpec.version")
        if self.schema_version != "2.0.0":
            raise InvalidInputError("ScenarioSpec.schema_version must be 2.0.0")
        _require_version_text(self.generator_version, field="ScenarioSpec.generator_version")
        require_non_negative_int(self.seed, field="ScenarioSpec.seed")
        if self.seed > 2**63 - 1:
            raise InvalidInputError("ScenarioSpec.seed exceeds the int64 seed range")
        require_utc_seconds(self.epoch_utc, field="ScenarioSpec.epoch_utc")
        require_non_negative_int(self.horizon_s, field="ScenarioSpec.horizon_s")
        if not 1 <= self.horizon_s <= HORIZON_MAX_S:
            raise InvalidInputError(f"ScenarioSpec.horizon_s must be 1..{HORIZON_MAX_S}")
        if not isinstance(self.size, ScenarioSize):
            raise InvalidInputError("ScenarioSpec.size must be a ScenarioSize")
        if not isinstance(self.generation_policy, GenerationPolicy):
            raise InvalidInputError("ScenarioSpec.generation_policy must be a GenerationPolicy")
        if not isinstance(self.event_specs, tuple):
            raise InvalidInputError("ScenarioSpec.event_specs must be a tuple")
        seen: set[UUID] = set()
        for index, event in enumerate(self.event_specs):
            if not isinstance(event, ScenarioEventSpec):
                raise InvalidInputError(f"event_specs[{index}] must be a ScenarioEventSpec")
            if event.event_id in seen:
                raise InvalidInputError("ScenarioSpec repeats an event id")
            seen.add(event.event_id)
            if event.payload.effective_at_s > self.horizon_s:
                raise InvalidInputError("scenario event lies outside the declared horizon")


@dataclass(frozen=True, slots=True)
class ScenarioInput:
    """Production planning input: snapshot plus typed task sets, never an expected plan."""

    snapshot: PlanningSnapshot
    transport_tasks: tuple[TransportTask, ...]
    warehouse_tasks: tuple[WarehouseTask, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.snapshot, PlanningSnapshot):
            raise InvalidInputError("ScenarioInput.snapshot must be a PlanningSnapshot")
        order_ids = {order.id for order in self.snapshot.orders}
        cargo_ids = {cargo.id for cargo in self.snapshot.cargo}
        warehouse_ids = {warehouse.id for warehouse in self.snapshot.resources.warehouses}
        for name, expected in (("transport_tasks", TransportTask),
                               ("warehouse_tasks", WarehouseTask)):
            value = getattr(self, name)
            if not isinstance(value, tuple):
                raise InvalidInputError(f"ScenarioInput.{name} must be a tuple")
            for index, task in enumerate(value):
                if not isinstance(task, expected):
                    raise InvalidInputError(f"ScenarioInput.{name}[{index}] must be a {expected.__name__}")
        task_ids = [task.id for task in (*self.transport_tasks, *self.warehouse_tasks)]
        if len(set(task_ids)) != len(task_ids):
            raise InvalidInputError("ScenarioInput repeats a task id")
        for task in self.transport_tasks:
            if task.order_id not in order_ids:
                raise InvalidInputError("transport task references an order outside the snapshot")
            if not set(task.cargo_ids) <= cargo_ids:
                raise InvalidInputError("transport task references cargo outside the snapshot")
        for task in self.warehouse_tasks:
            if task.warehouse_id not in warehouse_ids:
                raise InvalidInputError("warehouse task references a warehouse outside the snapshot")
            if task.order_id is not None and task.order_id not in order_ids:
                raise InvalidInputError("warehouse task references an order outside the snapshot")
        predecessors = {task.id: task.predecessor_ids for task in
                        (*self.transport_tasks, *self.warehouse_tasks)}
        for task_id, links in predecessors.items():
            for link in links:
                if link not in predecessors:
                    raise InvalidInputError("task predecessor is not part of the scenario input")
                if link == task_id:
                    raise InvalidInputError("task predecessor is a self loop")
        state: dict[UUID, int] = {}
        for start in predecessors:
            if state.get(start) == 2:
                continue
            state[start] = 1
            stack = [(start, iter(predecessors[start]))]
            while stack:
                current, links = stack[-1]
                try:
                    link = next(links)
                except StopIteration:
                    state[current] = 2
                    stack.pop()
                    continue
                if state.get(link) == 1:
                    raise InvalidInputError("task predecessor graph contains a cycle")
                if state.get(link) != 2:
                    state[link] = 1
                    stack.append((link, iter(predecessors[link])))


def _scenario_content_hash(scenario_id: UUID, dataset_version: int, spec: ScenarioSpec,
                           input: ScenarioInput) -> str:
    return content_hash({
        "schema_version": "2.0.0",
        "scenario_id": scenario_id,
        "dataset_version": dataset_version,
        "spec": spec,
        "input": input,
        "source": "synthetic",
    })


@dataclass(frozen=True, slots=True)
class ScenarioBundle:
    """Strict scenario bundle; the hash binds spec and input, expectations stay outside."""

    schema_version: Literal["2.0.0"]
    ref: ScenarioRef
    spec: ScenarioSpec
    input: ScenarioInput
    source: Literal["synthetic"]

    def __post_init__(self) -> None:
        if self.schema_version != "2.0.0" or self.source != "synthetic":
            raise InvalidInputError("ScenarioBundle must be a synthetic 2.0.0 bundle")
        if not isinstance(self.ref, ScenarioRef):
            raise InvalidInputError("ScenarioBundle.ref must be a ScenarioRef")
        if not isinstance(self.spec, ScenarioSpec):
            raise InvalidInputError("ScenarioBundle.spec must be a ScenarioSpec")
        if not isinstance(self.input, ScenarioInput):
            raise InvalidInputError("ScenarioBundle.input must be a ScenarioInput")
        if self.ref.scenario_id != self.spec.id or self.ref.dataset_version != self.spec.version:
            raise InvalidInputError("scenario ref id/version must equal the spec id/version")
        if self.ref.schema_version != self.spec.schema_version:
            raise InvalidInputError("scenario ref/spec schema versions differ")
        expected = _scenario_content_hash(self.ref.scenario_id, self.ref.dataset_version,
                                          self.spec, self.input)
        if expected != self.ref.content_hash:
            raise InvalidInputError("ScenarioRef.content_hash does not match the bundle content")
        scope = self.input.snapshot.scope
        if scope.epoch_utc != self.spec.epoch_utc or scope.horizon_s != self.spec.horizon_s:
            raise InvalidInputError("snapshot scope epoch/horizon must equal the scenario spec")
        snapshot = self.input.snapshot
        actual = ScenarioSize(
            orders=len(snapshot.orders), cargo=len(snapshot.cargo),
            vehicles=len(snapshot.vehicles), drivers=len(snapshot.drivers),
            warehouses=len(snapshot.resources.warehouses), zones=len(snapshot.resources.zones),
            storage_locations=len(snapshot.resources.locations),
            docks=len(snapshot.resources.docks), workers=len(snapshot.resources.workers),
            equipment=len(snapshot.resources.equipment),
            transport_tasks=len(self.input.transport_tasks),
            warehouse_tasks=len(self.input.warehouse_tasks),
            inventory_entries=len(snapshot.inventory), matrices=len(snapshot.matrices),
        )
        if actual != self.spec.size:
            raise InvalidInputError("ScenarioSpec.size does not match the actual collections")

    @classmethod
    def create(cls, *, scenario_id: UUID, spec: ScenarioSpec, input: ScenarioInput) -> "ScenarioBundle":
        digest = _scenario_content_hash(scenario_id, spec.version, spec, input)
        ref = ScenarioRef(scenario_id=scenario_id, dataset_version=spec.version,
                          schema_version="2.0.0", content_hash=digest)
        return cls(schema_version="2.0.0", ref=ref, spec=spec, input=input, source="synthetic")


@dataclass(frozen=True, slots=True)
class ExpectedInteger:
    kind: Literal["integer"]
    measure: ExpectationMeasure
    value: int

    def __post_init__(self) -> None:
        if self.kind != "integer":
            raise InvalidInputError("ExpectedInteger.kind must be 'integer'")
        if not isinstance(self.measure, ExpectationMeasure):
            raise InvalidInputError("ExpectedInteger.measure must be an ExpectationMeasure")
        require_non_negative_int(self.value, field="ExpectedInteger.value")


@dataclass(frozen=True, slots=True)
class ExpectedViolation:
    kind: Literal["violation"]
    code: ConstraintCode

    def __post_init__(self) -> None:
        if self.kind != "violation":
            raise InvalidInputError("ExpectedViolation.kind must be 'violation'")
        if not isinstance(self.code, str) or not self.code:
            raise InvalidInputError("ExpectedViolation.code must be a nonempty constraint code")


@dataclass(frozen=True, slots=True)
class ExpectedTaskSet:
    kind: Literal["task_set"]
    task_ids: tuple[UUID, ...]

    def __post_init__(self) -> None:
        if self.kind != "task_set":
            raise InvalidInputError("ExpectedTaskSet.kind must be 'task_set'")
        if not isinstance(self.task_ids, tuple) or not self.task_ids:
            raise InvalidInputError("ExpectedTaskSet.task_ids must be a nonempty tuple")
        seen: set[UUID] = set()
        for index, task_id in enumerate(self.task_ids):
            require_uuid(task_id, field=f"ExpectedTaskSet.task_ids[{index}]")
            if task_id in seen:
                raise InvalidInputError("ExpectedTaskSet.task_ids must be unique")
            seen.add(task_id)


FixtureExpectation: TypeAlias = ExpectedInteger | ExpectedViolation | ExpectedTaskSet


@dataclass(frozen=True, slots=True)
class FixtureExpectations:
    """Test-side expectations; never read by the production scenario loader."""

    schema_version: Literal["2.0.0"]
    scenario_ref: ScenarioRef
    expectations: tuple[FixtureExpectation, ...]

    def __post_init__(self) -> None:
        if self.schema_version != "2.0.0":
            raise InvalidInputError("FixtureExpectations.schema_version must be 2.0.0")
        if not isinstance(self.scenario_ref, ScenarioRef):
            raise InvalidInputError("FixtureExpectations.scenario_ref must be a ScenarioRef")
        if not isinstance(self.expectations, tuple):
            raise InvalidInputError("FixtureExpectations.expectations must be a tuple")
        keys: set[tuple] = set()
        for index, expectation in enumerate(self.expectations):
            if not isinstance(expectation, (ExpectedInteger, ExpectedViolation, ExpectedTaskSet)):
                raise InvalidInputError(f"expectations[{index}] is not a named expectation")
            if isinstance(expectation, ExpectedInteger):
                key = ("integer", expectation.measure.value)
            elif isinstance(expectation, ExpectedViolation):
                key = ("violation", expectation.code)
            else:
                key = ("task_set", tuple(sorted(str(item) for item in expectation.task_ids)))
            if key in keys:
                raise InvalidInputError("FixtureExpectations repeats an expectation key")
            keys.add(key)


@dataclass(frozen=True, kw_only=True)
class RequestMetadata:
    """Controlled metadata registered next to immutable request content."""

    ref: RequestRef
    scope_id: UUID
    owner_actor_id: UUID
    optimization_mode: JobOptimizationMode | None
    media_type: Literal["application/json"]

    def __post_init__(self) -> None:
        if not isinstance(self.ref, RequestRef):
            raise InvalidInputError("RequestMetadata.ref must be a RequestRef")
        require_uuid(self.scope_id, field="RequestMetadata.scope_id")
        require_uuid(self.owner_actor_id, field="RequestMetadata.owner_actor_id")
        if self.ref.family == JobKind.OPTIMIZATION:
            if not isinstance(self.optimization_mode, JobOptimizationMode):
                raise InvalidInputError("optimization metadata requires an explicit mode")
        elif self.optimization_mode is not None:
            raise InvalidInputError("only optimization metadata carries a mode")
        if self.media_type != "application/json":
            raise InvalidInputError("RequestMetadata.media_type must be application/json")


@dataclass(frozen=True, slots=True)
class AgentBudget:
    """Shared bounded budget for one agent run and all of its tool calls."""

    wall_time_ms: int
    max_tool_calls: int
    max_tokens: int
    deadline_utc: datetime

    def __post_init__(self) -> None:
        require_positive_int(self.wall_time_ms, field="AgentBudget.wall_time_ms")
        if self.wall_time_ms > 60000:
            raise InvalidInputError("AgentBudget.wall_time_ms exceeds 60000 ms")
        require_non_negative_int(self.max_tool_calls, field="AgentBudget.max_tool_calls")
        require_non_negative_int(self.max_tokens, field="AgentBudget.max_tokens")
        require_utc_seconds(self.deadline_utc, field="AgentBudget.deadline_utc")


@dataclass(frozen=True, slots=True)
class ExperimentSpec:
    """Paired, equal-budget evaluation definition; results are separate records."""

    scenario_ref: ScenarioRef
    policy_ids: tuple[str, ...]
    paired_seeds: tuple[int, ...]
    equal_budget: bool
    metric_version: str
    stop_policy: str
    environment_fingerprint: str

    def __post_init__(self) -> None:
        if not isinstance(self.scenario_ref, ScenarioRef):
            raise InvalidInputError("ExperimentSpec.scenario_ref must be a ScenarioRef")
        if not isinstance(self.policy_ids, tuple) or not self.policy_ids:
            raise InvalidInputError("ExperimentSpec.policy_ids must be a nonempty tuple")
        for index, policy in enumerate(self.policy_ids):
            _require_safe_text(policy, field=f"policy_ids[{index}]", maximum=128)
        if len(set(self.policy_ids)) != len(self.policy_ids):
            raise InvalidInputError("ExperimentSpec.policy_ids must be unique")
        if not isinstance(self.paired_seeds, tuple) or len(self.paired_seeds) < 10:
            raise InvalidInputError("ExperimentSpec.paired_seeds requires at least 10 repetitions")
        for index, seed in enumerate(self.paired_seeds):
            require_non_negative_int(seed, field=f"paired_seeds[{index}]")
            if seed > 2**63 - 1:
                raise InvalidInputError("ExperimentSpec seed exceeds the int64 seed range")
        if len(set(self.paired_seeds)) != len(self.paired_seeds):
            raise InvalidInputError("ExperimentSpec.paired_seeds must be unique")
        if not isinstance(self.equal_budget, bool):
            raise InvalidInputError("ExperimentSpec.equal_budget must be a bool")
        _require_version_text(self.metric_version, field="ExperimentSpec.metric_version")
        _require_safe_text(self.stop_policy, field="ExperimentSpec.stop_policy", maximum=128)
        _require_safe_text(self.environment_fingerprint,
                           field="ExperimentSpec.environment_fingerprint", maximum=128)
