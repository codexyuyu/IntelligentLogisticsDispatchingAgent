"""Metric constructors and comparability rules shared by all evaluation entrypoints."""
from logistics_domain.metrics import MetricSource, MetricValue, MissingReason

DEFINITION_VERSION = "1.1.0"


def _value(code: str, source: MetricSource, unit: str, value: float,
           numerator: float | None = None, denominator: float | None = None,
           sample_count: int = 1) -> MetricValue:
    return MetricValue(code=code, definition_version=DEFINITION_VERSION, source=source,
        unit=unit, value=float(value), numerator=numerator, denominator=denominator,
        reason=None, sample_count=sample_count)


def _missing(code: str, source: MetricSource, unit: str, reason: MissingReason) -> MetricValue:
    return MetricValue(code=code, definition_version=DEFINITION_VERSION, source=source,
        unit=unit, value=None, numerator=None, denominator=None, reason=reason,
        sample_count=0)


def comparable_values(left, right):
    a, b = ({m.code: m for m in values} for values in (left, right))
    if len(a) != len(left) or len(b) != len(right) or set(a) != set(b):
        raise ValueError("INCOMPARABLE_METRICS")
    if any((a[k].unit, a[k].definition_version, a[k].source) !=
           (b[k].unit, b[k].definition_version, b[k].source) for k in a):
        raise ValueError("INCOMPARABLE_METRICS")
    return a, b


def ratio_value(code, source, unit, numerator, denominator, sample_count):
    if denominator == 0:
        return _missing(code, source, unit, MissingReason.DIVISION_BY_ZERO)
    return _value(code, source, unit, numerator / denominator,
                  numerator, denominator, sample_count)
