"""Exception impact and reschedule-boundary values (P14 subset)."""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from logistics_domain.errors import InvalidInputError
from logistics_domain.execution import AtNodeLocation, ExecutionLocation, OnArcLocation
from logistics_domain.primitives import EntityRef, require_non_negative_int, require_sha256, require_uuid

__all__ = [
    "ImpactReasonPath",
    "ImpactReport",
    "ResidualLoad",
    "RescheduleBoundary",
    "ResourceBlock",
    "VirtualStart",
]


@dataclass(frozen=True, slots=True)
class ImpactReasonPath:
    code: str
    entity_refs: tuple[EntityRef, ...]
    message: str

    def __post_init__(self) -> None:
        if not isinstance(self.code, str) or not self.code:
            raise InvalidInputError("ImpactReasonPath.code must be nonempty")
        if not isinstance(self.entity_refs, tuple):
            raise InvalidInputError("ImpactReasonPath.entity_refs must be a tuple")
        for index, reference in enumerate(self.entity_refs):
            if not isinstance(reference, EntityRef):
                raise InvalidInputError(f"entity_refs[{index}] must be EntityRef")
        if not isinstance(self.message, str) or not 1 <= len(self.message) <= 512:
            raise InvalidInputError("ImpactReasonPath.message must be 1..512 characters")


@dataclass(frozen=True, slots=True)
class ImpactReport:
    event_ids: tuple[UUID, ...]
    affected_orders: tuple[UUID, ...]
    affected_tasks: tuple[UUID, ...]
    affected_resources: tuple[UUID, ...]
    reason_paths: tuple[ImpactReasonPath, ...]

    def __post_init__(self) -> None:
        for name in ("event_ids", "affected_orders", "affected_tasks", "affected_resources"):
            value = getattr(self, name)
            if not isinstance(value, tuple) or len(set(value)) != len(value):
                raise InvalidInputError(f"ImpactReport.{name} must be a unique tuple")
        if not isinstance(self.reason_paths, tuple):
            raise InvalidInputError("ImpactReport.reason_paths must be a tuple")


@dataclass(frozen=True, slots=True)
class VirtualStart:
    task_id: UUID
    location: ExecutionLocation
    start_s: int

    def __post_init__(self) -> None:
        require_uuid(self.task_id, field="VirtualStart.task_id")
        if not isinstance(self.location, (AtNodeLocation, OnArcLocation)):
            raise InvalidInputError("VirtualStart.location must be an ExecutionLocation")
        require_non_negative_int(self.start_s, field="VirtualStart.start_s")


@dataclass(frozen=True, slots=True)
class ResidualLoad:
    cargo_id: UUID
    weight_g: int
    volume_cm3: int

    def __post_init__(self) -> None:
        require_uuid(self.cargo_id, field="ResidualLoad.cargo_id")
        require_non_negative_int(self.weight_g, field="ResidualLoad.weight_g")
        require_non_negative_int(self.volume_cm3, field="ResidualLoad.volume_cm3")


@dataclass(frozen=True, slots=True)
class ResourceBlock:
    resource_id: UUID
    start_s: int
    end_s: int

    def __post_init__(self) -> None:
        require_uuid(self.resource_id, field="ResourceBlock.resource_id")
        require_non_negative_int(self.start_s, field="ResourceBlock.start_s")
        require_non_negative_int(self.end_s, field="ResourceBlock.end_s")
        if self.start_s >= self.end_s:
            raise InvalidInputError("ResourceBlock requires start_s < end_s")


@dataclass(frozen=True, slots=True)
class RescheduleBoundary:
    event_time_s: int
    frozen_task_ids: tuple[UUID, ...]
    interrupted_task_ids: tuple[UUID, ...]
    virtual_starts: tuple[VirtualStart, ...]
    residual_loads: tuple[ResidualLoad, ...]
    resource_blocks: tuple[ResourceBlock, ...]
    mutable_task_ids: tuple[UUID, ...]
    immutable_hash: str

    def __post_init__(self) -> None:
        require_non_negative_int(self.event_time_s, field="RescheduleBoundary.event_time_s")
        for name in ("frozen_task_ids", "interrupted_task_ids", "mutable_task_ids"):
            value = getattr(self, name)
            if not isinstance(value, tuple) or len(set(value)) != len(value):
                raise InvalidInputError(f"RescheduleBoundary.{name} must be a unique tuple")
        for name, expected in (("virtual_starts", VirtualStart),
                               ("residual_loads", ResidualLoad),
                               ("resource_blocks", ResourceBlock)):
            value = getattr(self, name)
            if not isinstance(value, tuple):
                raise InvalidInputError(f"RescheduleBoundary.{name} must be a tuple")
            for index, item in enumerate(value):
                if not isinstance(item, expected):
                    raise InvalidInputError(f"{name}[{index}] must be {expected.__name__}")
        require_sha256(self.immutable_hash, field="RescheduleBoundary.immutable_hash")
