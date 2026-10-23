"""Backend application: HTTP edge, application services, adapters and composition root.

Layer rules: this is the only assembly point. ``bootstrap.py`` (P05-01) instantiates
the database adapter, solvers, the SimPy engine and the LLM provider and injects them
into application services. Routers never construct a solver, never run a long solve
inside a request, and business state never bypasses an application service. Providers
that are not implemented yet must be registered as explicitly disabled, never wired
to an adapter that reports fixed success.

The API prefix is ``/api/v1`` (docs/api/API_CONTRACT.md). Nothing is implemented yet:
P03-03 onwards delivers persistence, P05-01 the composition root and error protocol.
"""

from __future__ import annotations

SCHEMA_VERSION = "1.0.0"
PACKAGE_NAME = "logistics-backend"
LAYER = "backend"
API_PREFIX = "/api/v1"

__all__ = ["SCHEMA_VERSION", "PACKAGE_NAME", "LAYER", "API_PREFIX"]

_PENDING_APIS: dict[str, str] = {
    "bootstrap": "P05-01: the single composition root",
    "app": "P05-01: FastAPI application with the error protocol",
    "router": "P05-01..P16-04: routers registered only for implemented capabilities",
    "services": "P05-02 onwards: application services holding the side effects",
    "worker": "P05-03: bounded worker with job leases, timeout and cancellation",
}


def __getattr__(name: str):
    if name in _PENDING_APIS:
        raise NotImplementedError(
            f"logistics_backend.{name} is not implemented yet ({_PENDING_APIS[name]}); "
            "see docs/implementation/P01-01.md for the delivered scope of the workspace bootstrap"
        )
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
