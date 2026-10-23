"""Shared domain primitives: identifiers, integer units and calendar values.

Units are the frozen ones (`docs/architecture/DOMAIN_CATALOG.md` lines 9-11 and
`docs/architecture/DATA_CONTRACTS.md` line 118): integer seconds, metres, grams, cm3,
fen (1/100 CNY), decicelsius and relative solve seconds; UTC instants are second-precision
and timezone-aware; resource occupancy is ``[start_s, end_s)`` while a service start window
is the closed interval ``[earliest_s, latest_s]``. Scalars reject ``bool``/``float`` and
stay inside the int64 range; ``PositiveInt`` is ``>= 1`` and ``NonNegativeInt`` is ``>= 0``.

Field lists follow ``contracts/changes/N01-R01-contract-decisions.json`` (task ``P02-01``,
file ``primitives.py``): ``TimeWindow``, ``Load``, ``CalendarInterval``, ``ResourceCalendar``,
``Rational``, ``EntityRef`` and ``ArtifactRef``. ``Money`` and the ``SafeArtifactPath`` shape
are the only names this task's own contract requires without a frozen member list; both are
documented in ``docs/implementation/P02-01.md`` and registered as issues.

No framework, ORM or solver import is allowed in the pure domain layer.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Final
from uuid import UUID

from logistics_domain.errors import InvalidInputError
from logistics_domain.states import EntityKind

__all__ = [
    "HORIZON_MAX_S",
    "INT64_MAX",
    "INT64_MIN",
    "ArtifactRef",
    "CalendarInterval",
    "EntityRef",
    "Load",
    "Money",
    "Rational",
    "ResourceCalendar",
    "TimeWindow",
    "intervals_adjacent",
    "intervals_overlap",
    "require_int",
    "require_non_negative_int",
    "require_positive_int",
    "require_safe_artifact_path",
    "require_safe_text",
    "require_sha256",
    "require_utc_seconds",
    "require_uuid",
]

INT64_MIN: Final[int] = -(2**63)
INT64_MAX: Final[int] = 2**63 - 1

#: Frozen horizon bound (`DOMAIN_CATALOG.md` line 11): default 86400 s, hard maximum 604800 s.
HORIZON_MAX_S: Final[int] = 604800

_SHA256_RE = re.compile(r"\A[0-9a-f]{64}\Z")
_UUID_RE = re.compile(r"\A[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\Z")


def require_int(
    value: object,
    *,
    field: str,
    minimum: int | None = None,
    maximum: int | None = None,
) -> int:
    """Validate an integer scalar: no ``bool``/``float``, int64 range, optional bounds."""
    if isinstance(value, bool) or not isinstance(value, int):
        raise InvalidInputError(
            f"{field} must be an int (bool and float are rejected), got {type(value).__name__}"
        )
    if not INT64_MIN <= value <= INT64_MAX:
        raise InvalidInputError(f"{field}={value} is outside the int64 range")
    if minimum is not None and value < minimum:
        raise InvalidInputError(f"{field}={value} must be >= {minimum}")
    if maximum is not None and value > maximum:
        raise InvalidInputError(f"{field}={value} must be <= {maximum}")
    return value


def require_non_negative_int(value: object, *, field: str, maximum: int | None = None) -> int:
    """``NonNegativeInt`` — an integer ``>= 0``."""
    return require_int(value, field=field, minimum=0, maximum=maximum)


def require_positive_int(value: object, *, field: str) -> int:
    """``PositiveInt`` — an integer ``>= 1``."""
    return require_int(value, field=field, minimum=1)


def require_uuid(value: object, *, field: str) -> UUID:
    """A ``UUID`` scalar. Standard lowercase textual form is required for text input."""
    if isinstance(value, UUID):
        return value
    if isinstance(value, str):
        if not _UUID_RE.match(value):
            raise InvalidInputError(f"{field} must be a lowercase canonical UUID, got {value!r}")
        return UUID(value)
    raise InvalidInputError(f"{field} must be a UUID, got {type(value).__name__}")


def require_utc_seconds(value: object, *, field: str) -> datetime:
    """``UTC`` — a timezone-aware datetime with no sub-second component."""
    if not isinstance(value, datetime):
        raise InvalidInputError(f"{field} must be a datetime, got {type(value).__name__}")
    if value.tzinfo is None or value.utcoffset() is None:
        raise InvalidInputError(f"{field} must be timezone-aware UTC, got a naive datetime")
    if value.utcoffset() != timezone.utc.utcoffset(value):
        raise InvalidInputError(f"{field} must be UTC, got offset {value.utcoffset()}")
    if value.microsecond != 0:
        raise InvalidInputError(f"{field} must have second precision, got microsecond={value.microsecond}")
    return value


def require_sha256(value: object, *, field: str) -> str:
    """``Sha256`` — 64 lowercase hexadecimal characters."""
    if not isinstance(value, str) or not _SHA256_RE.match(value):
        raise InvalidInputError(f"{field} must be 64 lowercase hex characters")
    return value


def require_safe_text(value: object, *, field: str) -> str:
    """``SafeText`` — 1..256 characters of already-sanitized explanation text."""
    if not isinstance(value, str):
        raise InvalidInputError(f"{field} must be a string, got {type(value).__name__}")
    if not 1 <= len(value) <= 256:
        raise InvalidInputError(f"{field} must be 1..256 characters, got {len(value)}")
    return value


def require_safe_artifact_path(value: object, *, field: str) -> str:
    """``SafeArtifactPath`` — a repository-relative POSIX path that cannot escape the root.

    The frozen inputs name this type through ``ArtifactRef`` but never publish its shape, so
    this validator implements the minimal safe reading (relative, forward slashes, no drive,
    UNC or ``..`` segment) and the gap is registered as an architecture issue.
    """
    if not isinstance(value, str):
        raise InvalidInputError(f"{field} must be a string, got {type(value).__name__}")
    if not value:
        raise InvalidInputError(f"{field} must not be empty")
    if "\\" in value:
        raise InvalidInputError(f"{field} must use forward slashes, got {value!r}")
    if value.startswith("/") or re.match(r"\A[A-Za-z]:", value):
        raise InvalidInputError(f"{field} must be relative, got {value!r}")
    parts = value.split("/")
    if any(part in ("", ".", "..") for part in parts):
        raise InvalidInputError(f"{field} must not contain empty, '.' or '..' segments: {value!r}")
    return value


@dataclass(frozen=True, slots=True)
class TimeWindow:
    """Closed service **start** window ``[earliest_s, latest_s]``; both ends are allowed."""

    earliest_s: int
    latest_s: int

    def __post_init__(self) -> None:
        require_non_negative_int(self.earliest_s, field="TimeWindow.earliest_s")
        require_non_negative_int(self.latest_s, field="TimeWindow.latest_s")
        if self.earliest_s > self.latest_s:
            raise InvalidInputError(
                f"TimeWindow requires earliest_s <= latest_s, got {self.earliest_s} > {self.latest_s}"
            )

    def contains_start(self, instant_s: int) -> bool:
        """A start instant is allowed when it lies inside the closed window."""
        require_non_negative_int(instant_s, field="instant_s")
        return self.earliest_s <= instant_s <= self.latest_s


@dataclass(frozen=True, slots=True)
class Load:
    """Cargo load in the frozen integer units: grams and cubic centimetres."""

    weight_g: int
    volume_cm3: int

    def __post_init__(self) -> None:
        require_non_negative_int(self.weight_g, field="Load.weight_g")
        require_non_negative_int(self.volume_cm3, field="Load.volume_cm3")

    def __add__(self, other: Load) -> Load:
        if not isinstance(other, Load):
            return NotImplemented
        return Load(weight_g=self.weight_g + other.weight_g, volume_cm3=self.volume_cm3 + other.volume_cm3)

    def __sub__(self, other: Load) -> Load:
        if not isinstance(other, Load):
            return NotImplemented
        return Load(weight_g=self.weight_g - other.weight_g, volume_cm3=self.volume_cm3 - other.volume_cm3)


@dataclass(frozen=True, slots=True)
class Money:
    """An amount of money in fen (1/100 CNY), the frozen integer money unit.

    The sign is not constrained here because the same value object also expresses cost
    deltas; callers that require a non-negative amount enforce that at their own boundary.
    """

    cents: int

    def __post_init__(self) -> None:
        require_int(self.cents, field="Money.cents")


@dataclass(frozen=True, slots=True)
class CalendarInterval:
    """Half-open availability interval ``[start_s, end_s)`` with an available unit count."""

    start_s: int
    end_s: int
    available_units: int

    def __post_init__(self) -> None:
        require_non_negative_int(self.start_s, field="CalendarInterval.start_s", maximum=HORIZON_MAX_S)
        require_non_negative_int(self.end_s, field="CalendarInterval.end_s", maximum=HORIZON_MAX_S)
        if self.start_s >= self.end_s:
            raise InvalidInputError(
                f"CalendarInterval requires 0 <= start_s < end_s <= {HORIZON_MAX_S}, "
                f"got start_s={self.start_s} end_s={self.end_s}"
            )
        require_non_negative_int(self.available_units, field="CalendarInterval.available_units")

    def covers(self, offset_s: int) -> bool:
        """Half-open containment: ``start_s <= offset_s < end_s``."""
        require_non_negative_int(offset_s, field="offset_s")
        return self.start_s <= offset_s < self.end_s


def intervals_overlap(left: CalendarInterval, right: CalendarInterval) -> bool:
    """Half-open overlap test. Adjacent intervals such as ``[0,10)`` and ``[10,20)`` do not conflict."""
    if not isinstance(left, CalendarInterval) or not isinstance(right, CalendarInterval):
        raise TypeError("intervals_overlap expects two CalendarInterval values")
    return left.start_s < right.end_s and right.start_s < left.end_s


def intervals_adjacent(left: CalendarInterval, right: CalendarInterval) -> bool:
    """True when the two half-open intervals touch without a gap and without overlapping."""
    if not isinstance(left, CalendarInterval) or not isinstance(right, CalendarInterval):
        raise TypeError("intervals_adjacent expects two CalendarInterval values")
    return left.end_s == right.start_s or right.end_s == left.start_s


@dataclass(frozen=True, slots=True)
class ResourceCalendar:
    """Versioned availability calendar of one resource, anchored at an explicit UTC epoch.

    ``epoch_utc`` is a required 2.0.0 field: without it the relative offsets have no absolute
    meaning, so construction without it is rejected. Intervals must be strictly ascending by
    ``start_s`` and must not overlap (touching is allowed). Time that no interval covers means
    zero available units - the calendar never implies capacity it does not state. An empty
    interval tuple is a valid calendar that offers nothing.
    """

    epoch_utc: datetime
    intervals: tuple[CalendarInterval, ...]
    version: int

    def __post_init__(self) -> None:
        require_utc_seconds(self.epoch_utc, field="ResourceCalendar.epoch_utc")
        require_non_negative_int(self.version, field="ResourceCalendar.version")
        if not isinstance(self.intervals, tuple):
            raise InvalidInputError(
                f"ResourceCalendar.intervals must be a tuple, got {type(self.intervals).__name__}"
            )
        previous: CalendarInterval | None = None
        for index, interval in enumerate(self.intervals):
            if not isinstance(interval, CalendarInterval):
                raise InvalidInputError(
                    f"ResourceCalendar.intervals[{index}] must be a CalendarInterval, "
                    f"got {type(interval).__name__}"
                )
            if previous is not None:
                if interval.start_s < previous.start_s:
                    raise InvalidInputError(
                        "ResourceCalendar.intervals must be strictly ascending by start_s: "
                        f"index {index} starts at {interval.start_s} after {previous.start_s}"
                    )
                if interval.start_s < previous.end_s:
                    raise InvalidInputError(
                        "ResourceCalendar.intervals must not overlap: "
                        f"[{previous.start_s},{previous.end_s}) and [{interval.start_s},{interval.end_s})"
                    )
            previous = interval

    def available_units_at(self, offset_s: int) -> int:
        """Available units at ``offset_s`` seconds after the epoch; 0 when uncovered."""
        require_non_negative_int(offset_s, field="offset_s")
        for interval in self.intervals:
            if interval.covers(offset_s):
                return interval.available_units
        return 0

    def total_covered_seconds(self) -> int:
        """Sum of the covered durations; useful for diagnostics, not for capacity."""
        return sum(interval.end_s - interval.start_s for interval in self.intervals)


@dataclass(frozen=True, slots=True)
class Rational:
    """A positive rational kept in lowest terms for deterministic integer scaling."""

    numerator: int
    denominator: int

    def __post_init__(self) -> None:
        require_positive_int(self.numerator, field="Rational.numerator")
        require_positive_int(self.denominator, field="Rational.denominator")
        divisor = _gcd(self.numerator, self.denominator)
        if divisor != 1:
            object.__setattr__(self, "numerator", self.numerator // divisor)
            object.__setattr__(self, "denominator", self.denominator // divisor)

    def scale(self, duration_s: int) -> int:
        """``ceil(duration_s * numerator / denominator)`` with an int64 overflow check."""
        require_non_negative_int(duration_s, field="duration_s")
        product = duration_s * self.numerator
        if not INT64_MIN <= product <= INT64_MAX:
            raise InvalidInputError(
                f"Rational.scale overflow: {duration_s} * {self.numerator} exceeds int64"
            )
        return -(-product // self.denominator)

    def __float__(self) -> float:
        return self.numerator / self.denominator


def _gcd(left: int, right: int) -> int:
    while right:
        left, right = right, left % right
    return left


@dataclass(frozen=True, slots=True)
class EntityRef:
    """Typed reference to one entity, optionally pinned to a revision.

    ``revision`` omitted means "identity only" and does not claim the current version
    matches; when supplied it is verified against the chosen immutable fact snapshot.
    """

    kind: EntityKind
    id: UUID
    revision: int | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.kind, EntityKind):
            raise InvalidInputError(
                f"EntityRef.kind must be an EntityKind, got {type(self.kind).__name__}"
            )
        require_uuid(self.id, field="EntityRef.id")
        if self.revision is not None:
            require_non_negative_int(self.revision, field="EntityRef.revision")


@dataclass(frozen=True, slots=True)
class ArtifactRef:
    """Reference to a stored artifact; the digest and relative path are both mandatory."""

    id: UUID
    media_type: str
    sha256: str
    relative_path: str

    def __post_init__(self) -> None:
        require_uuid(self.id, field="ArtifactRef.id")
        if not isinstance(self.media_type, str) or not self.media_type:
            raise InvalidInputError("ArtifactRef.media_type must be a non-empty string")
        require_sha256(self.sha256, field="ArtifactRef.sha256")
        require_safe_artifact_path(self.relative_path, field="ArtifactRef.relative_path")
