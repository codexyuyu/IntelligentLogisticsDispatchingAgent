"""Deterministic optimization layer: solvers, matrices and independent validation.

Layer rules: this package may depend on ``logistics_domain`` ports, must not query
the database or the network from solver logic, and must never mutate a formal
schedule. Third-party engine objects (OR-Tools ``RoutingModel``/``CpModel``) stay
inside this adapter layer and never cross an API, Agent or Simulation boundary.

Nothing is implemented yet: P06-01 onwards delivers the transport solver, P08/P09
the warehouse scheduler and P10 the constraint validator.
"""

from __future__ import annotations

SCHEMA_VERSION = "1.0.0"
PACKAGE_NAME = "logistics-optimization"
LAYER = "optimization"

# Engine that later tasks must lock and report: OR-Tools provides both the routing
# solver and CP-SAT. The concrete pinned version is recorded in uv.lock.
SOLVER_ENGINE = "ortools"

__all__ = ["SCHEMA_VERSION", "PACKAGE_NAME", "LAYER", "SOLVER_ENGINE"]

_PENDING_APIS: dict[str, str] = {
    "transport": "P07-01..P07-07: routing solve with typed candidate/status output",
    "warehouse": "P09-01..P09-05: CP-SAT scheduling with resource timelines",
    "matrix": "P06-02: versioned distance/time matrix provider",
    "validation": "P10-01..P10-03: independent hard-constraint validation report",
    "reschedule": "P15-01..P15-04: bounded local rescheduling under a frozen boundary",
}


def __getattr__(name: str):
    if name in _PENDING_APIS:
        raise NotImplementedError(
            f"logistics_optimization.{name} is not implemented yet ({_PENDING_APIS[name]}); "
            "see docs/implementation/P01-01.md for the delivered scope of the workspace bootstrap"
        )
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
