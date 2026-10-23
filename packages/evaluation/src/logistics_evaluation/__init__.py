"""Evaluation layer: metric definitions, version comparison and experiment policies.

Layer rules: this package never modifies primary business data and never hides a
failed sample. A metric without a denominator returns ``null`` plus a reason instead
of a fabricated zero, per docs/algorithms/METRICS_CONTRACT.md.

Nothing is implemented yet: P32-01 onwards delivers the 14 metric calculators and
P33 the paired-seed experiment framework.
"""

from __future__ import annotations

SCHEMA_VERSION = "1.0.0"
PACKAGE_NAME = "logistics-evaluation"
LAYER = "evaluation"

METRIC_COUNT = 14

__all__ = ["SCHEMA_VERSION", "PACKAGE_NAME", "LAYER", "METRIC_COUNT"]

_PENDING_APIS: dict[str, str] = {
    "metrics": "P32-01: 14 metric calculators with explicit definition_version and source",
    "persistence": "P32-02: metric persistence and version comparison",
    "experiments": "P33-01: paired-seed experiments with retained failed samples",
}


def __getattr__(name: str):
    if name in _PENDING_APIS:
        raise NotImplementedError(
            f"logistics_evaluation.{name} is not implemented yet ({_PENDING_APIS[name]}); "
            "see docs/implementation/P01-01.md for the delivered scope of the workspace bootstrap"
        )
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
