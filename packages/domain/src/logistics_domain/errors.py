"""Typed domain errors.

Pure domain code raises these types instead of framework or ORM exceptions; the Algorithm
section of the P02-01 task states "错误只用领域类型，不依赖 Pydantic". Every error carries the
frozen :class:`~logistics_domain.states.ErrorCode` the boundary later maps to an HTTP status
with :data:`~logistics_domain.states.HTTP_STATUS_BY_ERROR_CODE`.

This module owns no frozen type: it is a leaf that imports only ``states``.
"""

from __future__ import annotations

from enum import StrEnum
from typing import Any, Final, TypeVar

from logistics_domain.states import ErrorCode

__all__ = [
    "DomainError",
    "InvalidInputError",
    "InvalidTransitionError",
    "UnknownEnumValueError",
    "parse_enum",
]

E = TypeVar("E", bound=StrEnum)


class DomainError(Exception):
    """Base class for every rejected domain operation."""

    code: Final[ErrorCode] = ErrorCode.INTERNAL_ERROR

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message

    def __str__(self) -> str:  # pragma: no cover - Exception already renders args
        return self.message


class InvalidInputError(DomainError):
    """A value violates a frozen field rule (NonNegativeInt, unit, range, shape)."""

    code: Final[ErrorCode] = ErrorCode.INVALID_INPUT


class UnknownEnumValueError(InvalidInputError):
    """A serialized value is not a member of the closed enum it claims to be."""

    def __init__(self, enum_name: str, value: Any, allowed: tuple[str, ...]) -> None:
        self.enum_name = enum_name
        self.value = value
        self.allowed = allowed
        super().__init__(
            f"{value!r} is not a {enum_name} member; allowed values: {', '.join(allowed)}"
        )


class InvalidTransitionError(DomainError):
    """A lifecycle move that no documented lifecycle allows."""

    code: Final[ErrorCode] = ErrorCode.INVALID_TRANSITION

    def __init__(self, *, state: StrEnum, to_state: StrEnum, allowed: frozenset[StrEnum]) -> None:
        self.state = state
        self.to_state = to_state
        self.allowed = allowed
        rendered = ", ".join(sorted(member.value for member in allowed)) or "(terminal state)"
        super().__init__(
            f"transition {state.value!r} -> {to_state.value!r} is not allowed; "
            f"allowed next states from {state.value!r}: {rendered}"
        )


def parse_enum(enum_cls: type[E], value: object, *, field: str | None = None) -> E:
    """Return ``value`` as a member of the closed enum ``enum_cls``.

    Members pass through unchanged; a serialized value is accepted only when it is an exact
    member value. Anything else raises :class:`UnknownEnumValueError`, which keeps the
    rejection typed instead of leaking a bare ``ValueError`` across a boundary.
    """
    if isinstance(value, enum_cls):
        return value
    try:
        return enum_cls(value)  # type: ignore[arg-type]
    except ValueError as exc:
        allowed = tuple(member.value for member in enum_cls)
        name = f"{enum_cls.__name__}" + (f" ({field})" if field else "")
        raise UnknownEnumValueError(name, value, allowed) from exc
