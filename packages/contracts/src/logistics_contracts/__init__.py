"""Boundary contract layer: Pydantic DTOs, domain mapping and schema export.

Layer rules: this package may depend on ``logistics_domain`` but must not perform
database access or business execution. Boundary models use ``extra="forbid"`` and
carry ``schema_version`` 1.0.0, per docs/architecture/DATA_CONTRACTS.md. Exported
JSON Schema and OpenAPI artifacts are produced by generators only, never hand-edited.

Nothing is implemented yet: P02-04 onwards delivers the DTOs and the export script.
"""

from __future__ import annotations

SCHEMA_VERSION = "1.0.0"
PACKAGE_NAME = "logistics-contracts"
LAYER = "contracts"

__all__ = ["SCHEMA_VERSION", "PACKAGE_NAME", "LAYER"]

_PENDING_APIS: dict[str, str] = {
    "dto": "P02-04/P05-01/P06-01: boundary DTOs with extra=forbid",
    "mapping": "P02-04: domain<->DTO mapping, no business rules duplicated",
    "export_schema": "P02-04: deterministic JSON Schema export via scripts/export_contracts.py",
    "errors": "P05-01: typed ErrorEnvelope per DATA_CONTRACTS error table",
}


def __getattr__(name: str):
    if name in _PENDING_APIS:
        raise NotImplementedError(
            f"logistics_contracts.{name} is not implemented yet ({_PENDING_APIS[name]}); "
            "see docs/implementation/P01-01.md for the delivered scope of the workspace bootstrap"
        )
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
