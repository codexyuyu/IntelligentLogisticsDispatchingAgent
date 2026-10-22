"""B-04 local rescheduling contracts."""
from __future__ import annotations

from pydantic import StrictStr
from app.contracts.common import ContractModel, Id, NonNegativeInt, PositiveInt, ValidationReport
from app.contracts.events import DispatchEvent
from app.contracts.planning import CandidatePlan


class ImpactAnalysis(ContractModel):
    event_id: Id
    affected_order_ids: tuple[Id, ...]
    locked_order_ids: tuple[Id, ...]
    affected_vehicle_ids: tuple[Id, ...]
    affected_route_ids: tuple[Id, ...]
    reason: StrictStr


class PlanDiff(ContractModel):
    changed_order_ids: tuple[Id, ...]
    changed_vehicle_ids: tuple[Id, ...]
    old_distance_m: NonNegativeInt
    new_distance_m: NonNegativeInt
    distance_delta_m: int
    old_route_duration_s: NonNegativeInt
    new_route_duration_s: NonNegativeInt
    route_duration_delta_s: int


class LocalRescheduleResult(ContractModel):
    event: DispatchEvent
    impact: ImpactAnalysis
    previous_plan_id: Id
    previous_plan_version: PositiveInt
    replanned_plan: CandidatePlan
    diff: PlanDiff
    validation: ValidationReport
