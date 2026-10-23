"""Backend-level typed service errors.

This module is the single error bridge between application/persistence and the HTTP layer.
It deliberately contains no framework import: adapters may raise it, API handlers map its
``status`` to a response, and the pure domain keeps using ``logistics_domain.errors``.
"""

from __future__ import annotations

from logistics_domain.errors import DomainError
from logistics_domain.states import ErrorCode


class ServiceError(DomainError):
    """A domain error with an optional explicit HTTP status (for example 501)."""

    def __init__(self, code: ErrorCode, message: str, status: int | None = None):
        super().__init__(message)
        self.code = code
        self.status = status


__all__ = ["ServiceError"]
