"""Pure domain layer of the logistics dispatching system.

Layer rules (docs/architecture/ARCHITECTURE_OVERVIEW.md): this package must not
import a web framework, an ORM, a model SDK or a solver engine. Entity fields,
statuses and lifecycles are defined by docs/architecture/DOMAIN_CATALOG.md, and
the shared units are integer seconds / metres / grams / cm3 / decic / fen with
UTC epoch, `[start, end)` occupancy and schema_version 2.0.0.

Delivered so far:

* P02-01: ``states``, ``primitives``, ``errors``.
* P02-02: ``orders``, ``resources``.
* P02-03: ``planning`` (tasks, versions, candidates, validation and matrices).
* P02-04: ``execution`` and ``runtime`` (events, scenarios, jobs, budgets).
* P03-03: ``ports.storage`` protocols.

Names outside this list still fail loudly through ``__getattr__`` so a missing
implementation can never be mistaken for a delivered one.
"""

from __future__ import annotations

from . import errors, execution, planning, ports, primitives, resources, runtime, states
from . import orders, transport, warehouse

# Gate evidence schema stays 1.0.0; the business/data contract is 2.0.0.
SCHEMA_VERSION = "1.0.0"
CONTRACT_VERSION = "2.0.0"
PACKAGE_NAME = "logistics-domain"
DOMAIN_LAYER = "domain"

# Legacy version this package must migrate from.
LEGACY_CONTRACT_VERSION = "0.1.0"

__all__ = [
    "SCHEMA_VERSION",
    "CONTRACT_VERSION",
    "LEGACY_CONTRACT_VERSION",
    "PACKAGE_NAME",
    "DOMAIN_LAYER",
    "errors",
    "execution",
    "orders",
    "planning",
    "ports",
    "primitives",
    "resources",
    "runtime",
    "states",
    "transport",
    "warehouse",
]

# Public API surface owned by later tasks. Declared here so that an accidental
# early import fails with an explicit message and an owner instead of silently
# creating a second definition of a domain concept.
_PENDING_APIS: dict[str, str] = {
    "joint": "P08-02: joint transport/warehouse problem values",
    "ids": "P02-01: typed identifier primitives (UUID-based)",
    "units": "P02-01: integer second/metre/gram/cm3/decic/fen value objects",
}


def __getattr__(name: str):
    if name in _PENDING_APIS:
        raise NotImplementedError(
            f"logistics_domain.{name} is not implemented yet ({_PENDING_APIS[name]}); "
            "see docs/implementation/ for the delivered scope"
        )
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
