"""PARTNER: the single composition root (AGENTS.md rule 3).

Only this module may import concrete adapters. Everything else depends on the
protocols in ``app.ports`` and receives the graph through parameters. Callers
that inject nothing get the real graph from here — never a test double:
``build_services`` has no test-only switch, and tests supply their fakes to the
function they exercise instead of installing them globally.

Adapter imports are deferred into :func:`build_services` on purpose: the
simulation adapter imports ``app.application.coordinator``, so importing it at
module import time would make ``application -> bootstrap -> adapter ->
application`` a real cycle.
"""
from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache

from app.ports.routing import RoutingSolver
from app.ports.simulation import Simulator
from app.ports.warehouse import WarehouseScheduler, WarehouseValidator


@dataclass(frozen=True)
class Services:
    """The process-wide service graph. Frozen: rewiring creates a new graph."""

    routing: RoutingSolver
    warehouse_scheduler: WarehouseScheduler
    warehouse_validator: WarehouseValidator
    simulator: Simulator


@lru_cache(maxsize=1)
def build_services() -> Services:
    """Construct the real adapter graph once per process."""
    from app.adapters.routing.ortools_solver import OrToolsRoutingSolver
    from app.adapters.simulation.simpy_simulator import SimPySimulator
    from app.adapters.warehouse.cp_sat_scheduler import CpSatWarehouseScheduler
    from app.adapters.warehouse.validator import WarehouseScheduleValidator

    return Services(
        routing=OrToolsRoutingSolver(),
        warehouse_scheduler=CpSatWarehouseScheduler(),
        warehouse_validator=WarehouseScheduleValidator(),
        simulator=SimPySimulator(),
    )


def describe_services(services: Services | None = None) -> dict[str, str]:
    """Stable, secret-free description used by health checks and handoff notes."""
    graph = services or build_services()
    return {
        'routing': type(graph.routing).__name__,
        'warehouse_scheduler': type(graph.warehouse_scheduler).__name__,
        'warehouse_validator': type(graph.warehouse_validator).__name__,
        'simulator': type(graph.simulator).__name__,
    }
