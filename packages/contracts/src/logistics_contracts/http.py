"""Named HTTP projections from the API contract; no free-form patches."""
from datetime import datetime
from typing import Annotated, Literal, TypeAlias
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field, StrictInt, model_validator
from logistics_domain.states import EntityKind, EntityState
from logistics_domain.orders import CargoType
from logistics_domain.resources import OperationKind, EquipmentKind
from logistics_contracts.entities import (OrderDTO, VehicleDTO, DriverDTO, WarehouseDTO,
    ZoneDTO, StorageLocationDTO, DockDTO, WorkerDTO, EquipmentDTO, CalendarDTO, TimeWindowDTO)

class Body(BaseModel):
    model_config = ConfigDict(extra="forbid")
    schema_version: Literal["2.0.0"]

class Patch(Body):
    @model_validator(mode="after")
    def validate_changes(self):
        selected = self.model_fields_set - {"schema_version"}
        if not selected:
            raise ValueError("at least one mutable field is required")
        nullable = {"soft_due_at_s", "driver_id", "pool_id"}
        if any(getattr(self, key) is None and key not in nullable for key in selected):
            raise ValueError("null is only allowed on nullable fields")
        return self

class PageQuery(BaseModel):
    model_config = ConfigDict(extra="forbid")
    cursor: str | None = Field(default=None, max_length=2048)
    limit: int = Field(default=50, ge=1, le=200)

class PagePosition(BaseModel):
    """Opaque cursor payload; names follow DATA_CONTRACTS PagePosition."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    version: Literal[1]
    scope_id: UUID
    entity_kind: EntityKind
    filter_hash: str = Field(pattern="^[0-9a-f]{64}$")
    after_created_at: datetime
    after_id: UUID

class HealthResponse(Body):
    status: Literal["alive"] = "alive"

class ReadinessResponse(Body):
    status: Literal["ready", "not_ready"]
    database: Literal["available", "unavailable"]
    trace_id: UUID

class CargoCreate(Body):
    schema_version: Literal["2.0.0"] = "2.0.0"
    cargo_type: CargoType
    quantity_units: StrictInt
    weight_g: StrictInt
    volume_cm3: StrictInt
    min_temp_decic: StrictInt
    max_temp_decic: StrictInt
    max_exposure_s: StrictInt
    batch_ref: str

class OrderCreate(Body):
    external_ref: str
    pickup_node_id: UUID
    delivery_node_id: UUID
    pickup_window: TimeWindowDTO
    delivery_window: TimeWindowDTO
    service_s: StrictInt
    soft_due_at_s: StrictInt | None
    must_serve: bool
    priority: StrictInt
    cargo: tuple[CargoCreate, ...]

    @model_validator(mode="after")
    def require_cargo(self):
        if not self.cargo:
            raise ValueError("order requires cargo")
        return self

class OrderUpdate(Patch):
    external_ref: str | None = None
    pickup_node_id: UUID | None = None
    delivery_node_id: UUID | None = None
    pickup_window: TimeWindowDTO | None = None
    delivery_window: TimeWindowDTO | None = None
    service_s: StrictInt | None = None
    soft_due_at_s: StrictInt | None = None
    must_serve: bool | None = None
    priority: StrictInt | None = None

class OrderFilter(PageQuery):
    status: EntityState | None = None
    external_ref: str | None = None

class OrderPage(Body):
    items: tuple[OrderDTO, ...]
    next_cursor: str | None
    has_more: bool

    @model_validator(mode="after")
    def validate_cursor(self):
        if self.has_more != (self.next_cursor is not None):
            raise ValueError("has_more must agree with next_cursor")
        return self

class VehicleCreate(Body):
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

class VehicleUpdate(Patch):
    code: str | None = None
    capacity_weight_g: StrictInt | None = None
    capacity_volume_cm3: StrictInt | None = None
    setpoint_decic: StrictInt | None = None
    allowed_cargo_types: tuple[CargoType, ...] | None = None
    start_node_id: UUID | None = None
    end_node_id: UUID | None = None
    calendar: CalendarDTO | None = None
    driver_id: UUID | None = None
    fixed_cost_cents: StrictInt | None = None
    rate_cents_per_km: StrictInt | None = None

class VehicleFilter(PageQuery):
    status: EntityState | None = None
    code: str | None = None
    driver_id: UUID | None = None

class VehiclePage(Body):
    items: tuple[VehicleDTO, ...]
    next_cursor: str | None
    has_more: bool

    @model_validator(mode="after")
    def validate_cursor(self):
        if self.has_more != (self.next_cursor is not None):
            raise ValueError("has_more must agree with next_cursor")
        return self

class DriverCreate(Body):
    code: str
    qualifications: tuple[str, ...]
    shift: TimeWindowDTO
    max_drive_s: StrictInt
    max_work_s: StrictInt

class DriverUpdate(Patch):
    code: str | None = None
    qualifications: tuple[str, ...] | None = None
    shift: TimeWindowDTO | None = None
    max_drive_s: StrictInt | None = None
    max_work_s: StrictInt | None = None

class DriverQuery(PageQuery):
    status: EntityState | None = None
    code: str | None = None

class DriverPage(Body):
    items: tuple[DriverDTO, ...]
    next_cursor: str | None
    has_more: bool

    @model_validator(mode="after")
    def validate_cursor(self):
        if self.has_more != (self.next_cursor is not None):
            raise ValueError("has_more must agree with next_cursor")
        return self

class WarehouseCreate(Body):
    code: str
    name: str
    node_id: UUID
    timezone: str
    calendar: CalendarDTO

class WarehouseUpdate(Patch):
    code: str | None = None
    name: str | None = None
    node_id: UUID | None = None
    timezone: str | None = None
    calendar: CalendarDTO | None = None

class WarehouseFilter(PageQuery):
    status: EntityState | None = None
    code: str | None = None

class WarehousePage(Body):
    items: tuple[WarehouseDTO, ...]
    next_cursor: str | None
    has_more: bool

    @model_validator(mode="after")
    def validate_cursor(self):
        if self.has_more != (self.next_cursor is not None):
            raise ValueError("has_more must agree with next_cursor")
        return self

class ZoneCreate(Body):
    code: str
    setpoint_decic: StrictInt
    capacity_weight_g: StrictInt
    capacity_volume_cm3: StrictInt
    allowed_cargo_types: tuple[CargoType, ...]

class ZoneUpdate(Patch):
    code: str | None = None
    setpoint_decic: StrictInt | None = None
    capacity_weight_g: StrictInt | None = None
    capacity_volume_cm3: StrictInt | None = None
    allowed_cargo_types: tuple[CargoType, ...] | None = None

class ZoneQuery(PageQuery):
    status: EntityState | None = None
    code: str | None = None

class ZonePage(Body):
    items: tuple[ZoneDTO, ...]
    next_cursor: str | None
    has_more: bool

    @model_validator(mode="after")
    def validate_cursor(self):
        if self.has_more != (self.next_cursor is not None):
            raise ValueError("has_more must agree with next_cursor")
        return self

class LocationCreate(Body):
    zone_id: UUID
    code: str
    capacity_weight_g: StrictInt
    capacity_volume_cm3: StrictInt
    calendar: CalendarDTO

class LocationUpdate(Patch):
    code: str | None = None
    capacity_weight_g: StrictInt | None = None
    capacity_volume_cm3: StrictInt | None = None

class LocationQuery(PageQuery):
    status: EntityState | None = None
    code: str | None = None
    zone_id: UUID | None = None

class LocationPage(Body):
    items: tuple[StorageLocationDTO, ...]
    next_cursor: str | None
    has_more: bool

    @model_validator(mode="after")
    def validate_cursor(self):
        if self.has_more != (self.next_cursor is not None):
            raise ValueError("has_more must agree with next_cursor")
        return self

class DockCreate(Body):
    code: str
    supported_operations: tuple[OperationKind, ...]
    allowed_zone_ids: tuple[UUID, ...]
    calendar: CalendarDTO

class DockUpdate(Patch):
    code: str | None = None
    supported_operations: tuple[OperationKind, ...] | None = None
    allowed_zone_ids: tuple[UUID, ...] | None = None

class DockQuery(PageQuery):
    status: EntityState | None = None
    code: str | None = None

class DockPage(Body):
    items: tuple[DockDTO, ...]
    next_cursor: str | None
    has_more: bool

    @model_validator(mode="after")
    def validate_cursor(self):
        if self.has_more != (self.next_cursor is not None):
            raise ValueError("has_more must agree with next_cursor")
        return self

class WorkerCreate(Body):
    skills: tuple[str, ...]
    allowed_zone_ids: tuple[UUID, ...]
    calendar: CalendarDTO
    pool_id: UUID | None

class WorkerUpdate(Patch):
    skills: tuple[str, ...] | None = None
    allowed_zone_ids: tuple[UUID, ...] | None = None
    pool_id: UUID | None = None

class WorkerQuery(PageQuery):
    status: EntityState | None = None
    pool_id: UUID | None = None

class WorkerPage(Body):
    items: tuple[WorkerDTO, ...]
    next_cursor: str | None
    has_more: bool

    @model_validator(mode="after")
    def validate_cursor(self):
        if self.has_more != (self.next_cursor is not None):
            raise ValueError("has_more must agree with next_cursor")
        return self

class EquipmentCreate(Body):
    kind: EquipmentKind
    quantity_capacity: StrictInt
    allowed_zone_ids: tuple[UUID, ...]
    calendar: CalendarDTO

class EquipmentUpdate(Patch):
    kind: EquipmentKind | None = None
    quantity_capacity: StrictInt | None = None
    allowed_zone_ids: tuple[UUID, ...] | None = None

class EquipmentQuery(PageQuery):
    status: EntityState | None = None
    kind: EquipmentKind | None = None

class EquipmentPage(Body):
    items: tuple[EquipmentDTO, ...]
    next_cursor: str | None
    has_more: bool

    @model_validator(mode="after")
    def validate_cursor(self):
        if self.has_more != (self.next_cursor is not None):
            raise ValueError("has_more must agree with next_cursor")
        return self

class ZoneResourceUpdate(Body):
    kind: Literal["zone"]
    changes: ZoneUpdate

class LocationResourceUpdate(Body):
    kind: Literal["location"]
    changes: LocationUpdate

class DockResourceUpdate(Body):
    kind: Literal["dock"]
    changes: DockUpdate

class WorkerResourceUpdate(Body):
    kind: Literal["worker"]
    changes: WorkerUpdate

class EquipmentResourceUpdate(Body):
    kind: Literal["equipment"]
    changes: EquipmentUpdate

ResourceUpdate: TypeAlias = Annotated[ZoneResourceUpdate | LocationResourceUpdate | DockResourceUpdate | WorkerResourceUpdate | EquipmentResourceUpdate, Field(discriminator="kind")]

class OrderUpdateBranch(Body):
    entity_kind: Literal["order"]
    entity_id: UUID
    changes: OrderUpdate

class OrderMasterView(Body):
    entity_kind: Literal["order"]
    value: OrderDTO

class VehicleUpdateBranch(Body):
    entity_kind: Literal["vehicle"]
    entity_id: UUID
    changes: VehicleUpdate

class VehicleMasterView(Body):
    entity_kind: Literal["vehicle"]
    value: VehicleDTO

class DriverUpdateBranch(Body):
    entity_kind: Literal["driver"]
    entity_id: UUID
    changes: DriverUpdate

class DriverMasterView(Body):
    entity_kind: Literal["driver"]
    value: DriverDTO

class WarehouseUpdateBranch(Body):
    entity_kind: Literal["warehouse"]
    entity_id: UUID
    changes: WarehouseUpdate

class WarehouseMasterView(Body):
    entity_kind: Literal["warehouse"]
    value: WarehouseDTO

class ZoneUpdateBranch(Body):
    entity_kind: Literal["zone"]
    entity_id: UUID
    changes: ZoneUpdate

class ZoneMasterView(Body):
    entity_kind: Literal["zone"]
    value: ZoneDTO

class LocationUpdateBranch(Body):
    entity_kind: Literal["location"]
    entity_id: UUID
    changes: LocationUpdate

class LocationMasterView(Body):
    entity_kind: Literal["location"]
    value: StorageLocationDTO

class DockUpdateBranch(Body):
    entity_kind: Literal["dock"]
    entity_id: UUID
    changes: DockUpdate

class DockMasterView(Body):
    entity_kind: Literal["dock"]
    value: DockDTO

class WorkerUpdateBranch(Body):
    entity_kind: Literal["worker"]
    entity_id: UUID
    changes: WorkerUpdate

class WorkerMasterView(Body):
    entity_kind: Literal["worker"]
    value: WorkerDTO

class EquipmentUpdateBranch(Body):
    entity_kind: Literal["equipment"]
    entity_id: UUID
    changes: EquipmentUpdate

class EquipmentMasterView(Body):
    entity_kind: Literal["equipment"]
    value: EquipmentDTO

MasterDataUpdate: TypeAlias = Annotated[OrderUpdateBranch | VehicleUpdateBranch | DriverUpdateBranch | WarehouseUpdateBranch | ZoneUpdateBranch | LocationUpdateBranch | DockUpdateBranch | WorkerUpdateBranch | EquipmentUpdateBranch, Field(discriminator="entity_kind")]

MasterDataView: TypeAlias = Annotated[OrderMasterView | VehicleMasterView | DriverMasterView | WarehouseMasterView | ZoneMasterView | LocationMasterView | DockMasterView | WorkerMasterView | EquipmentMasterView, Field(discriminator="entity_kind")]
