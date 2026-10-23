"""Simulation layer: SimPy digital twin, event engine and snapshot replay.

Layer rules: simulation results are never formal facts. A simulation runs in an
isolated branch, exposes explicit RNG state and a stable event ordering, and only
an application service may commit a plan. Third-party engine objects (``simpy``
Environment/Process) stay inside this adapter layer.

Nothing is implemented yet: P11-01 onwards delivers the simulation contract,
P12 the SimPy kernel and P13 the event engine.
"""

from __future__ import annotations

SCHEMA_VERSION = "1.0.0"
PACKAGE_NAME = "logistics-simulation"
LAYER = "simulation"

SIMULATION_ENGINE = "simpy"

__all__ = ["SCHEMA_VERSION", "PACKAGE_NAME", "LAYER", "SIMULATION_ENGINE"]

_PENDING_APIS: dict[str, str] = {
    "kernel": "P12-01: deterministic time advance and stable same-second event order",
    "execution": "P11-02/P12-02/P12-03: execution state machines for order/vehicle/warehouse",
    "events": "P13-01/P13-02: ten exception event kinds, dedup, ordering, outbox",
    "snapshot": "P12-04: snapshot restore and counterfactual branch isolation",
    "impact": "P14-01/P14-02: impact closure and execution-freeze boundary",
}


def __getattr__(name: str):
    if name in _PENDING_APIS:
        raise NotImplementedError(
            f"logistics_simulation.{name} is not implemented yet ({_PENDING_APIS[name]}); "
            "see docs/implementation/P01-01.md for the delivered scope of the workspace bootstrap"
        )
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
