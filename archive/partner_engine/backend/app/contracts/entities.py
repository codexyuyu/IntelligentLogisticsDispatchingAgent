"""SHARED: snapshot entities. Strict quantities; seconds relative to origin_at."""
from typing import Literal
from pydantic import AwareDatetime, StrictStr, model_validator
from app.contracts.common import ContractModel, Id, NonNegativeInt, PositiveInt, TimeWindow, Source
from app.contracts.coldchain import (
    ColdChainSnapshot,
    ResourceAssignment,
    ResourceRequirement,
)
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
    #: R05: maximum allowed cumulative exposure, when the scenario declares one.
    #: None means "not declared", which R05 validation reports as not_checked —
    #: it never means unlimited.
    max_exposure_s: PositiveInt | None = None

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
    #: R05 sequence changeover: policy id and the class the resource starts in.
    #: ``initial_setup_class`` is required for the first task on a resource that
    #: has a setup policy; it is never guessed from the first task.
    setup_policy_id: Id | None = None
    initial_setup_class: StrictStr | None = None

    @model_validator(mode='after')
    def coherent(self):
        if self.setup_policy_id is not None and self.initial_setup_class is None:
            raise ValueError('resource with a setup policy must declare initial_setup_class')
        if self.setup_policy_id is None and self.initial_setup_class is not None:
            raise ValueError('initial_setup_class requires setup_policy_id')
        return self

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
    #: Legacy single-resource binding.  When ``requirements`` is empty it is the
    #: only resource the operation occupies.  When requirements exist it must
    #: equal the assignment of ``primary_requirement_id``.
    resource_id: Id
    operation_kind: StrictStr
    duration_s: PositiveInt
    release_at_s: NonNegativeInt
    deadline_at_s: PositiveInt
    predecessor_ids: tuple[Id, ...] = ()
    status: OperationStatus = 'pending'
    #: R05 multi-resource needs.  Empty means "single resource as before"; it is
    #: never interpreted as "no resources required".
    requirements: tuple[ResourceRequirement, ...] = ()
    primary_requirement_id: Id | None = None
    #: R05 changeover class of this operation's cleanup group.
    setup_class: StrictStr | None = None

    @model_validator(mode='after')
    def coherent(self):
        if self.requirements:
            ids = [req.requirement_id for req in self.requirements]
            if len(set(ids)) != len(ids):
                raise ValueError('requirement ids must be unique per operation')
            if self.primary_requirement_id is None:
                raise ValueError('operation with requirements must declare primary_requirement_id')
            if self.primary_requirement_id not in ids:
                raise ValueError('primary_requirement_id must be one of the requirements')
        elif self.primary_requirement_id is not None:
            raise ValueError('primary_requirement_id requires requirements')
        return self


class ScheduledOperation(ContractModel):
    operation_id: Id
    #: Primary resource (see ``Operation.resource_id``); kept for existing
    #: consumers and always equal to the primary assignment.
    resource_id: Id
    start_s: NonNegativeInt
    end_s: NonNegativeInt
    #: R05 multi-resource assignments, one entry per declared requirement.
    resource_assignments: tuple[ResourceAssignment, ...] = ()
    #: ``setup`` marks an explicit changeover operation rendered for a resource
    #: whose SetupPolicy demands an explicit operation instead of a bare gap.
    scheduled_kind: Literal['task', 'setup'] = 'task'
    setup_for_operation_id: Id | None = None

    @model_validator(mode='after')
    def ordered(self):
        if self.end_s <= self.start_s:
            raise ValueError('operation end must be after start')
        if self.scheduled_kind == 'task' and self.setup_for_operation_id is not None:
            raise ValueError('only setup operations may reference setup_for_operation_id')
        if self.scheduled_kind == 'setup' and self.setup_for_operation_id is None:
            raise ValueError('setup operation must reference the task it prepares')
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
    #: R05 inputs.  ``None`` means the scenario declares no R05 data, so R05
    #: rules must be reported as not_checked rather than silently passing.
    coldchain: ColdChainSnapshot | None = None
