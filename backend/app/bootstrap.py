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


def build_negotiator(snapshot, *, policy=None, warehouse_resource_id: str | None = None,
                     vehicle_id: str | None = None, disruption_at_s: int | None = None,
                     recovery_s: int = 0):
    """Compose the R08 four-role contract net for one snapshot.

    Roles are bound to real snapshot objects: the warehouse role uses the chosen
    resource calendar, the transport role the chosen vehicle's shift.  When no
    disruption is declared the exception role cannot offer a slot (it bids for a
    recovery window that starts after the horizon), so it never wins by default.
    """
    from app.application.contract_net import (
        ContractNet,
        ExceptionRecoveryRole,
        TransportWindowRole,
        WarehouseWindowRole,
    )

    resources = sorted(snapshot.resources, key=lambda item: item.resource_id)
    resource = next((item for item in resources
                     if warehouse_resource_id is None or item.resource_id == warehouse_resource_id), None)
    if resource is None:
        raise ValueError(f'unknown_warehouse_resource:{warehouse_resource_id}')
    vehicles = sorted(snapshot.vehicles, key=lambda item: item.vehicle_id)
    vehicle = next((item for item in vehicles
                    if vehicle_id is None or item.vehicle_id == vehicle_id), None)
    if vehicle is None:
        raise ValueError(f'unknown_vehicle:{vehicle_id}')

    if disruption_at_s is None:
        # No declared disruption: the role has nothing to offer and stays silent.
        exception = ExceptionRecoveryRole(disruption_at_s=None, recovery_s=max(1, recovery_s),
                                          resource_id=resource.resource_id)
    else:
        exception = ExceptionRecoveryRole(disruption_at_s=disruption_at_s,
                                          recovery_s=max(1, recovery_s),
                                          resource_id=resource.resource_id)
    return ContractNet([
        WarehouseWindowRole(snapshot, resource.resource_id),
        TransportWindowRole(vehicle),
        exception,
    ], policy)

