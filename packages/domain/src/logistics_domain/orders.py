"""Order-domain types; see CHG-20261023-master-data-types."""

from enum import StrEnum
from dataclasses import dataclass, fields
from datetime import datetime
from typing import ClassVar
from uuid import UUID

from logistics_domain.errors import InvalidInputError
from logistics_domain.primitives import TimeWindow, require_non_negative_int, require_positive_int, require_utc_seconds
from logistics_domain.states import EntityState, LIFECYCLE_TRANSITIONS


class CargoType(StrEnum):
    """Cargo classification shared with prepared datasets; temperature is separate."""

    GENERAL = "GENERAL"
    FROZEN = "FROZEN"
    CHILLED = "CHILLED"


@dataclass(frozen=True, kw_only=True)
class Entity:
    id: UUID
    status: EntityState
    created_at: datetime
    updated_at: datetime
    row_version: int
    schema_version: str
    created_by: UUID
    lifecycle: ClassVar[str]

    def __post_init__(self) -> None:
        if self.schema_version != "2.0.0":
            raise InvalidInputError("schema_version must be 2.0.0")
        require_non_negative_int(self.row_version, field="row_version")
        require_utc_seconds(self.created_at, field="created_at")
        require_utc_seconds(self.updated_at, field="updated_at")
        if self.updated_at < self.created_at:
            raise InvalidInputError("updated_at precedes created_at")
        if not isinstance(self.status, EntityState) or self.status not in LIFECYCLE_TRANSITIONS[self.lifecycle]:
            raise InvalidInputError(f"invalid {self.lifecycle} status")
        # ``source_event_id`` is the foreign system's opaque string identity, not a UUID.
        text_ids = {"source_event_id"}
        for field in fields(self):
            value = getattr(self, field.name)
            if field.name in text_ids:
                continue
            if field.name in ("id", "created_by") or field.name.endswith("_id"):
                if value is not None and not isinstance(value, UUID):
                    raise InvalidInputError(f"{field.name} must be UUID")


@dataclass(frozen=True, kw_only=True)
class Order(Entity):
    lifecycle = "order"
    external_ref: str
    pickup_node_id: UUID
    delivery_node_id: UUID
    cargo_ids: tuple[UUID, ...]
    pickup_window: TimeWindow
    delivery_window: TimeWindow
    service_s: int
    soft_due_at_s: int | None
    must_serve: bool
    priority: int

    def __post_init__(self) -> None:
        super().__post_init__()
        require_non_negative_int(self.service_s, field="service_s")
        require_non_negative_int(self.priority, field="priority")
        if self.soft_due_at_s is not None:
            require_non_negative_int(self.soft_due_at_s, field="soft_due_at_s")
        if not self.cargo_ids or len(set(self.cargo_ids)) != len(self.cargo_ids):
            raise InvalidInputError("order requires unique cargo IDs")

    def validate_cargo(self, cargo: tuple["Cargo", ...]) -> None:
        if set(self.cargo_ids) != {item.id for item in cargo} or len(cargo) != len(self.cargo_ids):
            raise InvalidInputError("order cargo references do not match")
        if any(item.order_id != self.id for item in cargo):
            raise InvalidInputError("cargo belongs to another order")


@dataclass(frozen=True, kw_only=True)
class Cargo(Entity):
    lifecycle = "cargo"
    order_id: UUID
    cargo_type: CargoType
    quantity_units: int
    weight_g: int
    volume_cm3: int
    min_temp_decic: int
    max_temp_decic: int
    max_exposure_s: int
    batch_ref: str

    def __post_init__(self) -> None:
        super().__post_init__()
        for name in ("quantity_units", "weight_g", "volume_cm3"):
            require_positive_int(getattr(self, name), field=name)
        require_non_negative_int(self.max_exposure_s, field="max_exposure_s")
        if not isinstance(self.cargo_type, CargoType) or self.min_temp_decic > self.max_temp_decic:
            raise InvalidInputError("invalid cargo type or temperature interval")
