"""Paired metric comparison values (P33-01 subset)."""

from __future__ import annotations

import math
from dataclasses import dataclass

from logistics_domain.errors import InvalidInputError
from logistics_domain.metrics import MissingReason
from logistics_domain.orders import Entity
from logistics_domain.primitives import require_int, require_non_negative_int

__all__ = ["ExperimentComparison", "ExperimentRecord", "MetricDelta"]


@dataclass(frozen=True, slots=True)
class MetricDelta:
    code: str
    base: float | None
    candidate: float | None
    delta: float | None
    relative_change: float | None
    reason: MissingReason | None

    def __post_init__(self) -> None:
        if not isinstance(self.code, str) or not self.code:
            raise InvalidInputError("MetricDelta.code must be nonempty")
        for name in ("base", "candidate", "delta", "relative_change"):
            value = getattr(self, name)
            if value is not None:
                if not isinstance(value, (int, float)) or isinstance(value, bool):
                    raise InvalidInputError(f"MetricDelta.{name} must be numeric")
                if not math.isfinite(float(value)):
                    raise InvalidInputError(f"MetricDelta.{name} must be finite")
        if self.reason is not None and not isinstance(self.reason, MissingReason):
            raise InvalidInputError("MetricDelta.reason must be MissingReason")
        if self.delta is None and self.reason is None:
            raise InvalidInputError("a missing delta requires a reason")


@dataclass(frozen=True, slots=True)
class ExperimentComparison:
    base_label: str
    candidate_label: str
    deltas: tuple[MetricDelta, ...]

    def __post_init__(self) -> None:
        for name in ("base_label", "candidate_label"):
            value = getattr(self, name)
            if not isinstance(value, str) or not 1 <= len(value) <= 128:
                raise InvalidInputError(f"ExperimentComparison.{name} must be 1..128 characters")
        if not isinstance(self.deltas, tuple):
            raise InvalidInputError("ExperimentComparison.deltas must be a tuple")
        for index, delta in enumerate(self.deltas):
            if not isinstance(delta, MetricDelta):
                raise InvalidInputError(f"deltas[{index}] must be MetricDelta")


@dataclass(frozen=True, slots=True)
class ExperimentRecord(Entity):
    lifecycle = "experiment"

    base_label: str
    candidate_label: str
    orders_total: int
    metric_version: str
    base_result_json: str
    candidate_result_json: str
    comparison_json: str

    def __post_init__(self) -> None:
        Entity.__post_init__(self)
        for name in ("base_label", "candidate_label", "metric_version"):
            value = getattr(self, name)
            if not isinstance(value, str) or not 1 <= len(value) <= 128:
                raise InvalidInputError(f"ExperimentRecord.{name} must be 1..128 characters")
        require_int(self.orders_total, field="ExperimentRecord.orders_total", minimum=0)
        for name in ("base_result_json", "candidate_result_json", "comparison_json"):
            if not isinstance(getattr(self, name), str):
                raise InvalidInputError(f"ExperimentRecord.{name} must be a string")
        require_non_negative_int(self.row_version, field="ExperimentRecord.row_version")
