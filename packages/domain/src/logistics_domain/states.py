"""Single source of truth for domain ids, statuses and lifecycles.

Every enum in this module is defined **once** for the whole project
(`docs/architecture/TYPE_DEFINITION_OWNERSHIP.md`): later tasks must import these names
instead of re-declaring them, and `docs/architecture/DATA_CONTRACTS.md` forbids a second
hand-written standard.

Frozen sources used here, all under the 2.0.0 business contract / 1.0.3 plan:

* ``contracts/changes/N01-R01-contract-decisions.json`` — the exact member/value list of
  every enum below (tasks ``P02-01``, files ``states.py`` / ``primitives.py``).
* ``docs/architecture/DATA_CONTRACTS.md`` §公共类型与状态 (line 13 error table, line 156
  addition of ``RESULT_NOT_READY`` / ``UNVERIFIED_SOLVER_RESULT``).
* ``docs/architecture/DOMAIN_CATALOG.md`` — the ``状态与生命周期`` column, which is the
  authoritative lifecycle graph transcribed into :data:`LIFECYCLE_TRANSITIONS`.

The pure domain layer imports no framework, ORM, model SDK or solver engine, so this module
uses only the standard library.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from types import MappingProxyType
from typing import Final, Mapping, NewType

__all__ = [
    "ActorRole",
    "AttemptOutcome",
    "CargoCondition",
    "ConstraintCode",
    "DependencyStatus",
    "ENTITY_STATE_VALUES",
    "EntityKind",
    "EntityState",
    "ErrorCode",
    "ExpectationMeasure",
    "GenerationPolicy",
    "HTTP_STATUS_BY_ERROR_CODE",
    "ImportStatus",
    "JobKind",
    "JobOptimizationMode",
    "JobStatus",
    "LIFECYCLE_TRANSITIONS",
    "LifecycleOwner",
    "ReadyStatus",
    "ResourceKind",
    "ReturnPolicy",
    "RuntimeMode",
    "TerminalJobStatus",
    "Transition",
    "ViolationCode",
    "WeatherProfile",
    "allowed_next_states",
    "transition",
]


class JobKind(StrEnum):
    """Kind of a durable job; the serialized value is the lowercase word."""

    OPTIMIZATION = "optimization"
    SIMULATION = "simulation"
    RESCHEDULE = "reschedule"
    EXPERIMENT = "experiment"
    METRIC = "metric"


class JobStatus(StrEnum):
    """Durable job lifecycle. ``COMPLETED`` means a typed result exists."""

    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class JobOptimizationMode(StrEnum):
    """Optimization family carried by an ``optimization`` job payload."""

    TRANSPORT = "transport"
    WAREHOUSE = "warehouse"
    JOINT = "joint"


class ActorRole(StrEnum):
    VIEWER = "viewer"
    OPERATOR = "operator"


class ResourceKind(StrEnum):
    """The five warehouse resource classes addressable by a requirement."""

    ZONE = "zone"
    LOCATION = "location"
    DOCK = "dock"
    WORKER = "worker"
    EQUIPMENT = "equipment"


class GenerationPolicy(StrEnum):
    """Named synthetic-dataset generation policies."""

    CANONICAL_T1 = "canonical_t1"
    CANONICAL_W1 = "canonical_w1"
    CANONICAL_J1 = "canonical_j1"
    CANONICAL_I1 = "canonical_i1"
    CANONICAL_S1 = "canonical_s1"
    CANONICAL_M1 = "canonical_m1"
    GRID_A = "grid_a"
    GRID_B = "grid_b"
    GRID_C1 = "grid_c1"
    GRID_C2 = "grid_c2"
    GRID_C3 = "grid_c3"
    GRID = "grid"


class CargoCondition(StrEnum):
    INTACT = "intact"
    TEMPERATURE_EXCURSION = "temperature_excursion"
    DAMAGED = "damaged"
    MISSING = "missing"


class ReturnPolicy(StrEnum):
    RETURN_TO_ORIGIN = "return_to_origin"
    QUARANTINE = "quarantine"


class WeatherProfile(StrEnum):
    CLEAR = "clear"
    RAIN = "rain"
    SNOW = "snow"
    STORM = "storm"


class ExpectationMeasure(StrEnum):
    """Measure a scenario expectation is expressed in."""

    DISTANCE_M = "distance_m"
    COST_CENTS = "cost_cents"
    COMPLETION_S = "completion_s"
    MAKESPAN_S = "makespan_s"
    CHANGED_TASKS = "changed_tasks"


class AttemptOutcome(StrEnum):
    """Terminal outcome of one durable-job attempt."""

    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    LEASE_LOST = "lease_lost"


class TerminalJobStatus(StrEnum):
    """The subset of :class:`JobStatus` that ends a job."""

    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class ImportStatus(StrEnum):
    IMPORTED = "imported"
    NO_CHANGE = "no_change"
    REJECTED = "rejected"


class RuntimeMode(StrEnum):
    DEVELOPMENT = "development"
    TEST = "test"
    PRODUCTION = "production"


class ReadyStatus(StrEnum):
    READY = "ready"
    NOT_READY = "not_ready"


class DependencyStatus(StrEnum):
    AVAILABLE = "available"
    UNAVAILABLE = "unavailable"


class ErrorCode(StrEnum):
    """The only error codes in the system.

    Transcribed from the frozen error table (``DATA_CONTRACTS.md`` line 13) plus the two
    codes that line 156 adds to the same unique mapping. ``UNSUPPORTED`` is deliberately
    **not** a member: line 156 states it is not an ``ErrorCode``, and
    ``MANUAL_REQUIRED`` / ``NO_FEASIBLE_CANDIDATE`` are business result reasons rather than
    error codes, so they are excluded as well.
    """

    INVALID_INPUT = "invalid_input"
    INVALID_TRANSITION = "invalid_transition"
    DEPENDENCY_CYCLE = "dependency_cycle"
    UNAUTHENTICATED = "unauthenticated"
    FORBIDDEN = "forbidden"
    TOOL_FORBIDDEN = "tool_forbidden"
    NOT_FOUND = "not_found"
    STALE_SNAPSHOT = "stale_snapshot"
    RESOURCE_CONFLICT = "resource_conflict"
    IDEMPOTENCY_CONFLICT = "idempotency_conflict"
    CONFIRMATION_EXPIRED = "confirmation_expired"
    REQUEST_TOO_LARGE = "request_too_large"
    RATE_LIMITED = "rate_limited"
    PROVIDER_UNAVAILABLE = "provider_unavailable"
    DEPENDENCY_UNAVAILABLE = "dependency_unavailable"
    INTERNAL_ERROR = "internal_error"
    RESULT_NOT_READY = "result_not_ready"
    UNVERIFIED_SOLVER_RESULT = "unverified_solver_result"


#: Frozen ``code -> HTTP status`` table (``DATA_CONTRACTS.md`` line 13 and line 156).
#: The boundary layer maps codes with this table; the domain never builds an HTTP response.
HTTP_STATUS_BY_ERROR_CODE: Final[Mapping[ErrorCode, int]] = MappingProxyType(
    {
        ErrorCode.INVALID_INPUT: 422,
        ErrorCode.INVALID_TRANSITION: 422,
        ErrorCode.DEPENDENCY_CYCLE: 422,
        ErrorCode.UNVERIFIED_SOLVER_RESULT: 422,
        ErrorCode.UNAUTHENTICATED: 401,
        ErrorCode.FORBIDDEN: 403,
        ErrorCode.TOOL_FORBIDDEN: 403,
        ErrorCode.NOT_FOUND: 404,
        ErrorCode.STALE_SNAPSHOT: 409,
        ErrorCode.RESOURCE_CONFLICT: 409,
        ErrorCode.IDEMPOTENCY_CONFLICT: 409,
        ErrorCode.CONFIRMATION_EXPIRED: 409,
        ErrorCode.RESULT_NOT_READY: 409,
        ErrorCode.REQUEST_TOO_LARGE: 413,
        ErrorCode.RATE_LIMITED: 429,
        ErrorCode.PROVIDER_UNAVAILABLE: 503,
        ErrorCode.DEPENDENCY_UNAVAILABLE: 503,
        ErrorCode.INTERNAL_ERROR: 500,
    }
)


class EntityKind(StrEnum):
    """Addressable kinds used by ``EntityRef.kind``.

    The 45 members are the 32 required catalog entities, the required auxiliary entities and
    the matrix / inline-region address kinds. Enum metadata only *names* lookup targets; this
    module imports no future entity model.
    """

    ORDER = "order"
    CARGO = "cargo"
    VEHICLE = "vehicle"
    DRIVER = "driver"
    WAREHOUSE = "warehouse"
    WAREHOUSE_ZONE = "zone"
    STORAGE_LOCATION = "location"
    DOCK = "dock"
    WORKER = "worker"
    EQUIPMENT = "equipment"
    TRANSPORT_TASK = "transport_task"
    WAREHOUSE_TASK = "warehouse_task"
    ROUTE = "route"
    ROUTE_STOP = "route_stop"
    SCHEDULE = "schedule"
    SCHEDULE_TASK = "schedule_task"
    SCHEDULE_VERSION = "schedule_version"
    CONSTRAINT = "constraint"
    OPTIMIZATION_REQUEST = "optimization_request"
    OPTIMIZATION_RESULT = "optimization_result"
    SIMULATION = "simulation"
    SIMULATION_SNAPSHOT = "simulation_snapshot"
    EVENT = "event"
    EXCEPTION_EVENT = "exception_event"
    RESCHEDULE_REQUEST = "reschedule_request"
    RESCHEDULE_RESULT = "reschedule_result"
    AGENT_RUN = "agent_run"
    TOOL_CALL = "tool_call"
    DECISION_RECORD = "decision_record"
    EXPERIMENT = "experiment"
    METRIC = "metric"
    EXPERIMENT_RESULT = "experiment_result"
    PLANNING_SNAPSHOT = "planning_snapshot"
    JOB = "job"
    JOB_ATTEMPT = "job_attempt"
    IDEMPOTENCY = "idempotency"
    RESERVATION = "reservation"
    INVENTORY_LEDGER = "inventory_ledger"
    OUTBOX = "outbox"
    AUDIT_ENTRY = "audit_entry"
    LIFECYCLE_EVENT = "lifecycle_event"
    EXECUTION_SNAPSHOT = "execution_snapshot"
    CONFIRMATION_TOKEN = "confirmation_token"
    TRAVEL_MATRIX = "travel_matrix"
    REGION = "region"


#: Code vocabularies owned by the registration task, not by this task.
#:
#: ``ConstraintCode`` and ``ViolationCode`` are assigned to P02-01 by
#: ``TYPE_DEFINITION_OWNERSHIP.md``, but no frozen input enumerates a single member: the
#: contract only says ``ConstraintParameters`` is discriminated *by* ``ConstraintCode`` and
#: that the coverage registry (``P10-01``, ``ConstraintValidator`` / ``constraint_id``) is
#: what registers them. Inventing codes here would fabricate contract data, so this module
#: delivers the typed name only and the registry supplies the vocabulary. Registered as an
#: architecture issue by this task.
ConstraintCode = NewType("ConstraintCode", str)
ViolationCode = NewType("ViolationCode", str)


class EntityState(StrEnum):
    """Union of the lifecycle state words documented in ``DOMAIN_CATALOG.md``.

    ``EntityState`` is deliberately the *union* over all catalog lifecycles: this task owns
    the shared vocabulary, while per-entity precision comes from each entity's own status
    enum (P02-02/P02-03) and from :data:`LIFECYCLE_TRANSITIONS`. The lifecycle columns of
    ``DOMAIN_CATALOG.md`` are the only source of members; a test asserts this enum covers
    exactly the states that appear in the graph.
    """

    DRAFT = "draft"
    ACCEPTED = "accepted"
    SCHEDULED = "scheduled"
    IN_EXECUTION = "in_execution"
    DELIVERED = "delivered"
    CANCELLED = "cancelled"
    CANCEL_REQUESTED = "cancel_requested"
    CANCELLED_AFTER_RETURN = "cancelled_after_return"
    REGISTERED = "registered"
    STORED = "stored"
    LOADED = "loaded"
    IN_TRANSIT = "in_transit"
    QUARANTINED = "quarantined"
    RETURNED = "returned"
    AVAILABLE = "available"
    RESERVED = "reserved"
    IN_SERVICE = "in_service"
    UNAVAILABLE = "unavailable"
    RETIRED = "retired"
    ACTIVE = "active"
    OCCUPIED = "occupied"
    BUSY = "busy"
    FAILED = "failed"
    REPAIRING = "repairing"
    PENDING = "pending"
    READY = "ready"
    RUNNING = "running"
    COMPLETED = "completed"
    INTERRUPTED = "interrupted"
    CANDIDATE = "candidate"
    VALIDATED = "validated"
    PUBLISHED = "published"
    SUPERSEDED = "superseded"
    PLANNED = "planned"
    REACHED = "reached"
    SERVICING = "servicing"
    DISPATCHED = "dispatched"
    COMMITTED = "committed"
    RELEASED = "released"
    REJECTED = "rejected"
    EXPIRED = "expired"
    QUEUED = "queued"
    RECORDED = "recorded"
    SUSPENDED = "suspended"
    DEPRECATED = "deprecated"
    INVALIDATED = "invalidated"
    CREATED = "created"
    PAUSED = "paused"
    RECEIVED = "received"
    APPLIED = "applied"
    DUPLICATE = "duplicate"
    MANUAL_REQUIRED = "manual_required"
    UNRESOLVED = "unresolved"
    DETECTED = "detected"
    ANALYZED = "analyzed"
    PROPOSED = "proposed"
    RESOLVED = "resolved"
    PLANNING = "planning"
    EXECUTING = "executing"
    EXPLAINING = "explaining"
    AWAIT_CONFIRMATION = "await_confirmation"
    WAITING_INPUT = "waiting_input"
    REQUESTED = "requested"
    AUTHORIZED = "authorized"
    SUCCEEDED = "succeeded"
    DENIED = "denied"
    HELD = "held"
    DELIVERING = "delivering"
    DEAD_LETTER = "dead_letter"
    CONSUMED = "consumed"


#: Which catalog entity owns each lifecycle row in ``DOMAIN_CATALOG.md``.
LifecycleOwner = str

#: ``owner -> {state -> allowed next states}`` transcribed from the ``状态与生命周期`` column
#: of ``docs/architecture/DOMAIN_CATALOG.md`` (32 required entities plus the auxiliary
#: entities described in §必需辅助实体). ``↔`` is read as two directed edges, ``→`` as one.
#: A state that is absent as a key is terminal for that owner.
LIFECYCLE_TRANSITIONS: Final[Mapping[LifecycleOwner, Mapping[EntityState, frozenset[EntityState]]]] = (
    MappingProxyType(
        {
            "order": MappingProxyType(
                {
                    EntityState.DRAFT: frozenset({EntityState.ACCEPTED, EntityState.CANCELLED}),
                    EntityState.ACCEPTED: frozenset({EntityState.SCHEDULED, EntityState.CANCELLED}),
                    EntityState.SCHEDULED: frozenset({EntityState.IN_EXECUTION, EntityState.CANCELLED}),
                    EntityState.IN_EXECUTION: frozenset(
                        {EntityState.DELIVERED, EntityState.CANCEL_REQUESTED}
                    ),
                    EntityState.CANCEL_REQUESTED: frozenset({EntityState.CANCELLED_AFTER_RETURN}),
                    EntityState.DELIVERED: frozenset(),
                    EntityState.CANCELLED: frozenset(),
                    EntityState.CANCELLED_AFTER_RETURN: frozenset(),
                }
            ),
            "cargo": MappingProxyType(
                {
                    EntityState.REGISTERED: frozenset({EntityState.STORED, EntityState.QUARANTINED}),
                    EntityState.STORED: frozenset({EntityState.LOADED, EntityState.QUARANTINED}),
                    EntityState.LOADED: frozenset({EntityState.IN_TRANSIT, EntityState.QUARANTINED}),
                    EntityState.IN_TRANSIT: frozenset({EntityState.DELIVERED, EntityState.QUARANTINED}),
                    EntityState.DELIVERED: frozenset({EntityState.RETURNED}),
                    EntityState.QUARANTINED: frozenset(),
                    EntityState.RETURNED: frozenset(),
                }
            ),
            "vehicle": MappingProxyType(
                {
                    EntityState.AVAILABLE: frozenset(
                        {EntityState.RESERVED, EntityState.IN_SERVICE, EntityState.UNAVAILABLE}
                    ),
                    EntityState.RESERVED: frozenset(
                        {EntityState.IN_SERVICE, EntityState.AVAILABLE, EntityState.UNAVAILABLE}
                    ),
                    EntityState.IN_SERVICE: frozenset({EntityState.AVAILABLE, EntityState.UNAVAILABLE}),
                    EntityState.UNAVAILABLE: frozenset({EntityState.AVAILABLE, EntityState.RETIRED}),
                    EntityState.RETIRED: frozenset(),
                }
            ),
            "driver": MappingProxyType(
                {
                    EntityState.ACTIVE: frozenset({EntityState.UNAVAILABLE}),
                    EntityState.UNAVAILABLE: frozenset({EntityState.ACTIVE, EntityState.RETIRED}),
                    EntityState.RETIRED: frozenset(),
                }
            ),
            "warehouse": MappingProxyType(
                {
                    EntityState.ACTIVE: frozenset({EntityState.UNAVAILABLE}),
                    EntityState.UNAVAILABLE: frozenset({EntityState.ACTIVE, EntityState.RETIRED}),
                    EntityState.RETIRED: frozenset(),
                }
            ),
            "warehouse_zone": MappingProxyType(
                {
                    EntityState.ACTIVE: frozenset({EntityState.UNAVAILABLE}),
                    EntityState.UNAVAILABLE: frozenset({EntityState.ACTIVE, EntityState.RETIRED}),
                    EntityState.RETIRED: frozenset(),
                }
            ),
            "storage_location": MappingProxyType(
                {
                    EntityState.AVAILABLE: frozenset(
                        {EntityState.RESERVED, EntityState.OCCUPIED, EntityState.UNAVAILABLE}
                    ),
                    EntityState.RESERVED: frozenset(
                        {EntityState.AVAILABLE, EntityState.OCCUPIED, EntityState.UNAVAILABLE}
                    ),
                    EntityState.OCCUPIED: frozenset(
                        {EntityState.AVAILABLE, EntityState.RESERVED, EntityState.UNAVAILABLE}
                    ),
                    EntityState.UNAVAILABLE: frozenset({EntityState.AVAILABLE, EntityState.RETIRED}),
                    EntityState.RETIRED: frozenset(),
                }
            ),
            "dock": MappingProxyType(
                {
                    EntityState.AVAILABLE: frozenset({EntityState.BUSY, EntityState.UNAVAILABLE}),
                    EntityState.BUSY: frozenset({EntityState.AVAILABLE, EntityState.UNAVAILABLE}),
                    EntityState.UNAVAILABLE: frozenset({EntityState.AVAILABLE, EntityState.RETIRED}),
                    EntityState.RETIRED: frozenset(),
                }
            ),
            "worker": MappingProxyType(
                {
                    EntityState.AVAILABLE: frozenset({EntityState.BUSY, EntityState.UNAVAILABLE}),
                    EntityState.BUSY: frozenset({EntityState.AVAILABLE, EntityState.UNAVAILABLE}),
                    EntityState.UNAVAILABLE: frozenset({EntityState.AVAILABLE, EntityState.RETIRED}),
                    EntityState.RETIRED: frozenset(),
                }
            ),
            "equipment": MappingProxyType(
                {
                    EntityState.AVAILABLE: frozenset(
                        {EntityState.BUSY, EntityState.FAILED, EntityState.RETIRED}
                    ),
                    EntityState.BUSY: frozenset({EntityState.AVAILABLE, EntityState.FAILED}),
                    EntityState.FAILED: frozenset({EntityState.REPAIRING, EntityState.RETIRED}),
                    EntityState.REPAIRING: frozenset({EntityState.AVAILABLE, EntityState.RETIRED}),
                    EntityState.RETIRED: frozenset(),
                }
            ),
            "transport_task": MappingProxyType(
                {
                    EntityState.PENDING: frozenset(
                        {EntityState.READY, EntityState.CANCELLED, EntityState.INTERRUPTED, EntityState.FAILED}
                    ),
                    EntityState.READY: frozenset(
                        {EntityState.RUNNING, EntityState.CANCELLED, EntityState.INTERRUPTED, EntityState.FAILED}
                    ),
                    EntityState.RUNNING: frozenset(
                        {
                            EntityState.COMPLETED,
                            EntityState.CANCELLED,
                            EntityState.INTERRUPTED,
                            EntityState.FAILED,
                        }
                    ),
                    EntityState.COMPLETED: frozenset(),
                    EntityState.CANCELLED: frozenset(),
                    EntityState.INTERRUPTED: frozenset(),
                    EntityState.FAILED: frozenset(),
                }
            ),
            "warehouse_task": MappingProxyType(
                {
                    EntityState.PENDING: frozenset(
                        {EntityState.READY, EntityState.CANCELLED, EntityState.INTERRUPTED, EntityState.FAILED}
                    ),
                    EntityState.READY: frozenset(
                        {EntityState.RUNNING, EntityState.CANCELLED, EntityState.INTERRUPTED, EntityState.FAILED}
                    ),
                    EntityState.RUNNING: frozenset(
                        {
                            EntityState.COMPLETED,
                            EntityState.CANCELLED,
                            EntityState.INTERRUPTED,
                            EntityState.FAILED,
                        }
                    ),
                    EntityState.COMPLETED: frozenset(),
                    EntityState.CANCELLED: frozenset(),
                    EntityState.INTERRUPTED: frozenset(),
                    EntityState.FAILED: frozenset(),
                }
            ),
            "route": MappingProxyType(
                {
                    EntityState.CANDIDATE: frozenset({EntityState.VALIDATED}),
                    EntityState.VALIDATED: frozenset({EntityState.PUBLISHED}),
                    EntityState.PUBLISHED: frozenset({EntityState.SUPERSEDED}),
                    EntityState.SUPERSEDED: frozenset(),
                }
            ),
            "route_stop": MappingProxyType(
                {
                    EntityState.PLANNED: frozenset({EntityState.REACHED, EntityState.CANCELLED}),
                    EntityState.REACHED: frozenset({EntityState.SERVICING, EntityState.CANCELLED}),
                    EntityState.SERVICING: frozenset({EntityState.COMPLETED}),
                    EntityState.COMPLETED: frozenset(),
                    EntityState.CANCELLED: frozenset(),
                }
            ),
            "schedule": MappingProxyType(
                {
                    EntityState.DRAFT: frozenset({EntityState.ACTIVE}),
                    EntityState.ACTIVE: frozenset(
                        {EntityState.COMPLETED, EntityState.SUSPENDED, EntityState.SUPERSEDED}
                    ),
                    EntityState.SUSPENDED: frozenset({EntityState.ACTIVE}),
                    EntityState.COMPLETED: frozenset(),
                    EntityState.SUPERSEDED: frozenset(),
                }
            ),
            "schedule_task": MappingProxyType(
                {
                    EntityState.PLANNED: frozenset(
                        {EntityState.DISPATCHED, EntityState.CANCELLED, EntityState.INTERRUPTED}
                    ),
                    EntityState.DISPATCHED: frozenset(
                        {EntityState.RUNNING, EntityState.CANCELLED, EntityState.INTERRUPTED}
                    ),
                    EntityState.RUNNING: frozenset(
                        {EntityState.COMPLETED, EntityState.CANCELLED, EntityState.INTERRUPTED}
                    ),
                    EntityState.COMPLETED: frozenset(),
                    EntityState.CANCELLED: frozenset(),
                    EntityState.INTERRUPTED: frozenset(),
                }
            ),
            "schedule_version": MappingProxyType(
                {
                    EntityState.CANDIDATE: frozenset(
                        {EntityState.VALIDATED, EntityState.REJECTED, EntityState.EXPIRED}
                    ),
                    EntityState.VALIDATED: frozenset({EntityState.COMMITTED}),
                    EntityState.COMMITTED: frozenset({EntityState.SUPERSEDED}),
                    EntityState.SUPERSEDED: frozenset(),
                    EntityState.REJECTED: frozenset(),
                    EntityState.EXPIRED: frozenset(),
                }
            ),
            "constraint": MappingProxyType(
                {
                    EntityState.DRAFT: frozenset({EntityState.ACTIVE}),
                    EntityState.ACTIVE: frozenset({EntityState.DEPRECATED}),
                    EntityState.DEPRECATED: frozenset(),
                }
            ),
            "optimization_request": MappingProxyType(
                {
                    EntityState.ACCEPTED: frozenset(
                        {EntityState.QUEUED, EntityState.CANCELLED, EntityState.FAILED}
                    ),
                    EntityState.QUEUED: frozenset(
                        {EntityState.RUNNING, EntityState.CANCELLED, EntityState.FAILED}
                    ),
                    EntityState.RUNNING: frozenset(
                        {EntityState.COMPLETED, EntityState.CANCELLED, EntityState.FAILED}
                    ),
                    EntityState.COMPLETED: frozenset(),
                    EntityState.CANCELLED: frozenset(),
                    EntityState.FAILED: frozenset(),
                }
            ),
            "optimization_result": MappingProxyType(
                {
                    EntityState.RECORDED: frozenset({EntityState.INVALIDATED}),
                    EntityState.INVALIDATED: frozenset(),
                }
            ),
            "simulation": MappingProxyType(
                {
                    EntityState.CREATED: frozenset(
                        {EntityState.RUNNING, EntityState.CANCELLED, EntityState.FAILED}
                    ),
                    EntityState.RUNNING: frozenset(
                        {
                            EntityState.PAUSED,
                            EntityState.COMPLETED,
                            EntityState.CANCELLED,
                            EntityState.FAILED,
                        }
                    ),
                    EntityState.PAUSED: frozenset(
                        {EntityState.RUNNING, EntityState.CANCELLED, EntityState.FAILED}
                    ),
                    EntityState.COMPLETED: frozenset(),
                    EntityState.CANCELLED: frozenset(),
                    EntityState.FAILED: frozenset(),
                }
            ),
            "event": MappingProxyType(
                {
                    EntityState.RECEIVED: frozenset(
                        {
                            EntityState.VALIDATED,
                            EntityState.DUPLICATE,
                            EntityState.REJECTED,
                            EntityState.QUARANTINED,
                        }
                    ),
                    EntityState.VALIDATED: frozenset(
                        {
                            EntityState.APPLIED,
                            EntityState.DUPLICATE,
                            EntityState.REJECTED,
                            EntityState.QUARANTINED,
                        }
                    ),
                    EntityState.APPLIED: frozenset(),
                    EntityState.DUPLICATE: frozenset(),
                    EntityState.REJECTED: frozenset(),
                    EntityState.QUARANTINED: frozenset(),
                }
            ),
            "exception_event": MappingProxyType(
                {
                    EntityState.DETECTED: frozenset(
                        {EntityState.ANALYZED, EntityState.MANUAL_REQUIRED, EntityState.UNRESOLVED}
                    ),
                    EntityState.ANALYZED: frozenset(
                        {EntityState.PROPOSED, EntityState.MANUAL_REQUIRED, EntityState.UNRESOLVED}
                    ),
                    EntityState.PROPOSED: frozenset(
                        {EntityState.RESOLVED, EntityState.MANUAL_REQUIRED, EntityState.UNRESOLVED}
                    ),
                    EntityState.RESOLVED: frozenset(),
                    EntityState.MANUAL_REQUIRED: frozenset(),
                    EntityState.UNRESOLVED: frozenset(),
                }
            ),
            "reschedule_request": MappingProxyType(
                {
                    EntityState.ACCEPTED: frozenset(
                        {EntityState.QUEUED, EntityState.CANCELLED, EntityState.FAILED}
                    ),
                    EntityState.QUEUED: frozenset(
                        {EntityState.RUNNING, EntityState.CANCELLED, EntityState.FAILED}
                    ),
                    EntityState.RUNNING: frozenset(
                        {EntityState.COMPLETED, EntityState.CANCELLED, EntityState.FAILED}
                    ),
                    EntityState.COMPLETED: frozenset(),
                    EntityState.CANCELLED: frozenset(),
                    EntityState.FAILED: frozenset(),
                }
            ),
            "agent_run": MappingProxyType(
                {
                    EntityState.RECEIVED: frozenset(
                        {EntityState.PLANNING, EntityState.WAITING_INPUT, EntityState.FAILED, EntityState.CANCELLED}
                    ),
                    EntityState.PLANNING: frozenset(
                        {EntityState.EXECUTING, EntityState.WAITING_INPUT, EntityState.FAILED, EntityState.CANCELLED}
                    ),
                    EntityState.EXECUTING: frozenset(
                        {EntityState.EXPLAINING, EntityState.WAITING_INPUT, EntityState.FAILED, EntityState.CANCELLED}
                    ),
                    EntityState.EXPLAINING: frozenset(
                        {
                            EntityState.AWAIT_CONFIRMATION,
                            EntityState.WAITING_INPUT,
                            EntityState.FAILED,
                            EntityState.CANCELLED,
                        }
                    ),
                    EntityState.AWAIT_CONFIRMATION: frozenset(
                        {EntityState.COMPLETED, EntityState.WAITING_INPUT, EntityState.FAILED, EntityState.CANCELLED}
                    ),
                    EntityState.WAITING_INPUT: frozenset({EntityState.FAILED, EntityState.CANCELLED}),
                    EntityState.COMPLETED: frozenset(),
                    EntityState.FAILED: frozenset(),
                    EntityState.CANCELLED: frozenset(),
                }
            ),
            "tool_call": MappingProxyType(
                {
                    EntityState.REQUESTED: frozenset(
                        {EntityState.AUTHORIZED, EntityState.DENIED, EntityState.FAILED, EntityState.CANCELLED}
                    ),
                    EntityState.AUTHORIZED: frozenset(
                        {EntityState.RUNNING, EntityState.DENIED, EntityState.FAILED, EntityState.CANCELLED}
                    ),
                    EntityState.RUNNING: frozenset(
                        {EntityState.SUCCEEDED, EntityState.DENIED, EntityState.FAILED, EntityState.CANCELLED}
                    ),
                    EntityState.SUCCEEDED: frozenset(),
                    EntityState.DENIED: frozenset(),
                    EntityState.FAILED: frozenset(),
                    EntityState.CANCELLED: frozenset(),
                }
            ),
            "decision_record": MappingProxyType(
                {
                    EntityState.PROPOSED: frozenset(
                        {EntityState.ACCEPTED, EntityState.REJECTED, EntityState.SUPERSEDED}
                    ),
                    EntityState.ACCEPTED: frozenset({EntityState.SUPERSEDED}),
                    EntityState.REJECTED: frozenset({EntityState.SUPERSEDED}),
                    EntityState.SUPERSEDED: frozenset(),
                }
            ),
            "experiment": MappingProxyType(
                {
                    EntityState.DRAFT: frozenset(
                        {EntityState.QUEUED, EntityState.FAILED, EntityState.CANCELLED}
                    ),
                    EntityState.QUEUED: frozenset(
                        {EntityState.RUNNING, EntityState.FAILED, EntityState.CANCELLED}
                    ),
                    EntityState.RUNNING: frozenset(
                        {EntityState.COMPLETED, EntityState.FAILED, EntityState.CANCELLED}
                    ),
                    EntityState.COMPLETED: frozenset(),
                    EntityState.FAILED: frozenset(),
                    EntityState.CANCELLED: frozenset(),
                }
            ),
            "metric": MappingProxyType(
                {
                    EntityState.DRAFT: frozenset({EntityState.ACTIVE}),
                    EntityState.ACTIVE: frozenset({EntityState.DEPRECATED}),
                    EntityState.DEPRECATED: frozenset(),
                }
            ),
            "job": MappingProxyType(
                {
                    EntityState.QUEUED: frozenset(
                        {EntityState.RUNNING, EntityState.COMPLETED, EntityState.FAILED, EntityState.CANCELLED}
                    ),
                    EntityState.RUNNING: frozenset(
                        {EntityState.COMPLETED, EntityState.FAILED, EntityState.CANCELLED}
                    ),
                    EntityState.COMPLETED: frozenset(),
                    EntityState.FAILED: frozenset(),
                    EntityState.CANCELLED: frozenset(),
                }
            ),
            "idempotency": MappingProxyType(
                {EntityState.ACTIVE: frozenset({EntityState.EXPIRED}), EntityState.EXPIRED: frozenset()}
            ),
            # DOMAIN_CATALOG.md line 54: Reservation(held->committed->released/expired).
            # Only these three edges are authorised; released and expired are terminal.
            "reservation": MappingProxyType(
                {
                    EntityState.HELD: frozenset({EntityState.COMMITTED}),
                    EntityState.COMMITTED: frozenset(
                        {EntityState.RELEASED, EntityState.EXPIRED}
                    ),
                    EntityState.RELEASED: frozenset(),
                    EntityState.EXPIRED: frozenset(),
                }
            ),
            "outbox": MappingProxyType(
                {
                    EntityState.PENDING: frozenset({EntityState.DELIVERING}),
                    EntityState.DELIVERING: frozenset(
                        {EntityState.DELIVERED, EntityState.DEAD_LETTER}
                    ),
                    EntityState.DELIVERED: frozenset(),
                    EntityState.DEAD_LETTER: frozenset(),
                }
            ),
            "confirmation_token": MappingProxyType(
                {
                    EntityState.ACTIVE: frozenset({EntityState.CONSUMED, EntityState.EXPIRED}),
                    EntityState.CONSUMED: frozenset(),
                    EntityState.EXPIRED: frozenset(),
                }
            ),
        }
    )
)


@dataclass(frozen=True, slots=True)
class Transition:
    """A requested lifecycle move.

    ``to_state`` is the state the caller wants to reach; ``cause`` is the optional
    human-readable reason kept for the append-only ``LifecycleEvent`` projection.
    """

    to_state: EntityState
    cause: str | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.to_state, EntityState):
            raise TypeError(
                f"Transition.to_state must be an EntityState, got {type(self.to_state).__name__}"
            )
        if self.cause is not None:
            if not isinstance(self.cause, str):
                raise TypeError("Transition.cause must be a string when provided")
            if not 1 <= len(self.cause) <= 256:
                # Imported lazily: errors.py depends on this module's ErrorCode.
                from logistics_domain.errors import InvalidInputError

                raise InvalidInputError(
                    f"Transition.cause must be 1..256 characters, got {len(self.cause)}"
                )


def allowed_next_states(state: EntityState) -> frozenset[EntityState]:
    """Every state reachable from ``state`` in at least one catalog lifecycle.

    A state that never appears as a source in any lifecycle is terminal everywhere, so the
    result is empty.
    """
    if not isinstance(state, EntityState):
        raise TypeError(f"state must be an EntityState, got {type(state).__name__}")
    allowed: set[EntityState] = set()
    for graph in LIFECYCLE_TRANSITIONS.values():
        allowed.update(graph.get(state, frozenset()))
    return frozenset(allowed)


def transition(state: EntityState, event: Transition) -> EntityState:
    """Return the state reached by ``event``, or reject the move.

    The frozen interface is ``transition(state, event) -> EntityState`` without an entity
    parameter, so legality is judged against the union of the documented lifecycles:
    ``delivered -> draft`` is rejected because ``delivered`` has no outgoing edge in any
    catalog lifecycle. Use :data:`LIFECYCLE_TRANSITIONS` with an explicit owner when an
    entity-specific decision is required.
    """
    if not isinstance(state, EntityState):
        raise TypeError(f"state must be an EntityState, got {type(state).__name__}")
    if not isinstance(event, Transition):
        raise TypeError(f"event must be a Transition, got {type(event).__name__}")
    allowed = allowed_next_states(state)
    if event.to_state not in allowed:
        from logistics_domain.errors import InvalidTransitionError

        raise InvalidTransitionError(state=state, to_state=event.to_state, allowed=allowed)
    return event.to_state


#: Every value :class:`EntityState` must contain, derived from the lifecycle graph itself.
ENTITY_STATE_VALUES: Final[frozenset[str]] = frozenset(
    {state.value for graph in LIFECYCLE_TRANSITIONS.values() for state in graph}
    | {
        next_state.value
        for graph in LIFECYCLE_TRANSITIONS.values()
        for next_states in graph.values()
        for next_state in next_states
    }
)
