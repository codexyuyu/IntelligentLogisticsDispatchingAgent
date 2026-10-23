"""Boundary mappings for master data (business contract 2.0.0)."""

from datetime import datetime
from typing import Annotated, ClassVar, Literal, TypeAlias
from uuid import UUID
from dataclasses import asdict

from pydantic import Field, StrictInt
from logistics_domain import orders, resources
from logistics_domain.states import EntityState
from logistics_domain.orders import CargoType
from logistics_domain.resources import OperationKind, EquipmentKind
from logistics_domain.primitives import TimeWindow

from pydantic import BaseModel, ConfigDict, model_validator

from logistics_domain.errors import InvalidInputError
from logistics_domain.primitives import CalendarInterval, ResourceCalendar


class CalendarIntervalDTO(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    start_s: StrictInt
    end_s: StrictInt
    available_units: StrictInt

    @model_validator(mode="after")
    def validate_domain(self) -> "CalendarIntervalDTO":
        try:
            self.to_domain()
        except InvalidInputError as exc:
            raise ValueError(str(exc)) from exc
        return self

    def to_domain(self) -> CalendarInterval:
        return CalendarInterval(self.start_s, self.end_s, self.available_units)

    @classmethod
    def from_domain(cls, value: CalendarInterval) -> "CalendarIntervalDTO":
        return cls(start_s=value.start_s, end_s=value.end_s,
                   available_units=value.available_units)


class CalendarDTO(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal["2.0.0"]
    epoch_utc: datetime
    version: StrictInt
    intervals: tuple[CalendarIntervalDTO, ...]

    @model_validator(mode="after")
    def validate_domain(self) -> "CalendarDTO":
        try:
            self.to_domain()
        except InvalidInputError as exc:
            raise ValueError(str(exc)) from exc
        return self

    def to_domain(self) -> ResourceCalendar:
        return ResourceCalendar(
            epoch_utc=self.epoch_utc,
            version=self.version,
            intervals=tuple(item.to_domain() for item in self.intervals),
        )

    @classmethod
    def from_domain(cls, value: ResourceCalendar) -> "CalendarDTO":
        return cls(
            schema_version="2.0.0", epoch_utc=value.epoch_utc,
            version=value.version,
            intervals=tuple(CalendarIntervalDTO.from_domain(item)
                            for item in value.intervals),
        )


class TimeWindowDTO(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    earliest_s: StrictInt
    latest_s: StrictInt

    @model_validator(mode="after")
    def validate_window(self):
        try:
            self.to_domain()
        except InvalidInputError as exc:
            raise ValueError(str(exc)) from exc
        return self

    def to_domain(self) -> TimeWindow:
        return TimeWindow(self.earliest_s, self.latest_s)


class EntityDTO(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, from_attributes=True)
    domain_type: ClassVar[type]
    id: UUID
    status: EntityState
    created_at: datetime
    updated_at: datetime
    row_version: StrictInt
    schema_version: Literal["2.0.0"]
    created_by: UUID

    @model_validator(mode="after")
    def validate_domain(self):
        try:
            self.to_domain()
        except InvalidInputError as exc:
            raise ValueError(str(exc)) from exc
        return self

    def to_domain(self):
        values = {name: getattr(self, name) for name in type(self).model_fields}
        for name, value in tuple(values.items()):
            if isinstance(value, (CalendarDTO, TimeWindowDTO)):
                values[name] = value.to_domain()
        if "skills" in values:
            values["skills"] = tuple(resources.Skill(v) for v in values["skills"])
        if "qualifications" in values:
            values["qualifications"] = tuple(resources.Qualification(v) for v in values["qualifications"])
        return self.domain_type(**values)

    @classmethod
    def from_domain(cls, value):
        values = asdict(value)
        if "calendar" in values:
            values["calendar"] = CalendarDTO.from_domain(value.calendar)
        return cls.model_validate(values)


class OrderDTO(EntityDTO):
    domain_type = orders.Order
    external_ref: str
    pickup_node_id: UUID
    delivery_node_id: UUID
    cargo_ids: tuple[UUID, ...]
    pickup_window: TimeWindowDTO
    delivery_window: TimeWindowDTO
    service_s: StrictInt
    soft_due_at_s: StrictInt | None
    must_serve: bool
    priority: StrictInt


class CargoDTO(EntityDTO):
    domain_type = orders.Cargo
    order_id: UUID
    cargo_type: CargoType
    quantity_units: StrictInt
    weight_g: StrictInt
    volume_cm3: StrictInt
    min_temp_decic: StrictInt
    max_temp_decic: StrictInt
    max_exposure_s: StrictInt
    batch_ref: str


class VehicleDTO(EntityDTO):
    domain_type = resources.Vehicle
    code: str
    capacity_weight_g: StrictInt
    capacity_volume_cm3: StrictInt
    setpoint_decic: StrictInt
    allowed_cargo_types: tuple[CargoType, ...]
    start_node_id: UUID
    end_node_id: UUID
    calendar: CalendarDTO
    driver_id: UUID | None
    fixed_cost_cents: StrictInt
    rate_cents_per_km: StrictInt


class DriverDTO(EntityDTO):
    domain_type = resources.Driver
    code: str
    qualifications: tuple[str, ...]
    shift: TimeWindowDTO
    max_drive_s: StrictInt
    max_work_s: StrictInt


class WarehouseDTO(EntityDTO):
    domain_type = resources.Warehouse
    code: str
    name: str
    node_id: UUID
    timezone: str
    calendar: CalendarDTO


class ZoneDTO(EntityDTO):
    domain_type = resources.WarehouseZone
    warehouse_id: UUID
    code: str
    setpoint_decic: StrictInt
    capacity_weight_g: StrictInt
    capacity_volume_cm3: StrictInt
    allowed_cargo_types: tuple[CargoType, ...]


class StorageLocationDTO(EntityDTO):
    domain_type = resources.StorageLocation
    zone_id: UUID
    code: str
    capacity_weight_g: StrictInt
    capacity_volume_cm3: StrictInt
    calendar: CalendarDTO


class DockDTO(EntityDTO):
    domain_type = resources.Dock
    warehouse_id: UUID
    code: str
    supported_operations: tuple[OperationKind, ...]
    allowed_zone_ids: tuple[UUID, ...]
    calendar: CalendarDTO


class WorkerDTO(EntityDTO):
    domain_type = resources.Worker
    warehouse_id: UUID
    skills: tuple[str, ...]
    allowed_zone_ids: tuple[UUID, ...]
    calendar: CalendarDTO
    pool_id: UUID | None


class EquipmentDTO(EntityDTO):
    domain_type = resources.Equipment
    warehouse_id: UUID
    kind: EquipmentKind
    quantity_capacity: StrictInt
    allowed_zone_ids: tuple[UUID, ...]
    calendar: CalendarDTO


class ZoneResourceDTO(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    kind: Literal["zone"]
    value: ZoneDTO

    def to_domain(self) -> resources.ZoneResource:
        return resources.ZoneResource(self.kind, self.value.to_domain())


class LocationResourceDTO(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    kind: Literal["location"]
    value: StorageLocationDTO

    def to_domain(self) -> resources.LocationResource:
        return resources.LocationResource(self.kind, self.value.to_domain())


class DockResourceDTO(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    kind: Literal["dock"]
    value: DockDTO

    def to_domain(self) -> resources.DockResource:
        return resources.DockResource(self.kind, self.value.to_domain())


class WorkerResourceDTO(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    kind: Literal["worker"]
    value: WorkerDTO

    def to_domain(self) -> resources.WorkerResource:
        return resources.WorkerResource(self.kind, self.value.to_domain())


class EquipmentResourceDTO(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    kind: Literal["equipment"]
    value: EquipmentDTO

    def to_domain(self) -> resources.EquipmentResource:
        return resources.EquipmentResource(self.kind, self.value.to_domain())


ResourceDTO: TypeAlias = Annotated[ZoneResourceDTO | LocationResourceDTO | DockResourceDTO | WorkerResourceDTO | EquipmentResourceDTO, Field(discriminator="kind")]
