"""Durable-job, scenario and execution DTOs with exact domain mappings.

The module intentionally reuses the single domain enums and carries the P02-04 scenario and
execution boundary projections, because ``ScenarioEventSpec.payload`` must be a named
discriminated union rather than an arbitrary dict. It never redefines a domain entity.
"""
from datetime import datetime
from typing import Annotated, Literal, TypeAlias, ClassVar
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, StrictInt, model_validator

from logistics_domain import runtime as domain
from logistics_domain import execution as execution
from logistics_domain.errors import InvalidInputError
from logistics_domain.states import (
    ActorRole,
    AttemptOutcome,
    CargoCondition,
    EntityState,
    ErrorCode,
    ExpectationMeasure,
    GenerationPolicy,
    JobKind,
    JobStatus,
    JobOptimizationMode,
    ReturnPolicy,
    WeatherProfile,
)
from logistics_contracts.common import EntityRefDTO, ErrorEnvelope

class Record(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    domain_type: ClassVar[type]

    def to_domain(self):
        return self.domain_type(**{key: _convert(value) for key, value in self.__dict__.items()})

    @model_validator(mode="after")
    def validate_domain(self):
        try:
            self.to_domain()
        except InvalidInputError as exc:
            raise ValueError(str(exc)) from exc
        except TypeError as exc:
            raise ValueError(str(exc)) from exc
        return self


def _convert(value):
    if isinstance(value, Record):
        return value.to_domain()
    if isinstance(value, BaseModel) and hasattr(value, "to_domain"):
        return value.to_domain()
    if isinstance(value, tuple):
        return tuple(_convert(item) for item in value)
    if isinstance(value, list):
        return [_convert(item) for item in value]
    return value

class ActorContext(Record):
    domain_type = domain.ActorContext
    actor_id: UUID
    role: ActorRole
    scope_id: UUID

class RequestRef(Record):
    domain_type = domain.RequestRef
    request_id: UUID
    version: StrictInt
    schema_version: Literal["2.0.0"]
    hash: str
    family: JobKind

class OptimizationJobPayload(Record):
    domain_type = domain.OptimizationJobPayload
    family: Literal["optimization"]
    request_ref: RequestRef
    mode: JobOptimizationMode

class SimulationJobPayload(Record):
    domain_type = domain.SimulationJobPayload
    family: Literal["simulation"]
    request_ref: RequestRef

class RescheduleJobPayload(Record):
    domain_type = domain.RescheduleJobPayload
    family: Literal["reschedule"]
    request_ref: RequestRef

class ExperimentJobPayload(Record):
    domain_type = domain.ExperimentJobPayload
    family: Literal["experiment"]
    request_ref: RequestRef

class MetricJobPayload(Record):
    domain_type = domain.MetricJobPayload
    family: Literal["metric"]
    request_ref: RequestRef

JobPayload: TypeAlias = Annotated[OptimizationJobPayload | SimulationJobPayload | RescheduleJobPayload | ExperimentJobPayload | MetricJobPayload, Field(discriminator="family")]

class JobRequest(Record):
    domain_type = domain.JobCommand
    schema_version: Literal["2.0.0"]
    kind: JobKind
    payload: JobPayload
    deadline_utc: datetime

class JobResultRef(Record):
    domain_type = domain.JobResultRef
    result_id: UUID
    version: StrictInt
    schema_version: Literal["2.0.0"]
    hash: str
    family: JobKind

class JobRef(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    schema_version: Literal["2.0.0"]
    job_id: UUID
    status: JobStatus
    status_url: str
    result_url: str
    trace_id: UUID

class JobView(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    schema_version: Literal["2.0.0"]
    job_id: UUID
    kind: JobKind
    status: JobStatus
    row_version: StrictInt
    created_at: datetime
    started_at: datetime | None
    finished_at: datetime | None
    attempt: StrictInt
    max_attempts: StrictInt
    deadline_utc: datetime
    cancel_requested: bool
    result_ref: JobResultRef | None
    error: ErrorEnvelope | None
    trace_id: UUID

class CancelCommand(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    schema_version: Literal["2.0.0"]
    expected_revision: StrictInt
    reason: str


# ------------------------------------------------------------------ execution values

from logistics_contracts.entities import TimeWindowDTO
from logistics_contracts.planning import (
    InventoryEntryDTO,
    LoadDTO,
    PlanningSnapshotDTO,
    ResourceRevisionDTO,
    TransportTaskDTO,
    WarehouseTaskDTO,
)


class AtNodeLocationDTO(Record):
    domain_type = execution.AtNodeLocation
    kind: Literal["at_node"]
    node_id: UUID


class OnArcLocationDTO(Record):
    domain_type = execution.OnArcLocation
    kind: Literal["on_arc"]
    from_node_id: UUID
    to_node_id: UUID
    departed_at_s: StrictInt
    expected_arrival_s: StrictInt
    progress_numerator: StrictInt
    progress_denominator: StrictInt


ExecutionLocationDTO: TypeAlias = Annotated[
    AtNodeLocationDTO | OnArcLocationDTO, Field(discriminator="kind")]


class ArcRefDTO(Record):
    domain_type = execution.ArcRef
    from_node_id: UUID
    to_node_id: UUID


class RegionRefDTO(Record):
    domain_type = execution.RegionRef
    region_id: UUID
    node_ids: tuple[UUID, ...]


class VehicleFailurePayloadDTO(Record):
    domain_type = execution.VehicleFailurePayload
    kind: Literal["vehicle_failure"]
    entity_ref: EntityRefDTO
    effective_at_s: StrictInt
    reason: str
    vehicle_id: UUID
    location: ExecutionLocationDTO
    unavailable_until_s: StrictInt | None
    cargo_condition: CargoCondition


class RationalDTO(Record):
    domain_type = execution.Rational
    numerator: StrictInt
    denominator: StrictInt


class TransportDelayPayloadDTO(Record):
    domain_type = execution.TransportDelayPayload
    kind: Literal["transport_delay"]
    entity_ref: EntityRefDTO
    effective_at_s: StrictInt
    reason: str
    transport_task_id: UUID
    additional_seconds: StrictInt


class TrafficDisruptionPayloadDTO(Record):
    domain_type = execution.TrafficDisruptionPayload
    kind: Literal["traffic_disruption"]
    entity_ref: EntityRefDTO
    effective_at_s: StrictInt
    reason: str
    arc_refs: tuple[ArcRefDTO, ...]
    closure: bool
    travel_multiplier: RationalDTO | None
    new_matrix_version: StrictInt


class WeatherChangePayloadDTO(Record):
    domain_type = execution.WeatherChangePayload
    kind: Literal["weather_change"]
    entity_ref: EntityRefDTO
    effective_at_s: StrictInt
    reason: str
    region_ref: RegionRefDTO
    profile: WeatherProfile
    travel_multiplier: RationalDTO
    new_matrix_version: StrictInt


class CargoAnomalyPayloadDTO(Record):
    domain_type = execution.CargoAnomalyPayload
    kind: Literal["cargo_anomaly"]
    entity_ref: EntityRefDTO
    effective_at_s: StrictInt
    reason: str
    cargo_id: UUID
    condition: CargoCondition
    quantity_units: StrictInt
    measured_temp_decic: StrictInt | None


class OrderCancellationPayloadDTO(Record):
    domain_type = execution.OrderCancellationPayload
    kind: Literal["order_cancellation"]
    entity_ref: EntityRefDTO
    effective_at_s: StrictInt
    reason: str
    order_id: UUID
    disposition_policy: ReturnPolicy


class DemandIncreasePayloadDTO(Record):
    domain_type = execution.DemandIncreasePayload
    kind: Literal["demand_increase"]
    entity_ref: EntityRefDTO
    effective_at_s: StrictInt
    reason: str
    order_id: UUID
    delta_quantity: StrictInt
    delta_weight_g: StrictInt
    delta_volume_cm3: StrictInt


class DemandDecreasePayloadDTO(Record):
    domain_type = execution.DemandDecreasePayload
    kind: Literal["demand_decrease"]
    entity_ref: EntityRefDTO
    effective_at_s: StrictInt
    reason: str
    order_id: UUID
    delta_quantity: StrictInt
    delta_weight_g: StrictInt
    delta_volume_cm3: StrictInt


class EquipmentFailurePayloadDTO(Record):
    domain_type = execution.EquipmentFailurePayload
    kind: Literal["equipment_failure"]
    entity_ref: EntityRefDTO
    effective_at_s: StrictInt
    reason: str
    equipment_id: UUID
    unavailable_until_s: StrictInt | None
    remaining_capacity_units: StrictInt


class WarehouseResourceUnavailablePayloadDTO(Record):
    domain_type = execution.WarehouseResourceUnavailablePayload
    kind: Literal["warehouse_resource_unavailable"]
    entity_ref: EntityRefDTO
    effective_at_s: StrictInt
    reason: str
    resource_ref: EntityRefDTO
    unavailable_window: TimeWindowDTO
    remaining_capacity_units: StrictInt


EventPayloadDTO: TypeAlias = Annotated[
    VehicleFailurePayloadDTO | TransportDelayPayloadDTO | TrafficDisruptionPayloadDTO
    | WeatherChangePayloadDTO | CargoAnomalyPayloadDTO | OrderCancellationPayloadDTO
    | DemandIncreasePayloadDTO | DemandDecreasePayloadDTO | EquipmentFailurePayloadDTO
    | WarehouseResourceUnavailablePayloadDTO,
    Field(discriminator="kind"),
]


class ExecutionEventDTO(Record):
    domain_type = execution.ExecutionEvent
    event_id: UUID
    kind: execution.EventKind
    occurred_at_s: StrictInt
    payload: EventPayloadDTO


class PendingEventDTO(Record):
    domain_type = execution.PendingEvent
    event_id: UUID
    time_s: StrictInt
    priority: StrictInt
    insertion_seq: StrictInt
    payload: EventPayloadDTO


class RngStateDTO(Record):
    domain_type = execution.RngState
    stream_name: str
    algorithm_version: str
    state: StrictInt
    draw_count: StrictInt


class CargoExecutionDTO(Record):
    domain_type = execution.CargoExecution
    cargo_id: UUID
    location_id: UUID | None
    quantity_units: StrictInt
    condition: CargoCondition
    uncontrolled_exposure_s: StrictInt


class OrderExecutionDTO(Record):
    domain_type = execution.OrderExecution
    order_id: UUID
    status: EntityState
    cargo_ids: tuple[UUID, ...]


class VehicleExecutionDTO(Record):
    domain_type = execution.VehicleExecution
    vehicle_id: UUID
    status: EntityState
    location: ExecutionLocationDTO
    driver_id: UUID | None
    load: LoadDTO


class ResourceUsageDTO(Record):
    domain_type = execution.ResourceUsage
    resource_id: UUID
    used_units: StrictInt
    start_s: StrictInt
    end_s: StrictInt


class WarehouseExecutionDTO(Record):
    domain_type = execution.WarehouseExecution
    warehouse_id: UUID
    status: EntityState
    resource_usage: tuple[ResourceUsageDTO, ...]


class TwinStateDTO(Record):
    domain_type = execution.TwinState
    time_s: StrictInt
    orders: tuple[OrderExecutionDTO, ...]
    vehicles: tuple[VehicleExecutionDTO, ...]
    warehouses: tuple[WarehouseExecutionDTO, ...]
    inventory: tuple[InventoryEntryDTO, ...]
    resource_usage: tuple[ResourceUsageDTO, ...]
    last_event_seq: StrictInt


class ExecutionSnapshotDTO(Record):
    domain_type = execution.ExecutionSnapshot
    id: UUID
    status: Literal["recorded"]
    created_at: datetime
    updated_at: datetime
    row_version: StrictInt
    schema_version: Literal["2.0.0"]
    created_by: UUID
    time_s: StrictInt
    state: TwinStateDTO
    source_version_id: UUID
    revisions: tuple[ResourceRevisionDTO, ...]
    content_hash: str


# ------------------------------------------------------------------- scenario values


class ScenarioRefDTO(Record):
    domain_type = domain.ScenarioRef
    scenario_id: UUID
    dataset_version: StrictInt
    schema_version: Literal["2.0.0"]
    content_hash: str


class ScenarioSizeDTO(Record):
    domain_type = domain.ScenarioSize
    orders: StrictInt
    cargo: StrictInt
    vehicles: StrictInt
    drivers: StrictInt
    warehouses: StrictInt
    zones: StrictInt
    storage_locations: StrictInt
    docks: StrictInt
    workers: StrictInt
    equipment: StrictInt
    transport_tasks: StrictInt
    warehouse_tasks: StrictInt
    inventory_entries: StrictInt
    matrices: StrictInt


class ScenarioEventSpecDTO(Record):
    domain_type = domain.ScenarioEventSpec
    event_id: UUID
    payload: EventPayloadDTO


class ScenarioSpecDTO(Record):
    domain_type = domain.ScenarioSpec
    id: UUID
    version: StrictInt
    schema_version: Literal["2.0.0"]
    generator_version: str
    seed: StrictInt
    epoch_utc: datetime
    horizon_s: StrictInt
    size: ScenarioSizeDTO
    generation_policy: GenerationPolicy
    event_specs: tuple[ScenarioEventSpecDTO, ...]


class ScenarioInputDTO(Record):
    domain_type = domain.ScenarioInput
    snapshot: PlanningSnapshotDTO
    transport_tasks: tuple[TransportTaskDTO, ...]
    warehouse_tasks: tuple[WarehouseTaskDTO, ...]


class ScenarioBundleDTO(Record):
    domain_type = domain.ScenarioBundle
    schema_version: Literal["2.0.0"]
    ref: ScenarioRefDTO
    spec: ScenarioSpecDTO
    input: ScenarioInputDTO
    source: Literal["synthetic"]


class ExpectedIntegerDTO(Record):
    domain_type = domain.ExpectedInteger
    kind: Literal["integer"]
    measure: ExpectationMeasure
    value: StrictInt


class ExpectedViolationDTO(Record):
    domain_type = domain.ExpectedViolation
    kind: Literal["violation"]
    code: str


class ExpectedTaskSetDTO(Record):
    domain_type = domain.ExpectedTaskSet
    kind: Literal["task_set"]
    task_ids: tuple[UUID, ...]


FixtureExpectationDTO: TypeAlias = Annotated[
    ExpectedIntegerDTO | ExpectedViolationDTO | ExpectedTaskSetDTO,
    Field(discriminator="kind"),
]


class FixtureExpectationsDTO(Record):
    domain_type = domain.FixtureExpectations
    schema_version: Literal["2.0.0"]
    scenario_ref: ScenarioRefDTO
    expectations: tuple[FixtureExpectationDTO, ...]


class RequestMetadataDTO(Record):
    domain_type = domain.RequestMetadata
    ref: RequestRef
    scope_id: UUID
    owner_actor_id: UUID
    optimization_mode: JobOptimizationMode | None
    media_type: Literal["application/json"]


class AgentBudgetDTO(Record):
    domain_type = domain.AgentBudget
    wall_time_ms: StrictInt
    max_tool_calls: StrictInt
    max_tokens: StrictInt
    deadline_utc: datetime


class ExperimentSpecDTO(Record):
    domain_type = domain.ExperimentSpec
    scenario_ref: ScenarioRefDTO
    policy_ids: tuple[str, ...]
    paired_seeds: tuple[StrictInt, ...]
    equal_budget: bool
    metric_version: str
    stop_policy: str
    environment_fingerprint: str
