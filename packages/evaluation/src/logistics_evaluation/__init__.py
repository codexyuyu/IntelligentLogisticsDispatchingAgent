"""Evaluation layer: metric definitions, version comparison and experiment policies.

Layer rules: this package never modifies primary business data and never hides a
failed sample. A metric without a denominator returns ``null`` plus a reason instead
of a fabricated zero, per docs/algorithms/METRICS_CONTRACT.md.

complete calculates the 14 evidence-based metrics; metrics adapts legacy aggregate
inputs; values owns versions and comparability; paired implements paired experiments.
"""

from __future__ import annotations

from . import complete, metrics, paired, values

SCHEMA_VERSION = "1.0.0"
PACKAGE_NAME = "logistics-evaluation"
LAYER = "evaluation"

METRIC_COUNT = 14

__all__ = ["SCHEMA_VERSION", "PACKAGE_NAME", "LAYER", "METRIC_COUNT", "metrics", "complete", "paired", "values"]

_PENDING_APIS: dict[str, str] = {
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
