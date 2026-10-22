"""SHARED: snapshot entities. Strict quantities; seconds relative to origin_at."""
from pydantic import AwareDatetime, StrictStr, model_validator
from app.contracts.common import ContractModel, Id, NonNegativeInt, PositiveInt, TimeWindow, Source
from app.domain.states import TemperatureZone, OperationStatus

class Order(ContractModel):
    order_id: Id
    version: PositiveInt
    warehouse_id: Id
    batch_id: Id
    delivery_node_id: Id
    quantity_units: PositiveInt
    weight_kg: PositiveInt
    volume_l: PositiveInt
    temperature_zone: TemperatureZone
    service_window: TimeWindow
    service_duration_s: PositiveInt
    freshness_deadline_s: PositiveInt
    required: bool = True
    source: Source

class Vehicle(ContractModel):
    vehicle_id: Id
    version: PositiveInt
    warehouse_id: Id
    start_node_id: Id
    end_node_id: Id
    current_node_id: Id
    capacity_weight_kg: PositiveInt
    capacity_volume_l: PositiveInt
    remaining_weight_kg: NonNegativeInt
    remaining_volume_l: NonNegativeInt
    temperature_zone: TemperatureZone
    shift_window: TimeWindow
    available_at_s: NonNegativeInt
    source: Source

class Warehouse(ContractModel):
    warehouse_id: Id
    version: PositiveInt
    node_id: Id
    temperature_zones: tuple[TemperatureZone, ...]

class WarehouseResource(ContractModel):
    resource_id: Id
    warehouse_id: Id
    version: PositiveInt
    resource_kind: StrictStr
    capacity_units: PositiveInt
    available_windows: tuple[TimeWindow, ...]
    unavailable_windows: tuple[TimeWindow, ...] = ()

class StockLot(ContractModel):
    batch_id: Id
    warehouse_id: Id
    version: PositiveInt
    temperature_zone: TemperatureZone
    on_hand_units: NonNegativeInt
    reserved_units: NonNegativeInt
    quarantined_units: NonNegativeInt
    expires_at: AwareDatetime

class Operation(ContractModel):
    operation_id: Id
    order_ids: tuple[Id, ...]
    warehouse_id: Id
    resource_id: Id
    operation_kind: StrictStr
    duration_s: PositiveInt
    release_at_s: NonNegativeInt
    deadline_at_s: PositiveInt
    predecessor_ids: tuple[Id, ...] = ()
    status: OperationStatus = 'pending'

class ScheduledOperation(ContractModel):
    operation_id: Id
    resource_id: Id
    start_s: NonNegativeInt
    end_s: NonNegativeInt

    @model_validator(mode='after')
    def ordered(self):
        if self.end_s <= self.start_s:
            raise ValueError('operation end must be after start')
        return self

class TravelMatrix(ContractModel):
    matrix_id: Id
    version: PositiveInt
    node_ids: tuple[Id, ...]
    duration_s: tuple[tuple[NonNegativeInt | None, ...], ...]
    distance_m: tuple[tuple[NonNegativeInt | None, ...], ...]
    source: Source

    @model_validator(mode='after')
    def square(self):
        n = len(self.node_ids)
        if not n or len(set(self.node_ids)) != n:
            raise ValueError('matrix node_ids must be unique and nonempty')
        for matrix in (self.duration_s, self.distance_m):
            if len(matrix) != n or any(len(row) != n for row in matrix):
                raise ValueError('matrix dimensions must match node_ids')
            if any(matrix[i][i] != 0 for i in range(n)):
                raise ValueError('matrix diagonal must be zero')
        return self

class PlanningSnapshot(ContractModel):
    snapshot_id: Id
    version: PositiveInt
    origin_at: AwareDatetime
    simulation_time_s: NonNegativeInt
    rule_version: StrictStr
    orders: tuple[Order, ...]
    vehicles: tuple[Vehicle, ...]
    warehouses: tuple[Warehouse, ...]
    resources: tuple[WarehouseResource, ...]
    stock_lots: tuple[StockLot, ...]
    operations: tuple[Operation, ...]
    frozen_operations: tuple[ScheduledOperation, ...] = ()
    matrix: TravelMatrix
