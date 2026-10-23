"""Metric values and missing-data semantics (P32-01 subset)."""

from __future__ import annotations

import math
from dataclasses import dataclass
from enum import StrEnum

from logistics_domain.errors import InvalidInputError
from logistics_domain.primitives import require_non_negative_int

__all__ = ["MetricSource", "MetricValue", "MissingReason"]


class MetricSource(StrEnum):
    PLANNED = "planned"
    SIMULATION = "simulation"
    ACTUAL = "actual"


class MissingReason(StrEnum):
    NOT_APPLICABLE = "not_applicable"
    MISSING_DATA = "missing_data"
    DIVISION_BY_ZERO = "division_by_zero"


@dataclass(frozen=True, slots=True)
class MetricValue:
    code: str
    definition_version: str
    source: MetricSource
    unit: str
    value: float | None
    numerator: float | None
    denominator: float | None
    reason: MissingReason | None
    sample_count: int

    def __post_init__(self) -> None:
        if not isinstance(self.code, str) or not self.code:
            raise InvalidInputError("MetricValue.code must be nonempty")
        if not isinstance(self.definition_version, str) or not self.definition_version:
            raise InvalidInputError("MetricValue.definition_version must be nonempty")
        if not isinstance(self.source, MetricSource):
            raise InvalidInputError("MetricValue.source must be MetricSource")
        if not isinstance(self.unit, str):
            raise InvalidInputError("MetricValue.unit must be a string")
        if self.value is not None:
            if not isinstance(self.value, (int, float)) or isinstance(self.value, bool):
                raise InvalidInputError("MetricValue.value must be numeric")
            if not math.isfinite(float(self.value)):
                raise InvalidInputError("MetricValue.value must be finite")
        if self.reason is not None and not isinstance(self.reason, MissingReason):
            raise InvalidInputError("MetricValue.reason must be MissingReason")
        if self.value is None and self.reason is None:
            raise InvalidInputError("a missing metric requires a reason")
        if self.value is not None and self.reason is not None:
            raise InvalidInputError("a present metric cannot carry a missing reason")
        require_non_negative_int(self.sample_count, field="MetricValue.sample_count")
