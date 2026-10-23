"""Unit checks for P02-01: domain ids, integer units and the unique state enums.

Every assertion is over frozen contract data:

* enum members and serialized values come from
  ``contracts/changes/N01-R01-contract-decisions.json`` (task ``P02-01``);
* field rules come from ``docs/architecture/DATA_CONTRACTS.md`` line 118;
* lifecycles come from the ``状态与生命周期`` column of ``docs/architecture/DOMAIN_CATALOG.md``.

The six Test Cases of the task are covered here (and again at the real boundary in the
integration file). Negative cases change exactly one field and assert the typed rejection.
"""

from __future__ import annotations

import json
from dataclasses import FrozenInstanceError
from datetime import datetime, timedelta, timezone
from uuid import UUID, uuid4

import pytest
from logistics_domain import primitives, states
from logistics_domain.errors import (
    DomainError,
    InvalidInputError,
    InvalidTransitionError,
    UnknownEnumValueError,
    parse_enum,
)
from logistics_domain.primitives import (
    CalendarInterval,
    EntityRef,
    Load,
    Money,
    Rational,
    ResourceCalendar,
    TimeWindow,
    intervals_adjacent,
    intervals_overlap,
)
from logistics_domain.states import (
    CargoCondition,
    DependencyStatus,
    EntityKind,
    EntityState,
    ErrorCode,
    ExpectationMeasure,
    GenerationPolicy,
    ImportStatus,
    JobKind,
    JobOptimizationMode,
    JobStatus,
    ReadyStatus,
    ReturnPolicy,
    RuntimeMode,
    TerminalJobStatus,
    Transition,
    WeatherProfile,
    transition,
)

UTC_EPOCH = datetime(2026, 1, 1, tzinfo=timezone.utc)


def calendar(*intervals: CalendarInterval, version: int = 0) -> ResourceCalendar:
    return ResourceCalendar(epoch_utc=UTC_EPOCH, intervals=tuple(intervals), version=version)


# ----------------------------------------------------------------- test case 1


def test_test_case_1_adjacent_half_open_intervals_do_not_conflict() -> None:
    """Test Case 1: [0,10) 和 [10,20) => 不冲突."""
    first = CalendarInterval(start_s=0, end_s=10, available_units=1)
    second = CalendarInterval(start_s=10, end_s=20, available_units=1)

    assert intervals_overlap(first, second) is False
    assert intervals_overlap(second, first) is False
    assert intervals_adjacent(first, second) is True
    # The touching point belongs to the second interval only.
    assert first.covers(9) is True and first.covers(10) is False
    assert second.covers(10) is True
    assert calendar(first, second).available_units_at(10) == 1


def test_overlapping_half_open_intervals_are_detected() -> None:
    first = CalendarInterval(start_s=0, end_s=10, available_units=1)
    overlapping = CalendarInterval(start_s=9, end_s=20, available_units=1)
    assert intervals_overlap(first, overlapping) is True
    assert intervals_adjacent(first, overlapping) is False
    with pytest.raises(InvalidInputError):
        calendar(first, overlapping)


def test_identical_intervals_conflict() -> None:
    same = CalendarInterval(start_s=3, end_s=7, available_units=2)
    assert intervals_overlap(same, same) is True
    with pytest.raises(InvalidInputError):
        calendar(same, same)


def test_intervals_must_be_strictly_ascending() -> None:
    later = CalendarInterval(start_s=20, end_s=30, available_units=1)
    earlier = CalendarInterval(start_s=0, end_s=10, available_units=1)
    with pytest.raises(InvalidInputError):
        calendar(later, earlier)


# ----------------------------------------------------------------- test case 2


def test_test_case_2_delivered_to_draft_is_invalid_transition() -> None:
    """Test Case 2: delivered -> draft => INVALID_TRANSITION."""
    with pytest.raises(InvalidTransitionError) as error:
        transition(EntityState.DELIVERED, Transition(EntityState.DRAFT))

    assert error.value.code is ErrorCode.INVALID_TRANSITION
    assert error.value.state is EntityState.DELIVERED
    assert error.value.to_state is EntityState.DRAFT
    # `delivered` has no edge to `draft`; the only successor documented anywhere is the
    # cargo return leg, so the rejected move cannot be smuggled in through another lifecycle.
    assert EntityState.DRAFT not in states.allowed_next_states(EntityState.DELIVERED)
    assert states.allowed_next_states(EntityState.DELIVERED) == frozenset({EntityState.RETURNED})


def test_documented_transitions_are_accepted() -> None:
    assert transition(EntityState.DRAFT, Transition(EntityState.ACCEPTED)) is EntityState.ACCEPTED
    assert transition(EntityState.IN_TRANSIT, Transition(EntityState.DELIVERED)) is EntityState.DELIVERED
    assert transition(EntityState.QUEUED, Transition(EntityState.RUNNING)) is EntityState.RUNNING


def test_transition_rejects_wrong_argument_types() -> None:
    with pytest.raises(TypeError):
        transition("draft", Transition(EntityState.ACCEPTED))  # type: ignore[arg-type]
    with pytest.raises(TypeError):
        transition(EntityState.DRAFT, EntityState.ACCEPTED)  # type: ignore[arg-type]


def test_transition_cause_is_validated_as_safe_text() -> None:
    assert Transition(EntityState.ACCEPTED, cause="operator accepted").cause == "operator accepted"
    with pytest.raises(InvalidInputError):
        Transition(EntityState.ACCEPTED, cause="")
    with pytest.raises(InvalidInputError):
        Transition(EntityState.ACCEPTED, cause="x" * 257)
    with pytest.raises(TypeError):
        Transition(EntityState.ACCEPTED, cause=7)  # type: ignore[arg-type]


def test_cancelled_is_terminal_but_reachable() -> None:
    assert EntityState.CANCELLED in states.allowed_next_states(EntityState.DRAFT)
    assert states.allowed_next_states(EntityState.CANCELLED) == frozenset()
    with pytest.raises(InvalidTransitionError):
        transition(EntityState.CANCELLED, Transition(EntityState.DRAFT))


# ----------------------------------------------------------------- test case 3


def test_test_case_3_job_kind_and_optimization_mode_serialize_to_fixed_values() -> None:
    """Test Case 3: JobKind=simulation 与 JobOptimizationMode=transport 各自序列化 => 固定唯一值."""
    assert json.dumps(JobKind.SIMULATION) == '"simulation"'
    assert json.dumps(JobOptimizationMode.TRANSPORT) == '"transport"'
    assert JobKind.SIMULATION.value == "simulation"
    assert JobOptimizationMode.TRANSPORT.value == "transport"
    assert json.loads(json.dumps({"kind": JobKind.METRIC, "mode": JobOptimizationMode.JOINT})) == {
        "kind": "metric",
        "mode": "joint",
    }


# ----------------------------------------------------------------- test case 4


def test_test_case_4_unknown_job_kind_is_rejected() -> None:
    """Test Case 4: JobKind=routing => 拒绝未知枚举."""
    with pytest.raises(ValueError):
        JobKind("routing")
    with pytest.raises(ValueError):
        JobOptimizationMode("routing")

    with pytest.raises(UnknownEnumValueError) as error:
        parse_enum(JobKind, "routing", field="kind")
    assert error.value.code is ErrorCode.INVALID_INPUT
    assert error.value.value == "routing"
    assert "optimization" in error.value.allowed


def test_parse_enum_passes_members_and_parses_exact_values() -> None:
    assert parse_enum(JobKind, JobKind.METRIC) is JobKind.METRIC
    assert parse_enum(JobKind, "metric") is JobKind.METRIC
    with pytest.raises(UnknownEnumValueError):
        parse_enum(JobKind, "METRIC")


# ----------------------------------------------------------------- test case 5


def test_test_case_5_zero_length_calendar_interval_is_rejected() -> None:
    """Test Case 5: CalendarInterval(start_s=10,end_s=10) => 拒绝."""
    with pytest.raises(InvalidInputError):
        CalendarInterval(start_s=10, end_s=10, available_units=1)
    with pytest.raises(InvalidInputError):
        CalendarInterval(start_s=10, end_s=9, available_units=1)


def test_calendar_interval_bounds_and_units() -> None:
    assert CalendarInterval(0, primitives.HORIZON_MAX_S, 0).available_units == 0
    with pytest.raises(InvalidInputError):
        CalendarInterval(start_s=-1, end_s=10, available_units=1)
    with pytest.raises(InvalidInputError):
        CalendarInterval(start_s=0, end_s=primitives.HORIZON_MAX_S + 1, available_units=1)
    with pytest.raises(InvalidInputError):
        CalendarInterval(start_s=0, end_s=10, available_units=-1)


# ----------------------------------------------------------------- test case 6


def test_test_case_6_calendar_without_epoch_is_rejected() -> None:
    """Test Case 6: calendar 缺 epoch_utc => 拒绝."""
    with pytest.raises(TypeError):
        ResourceCalendar(intervals=(CalendarInterval(0, 10, 1),), version=0)  # type: ignore[call-arg]
    with pytest.raises(InvalidInputError):
        ResourceCalendar(epoch_utc=None, intervals=(), version=0)  # type: ignore[arg-type]
    with pytest.raises(InvalidInputError):
        ResourceCalendar(epoch_utc=datetime(2026, 1, 1), intervals=(), version=0)


def test_calendar_epoch_rules() -> None:
    with pytest.raises(InvalidInputError):
        ResourceCalendar(epoch_utc=UTC_EPOCH.replace(tzinfo=None), intervals=(), version=0)
    with pytest.raises(InvalidInputError):
        ResourceCalendar(epoch_utc=UTC_EPOCH.astimezone(timezone(timedelta(hours=8))), intervals=(), version=0)
    with pytest.raises(InvalidInputError):
        ResourceCalendar(epoch_utc=UTC_EPOCH.replace(microsecond=1), intervals=(), version=0)
    with pytest.raises(InvalidInputError):
        calendar(version=-1)


def test_calendar_never_implies_capacity_it_does_not_state() -> None:
    empty = calendar()
    assert empty.intervals == ()
    assert empty.available_units_at(0) == 0
    assert empty.total_covered_seconds() == 0

    covered = calendar(CalendarInterval(0, 10, 2))
    assert covered.available_units_at(0) == 2
    assert covered.available_units_at(9) == 2
    assert covered.available_units_at(10) == 0
    assert covered.available_units_at(3600) == 0


def test_calendar_intervals_must_be_calendar_interval_instances() -> None:
    with pytest.raises(InvalidInputError):
        ResourceCalendar(epoch_utc=UTC_EPOCH, intervals=([0, 10, 1],), version=0)  # type: ignore[arg-type]
    with pytest.raises(InvalidInputError):
        ResourceCalendar(epoch_utc=UTC_EPOCH, intervals=[CalendarInterval(0, 10, 1)], version=0)  # type: ignore[arg-type]


# ------------------------------------------------------------ frozen enum fidelity


def test_every_frozen_enum_member_and_value_is_exact() -> None:
    expected: dict[type, dict[str, str]] = {
        JobKind: {
            "OPTIMIZATION": "optimization",
            "SIMULATION": "simulation",
            "RESCHEDULE": "reschedule",
            "EXPERIMENT": "experiment",
            "METRIC": "metric",
        },
        JobStatus: {
            "QUEUED": "queued",
            "RUNNING": "running",
            "COMPLETED": "completed",
            "FAILED": "failed",
            "CANCELLED": "cancelled",
        },
        JobOptimizationMode: {"TRANSPORT": "transport", "WAREHOUSE": "warehouse", "JOINT": "joint"},
        states.ActorRole: {"VIEWER": "viewer", "OPERATOR": "operator"},
        states.ResourceKind: {
            "ZONE": "zone",
            "LOCATION": "location",
            "DOCK": "dock",
            "WORKER": "worker",
            "EQUIPMENT": "equipment",
        },
        GenerationPolicy: {
            "CANONICAL_T1": "canonical_t1",
            "CANONICAL_W1": "canonical_w1",
            "CANONICAL_J1": "canonical_j1",
            "CANONICAL_I1": "canonical_i1",
            "CANONICAL_S1": "canonical_s1",
            "CANONICAL_M1": "canonical_m1",
            "GRID_A": "grid_a",
            "GRID_B": "grid_b",
            "GRID_C1": "grid_c1",
            "GRID_C2": "grid_c2",
            "GRID_C3": "grid_c3",
            "GRID": "grid",
        },
        CargoCondition: {
            "INTACT": "intact",
            "TEMPERATURE_EXCURSION": "temperature_excursion",
            "DAMAGED": "damaged",
            "MISSING": "missing",
        },
        ReturnPolicy: {"RETURN_TO_ORIGIN": "return_to_origin", "QUARANTINE": "quarantine"},
        WeatherProfile: {"CLEAR": "clear", "RAIN": "rain", "SNOW": "snow", "STORM": "storm"},
        ExpectationMeasure: {
            "DISTANCE_M": "distance_m",
            "COST_CENTS": "cost_cents",
            "COMPLETION_S": "completion_s",
            "MAKESPAN_S": "makespan_s",
            "CHANGED_TASKS": "changed_tasks",
        },
        states.AttemptOutcome: {
            "COMPLETED": "completed",
            "FAILED": "failed",
            "CANCELLED": "cancelled",
            "LEASE_LOST": "lease_lost",
        },
        TerminalJobStatus: {"COMPLETED": "completed", "FAILED": "failed", "CANCELLED": "cancelled"},
        ImportStatus: {"IMPORTED": "imported", "NO_CHANGE": "no_change", "REJECTED": "rejected"},
        RuntimeMode: {"DEVELOPMENT": "development", "TEST": "test", "PRODUCTION": "production"},
        ReadyStatus: {"READY": "ready", "NOT_READY": "not_ready"},
        DependencyStatus: {"AVAILABLE": "available", "UNAVAILABLE": "unavailable"},
    }
    for enum_cls, members in expected.items():
        assert {member.name: member.value for member in enum_cls} == members, enum_cls.__name__


def test_entity_kind_has_exactly_the_frozen_45_members() -> None:
    assert len(EntityKind) == 45
    assert EntityKind.WAREHOUSE_ZONE.value == "zone"
    assert EntityKind.STORAGE_LOCATION.value == "location"
    assert EntityKind.TRAVEL_MATRIX.value == "travel_matrix"
    assert EntityKind.REGION.value == "region"
    assert len({member.value for member in EntityKind}) == 45


def test_error_code_table_is_exactly_the_frozen_mapping() -> None:
    expected = {
        "invalid_input": 422,
        "invalid_transition": 422,
        "dependency_cycle": 422,
        "unverified_solver_result": 422,
        "unauthenticated": 401,
        "forbidden": 403,
        "tool_forbidden": 403,
        "not_found": 404,
        "stale_snapshot": 409,
        "resource_conflict": 409,
        "idempotency_conflict": 409,
        "confirmation_expired": 409,
        "result_not_ready": 409,
        "request_too_large": 413,
        "rate_limited": 429,
        "provider_unavailable": 503,
        "dependency_unavailable": 503,
        "internal_error": 500,
    }
    assert {code.value: status for code, status in states.HTTP_STATUS_BY_ERROR_CODE.items()} == expected
    assert {code.value for code in ErrorCode} == set(expected)
    # DATA_CONTRACTS line 156: UNSUPPORTED is explicitly not an ErrorCode.
    assert "unsupported" not in {code.value for code in ErrorCode}
    # Business result reasons are not error codes either.
    assert {"manual_required", "no_feasible_candidate"}.isdisjoint({code.value for code in ErrorCode})


def test_entity_state_covers_exactly_the_lifecycle_graph() -> None:
    member_values = {member.value for member in EntityState}
    assert member_values == set(states.ENTITY_STATE_VALUES)
    graph_next = {
        next_state.value
        for graph in states.LIFECYCLE_TRANSITIONS.values()
        for next_states in graph.values()
        for next_state in next_states
    }
    assert graph_next <= member_values


def test_lifecycle_edges_match_the_domain_catalog_rows() -> None:
    graph = states.LIFECYCLE_TRANSITIONS
    assert set(graph) == {
        "order",
        "cargo",
        "vehicle",
        "driver",
        "warehouse",
        "warehouse_zone",
        "storage_location",
        "dock",
        "worker",
        "equipment",
        "transport_task",
        "warehouse_task",
        "route",
        "route_stop",
        "schedule",
        "schedule_task",
        "schedule_version",
        "constraint",
        "optimization_request",
        "optimization_result",
        "simulation",
        "event",
        "exception_event",
        "reschedule_request",
        "agent_run",
        "tool_call",
        "decision_record",
        "experiment",
        "metric",
        "job",
        "idempotency",
        "reservation",
        "outbox",
        "confirmation_token",
    }
    assert graph["order"][EntityState.DRAFT] == frozenset({EntityState.ACCEPTED, EntityState.CANCELLED})
    assert graph["order"][EntityState.DELIVERED] == frozenset()
    assert graph["schedule"][EntityState.ACTIVE] == frozenset(
        {EntityState.COMPLETED, EntityState.SUSPENDED, EntityState.SUPERSEDED}
    )
    assert graph["schedule"][EntityState.SUSPENDED] == frozenset({EntityState.ACTIVE})
    # ↔ means both directions
    assert EntityState.RUNNING in graph["simulation"][EntityState.PAUSED]
    assert EntityState.PAUSED in graph["simulation"][EntityState.RUNNING]


def test_reservation_lifecycle_matches_the_frozen_catalog_exactly() -> None:
    """``DOMAIN_CATALOG.md``: ``Reservation(held→committed→released/expired)``.

    The exact edge set is asserted on the **entity-specific** graph: the global union also
    carries other entities' edges out of ``committed`` (for example ``superseded`` from
    scheduling), so the union is the wrong object for this check.
    """
    graph = states.LIFECYCLE_TRANSITIONS["reservation"]
    assert {state.value for state in graph} == {"held", "committed", "released", "expired"}
    edges = {(source.value, target.value) for source, targets in graph.items() for target in targets}
    assert edges == {("held", "committed"), ("committed", "released"), ("committed", "expired")}
    assert graph[EntityState.HELD] == frozenset({EntityState.COMMITTED})
    assert graph[EntityState.COMMITTED] == frozenset({EntityState.RELEASED, EntityState.EXPIRED})
    assert graph[EntityState.RELEASED] == frozenset()
    assert graph[EntityState.EXPIRED] == frozenset()
    # entity-specific fidelity: no foreign edge leaked into this graph
    assert EntityState.SUPERSEDED not in graph[EntityState.COMMITTED]
    assert states.allowed_next_states(EntityState.HELD) == frozenset({EntityState.COMMITTED})


def test_released_is_a_serialized_terminal_state() -> None:
    """``released`` must exist as a state word and must be terminal everywhere it is defined."""
    assert EntityState.RELEASED.value == "released"
    assert json.dumps(EntityState.RELEASED) == '"released"'
    assert json.loads(json.dumps({"reservation_status": EntityState.RELEASED})) == {
        "reservation_status": "released"
    }
    assert EntityState.RELEASED in states.ENTITY_STATE_VALUES
    assert states.allowed_next_states(EntityState.RELEASED) == frozenset()
    assert states.LIFECYCLE_TRANSITIONS["reservation"][EntityState.RELEASED] == frozenset()


def test_committed_reservation_can_be_released_or_expired() -> None:
    graph = states.LIFECYCLE_TRANSITIONS["reservation"]
    for target in (EntityState.RELEASED, EntityState.EXPIRED):
        assert target in graph[EntityState.COMMITTED]
        assert transition(EntityState.COMMITTED, Transition(target)) is target
    assert transition(EntityState.HELD, Transition(EntityState.COMMITTED)) is EntityState.COMMITTED


def test_reservation_unauthorised_and_reverse_edges_are_rejected() -> None:
    graph = states.LIFECYCLE_TRANSITIONS["reservation"]
    unauthorised = [
        (EntityState.RELEASED, EntityState.COMMITTED),
        (EntityState.RELEASED, EntityState.HELD),
        (EntityState.EXPIRED, EntityState.COMMITTED),
        (EntityState.HELD, EntityState.RELEASED),
        (EntityState.HELD, EntityState.EXPIRED),
        (EntityState.HELD, EntityState.CANCELLED),
        (EntityState.COMMITTED, EntityState.CANCELLED),
        (EntityState.COMMITTED, EntityState.HELD),
    ]
    for source, target in unauthorised:
        assert target not in graph.get(source, frozenset()), (source, target)
        with pytest.raises(InvalidTransitionError):
            transition(source, Transition(target))


def test_reservation_graph_drops_cancellation_without_changing_other_entities() -> None:
    """Removing the unauthorised reservation edges must not remove global cancellation."""
    graph = states.LIFECYCLE_TRANSITIONS["reservation"]
    assert EntityState.CANCELLED not in graph
    assert EntityState.CANCELLED not in graph[EntityState.HELD]
    assert EntityState.CANCELLED not in graph[EntityState.COMMITTED]
    # other entities keep their documented cancellation edges
    assert EntityState.CANCELLED in states.LIFECYCLE_TRANSITIONS["order"][EntityState.DRAFT]
    assert EntityState.CANCELLED in states.LIFECYCLE_TRANSITIONS["transport_task"][EntityState.PENDING]
    assert EntityState.CANCELLED in states.LIFECYCLE_TRANSITIONS["job"][EntityState.RUNNING]


# ---------------------------------------------------------------- scalar rules


def test_integer_scalars_reject_bool_float_and_overflow() -> None:
    for bad in (True, False, 1.0, "1", None):
        with pytest.raises(InvalidInputError):
            primitives.require_int(bad, field="value")
    with pytest.raises(InvalidInputError):
        primitives.require_int(2**63, field="value")
    with pytest.raises(InvalidInputError):
        primitives.require_positive_int(0, field="value")
    with pytest.raises(InvalidInputError):
        primitives.require_non_negative_int(-1, field="value")
    assert primitives.require_positive_int(1, field="value") == 1
    assert primitives.require_non_negative_int(0, field="value") == 0


def test_uuid_sha256_and_safe_text_rules() -> None:
    value = uuid4()
    assert primitives.require_uuid(value, field="id") is value
    assert primitives.require_uuid(str(value), field="id") == value
    with pytest.raises(InvalidInputError):
        primitives.require_uuid(str(value).upper(), field="id")
    with pytest.raises(InvalidInputError):
        primitives.require_uuid("not-a-uuid", field="id")

    digest = "a" * 64
    assert primitives.require_sha256(digest, field="hash") == digest
    with pytest.raises(InvalidInputError):
        primitives.require_sha256("A" * 64, field="hash")
    with pytest.raises(InvalidInputError):
        primitives.require_sha256("a" * 63, field="hash")

    assert primitives.require_safe_text("cause", field="reason") == "cause"
    with pytest.raises(InvalidInputError):
        primitives.require_safe_text("", field="reason")
    with pytest.raises(InvalidInputError):
        primitives.require_safe_text("x" * 257, field="reason")


def test_artifact_path_cannot_escape_the_root() -> None:
    assert primitives.require_safe_artifact_path("runs/a.json", field="p") == "runs/a.json"
    for bad in ("", "/abs/a.json", "C:/a.json", "a\\b.json", "../a.json", "a/../b.json", "./a.json", "a//b.json"):
        with pytest.raises(InvalidInputError):
            primitives.require_safe_artifact_path(bad, field="p")


def test_time_window_is_a_closed_start_window() -> None:
    window = TimeWindow(earliest_s=0, latest_s=10)
    assert window.contains_start(0) is True
    assert window.contains_start(10) is True
    assert window.contains_start(11) is False
    assert TimeWindow(earliest_s=5, latest_s=5).contains_start(5) is True
    with pytest.raises(InvalidInputError):
        TimeWindow(earliest_s=6, latest_s=5)
    with pytest.raises(InvalidInputError):
        TimeWindow(earliest_s=-1, latest_s=5)


def test_load_uses_grams_and_cubic_centimetres() -> None:
    load = Load(weight_g=1500, volume_cm3=250)
    assert load + Load(500, 50) == Load(2000, 300)
    assert load - Load(500, 50) == Load(1000, 200)
    with pytest.raises(InvalidInputError):
        Load(weight_g=-1, volume_cm3=1)
    with pytest.raises(InvalidInputError):
        Load(weight_g=1, volume_cm3=-1)
    with pytest.raises(InvalidInputError):
        Load(weight_g=1000, volume_cm3=100) - Load(weight_g=2000, volume_cm3=0)


def test_money_is_an_integer_fen_amount() -> None:
    assert Money(cents=1999).cents == 1999
    assert Money(cents=-500).cents == -500  # deltas are allowed; callers gate non-negativity
    with pytest.raises(InvalidInputError):
        Money(cents=1.5)  # type: ignore[arg-type]
    with pytest.raises(InvalidInputError):
        Money(cents=True)  # type: ignore[arg-type]


def test_rational_is_lowest_terms_and_scales_with_ceiling() -> None:
    assert Rational(numerator=4, denominator=8) == Rational(numerator=1, denominator=2)
    assert Rational(numerator=6, denominator=3) == Rational(numerator=2, denominator=1)
    assert Rational(numerator=3, denominator=2).scale(5) == 8
    assert Rational(numerator=1, denominator=3).scale(3) == 1
    assert Rational(numerator=1, denominator=1).scale(0) == 0
    with pytest.raises(InvalidInputError):
        Rational(numerator=0, denominator=1)
    with pytest.raises(InvalidInputError):
        Rational(numerator=1, denominator=0)
    with pytest.raises(InvalidInputError):
        Rational(numerator=2**62, denominator=1).scale(4)


def test_entity_ref_identity_and_optional_revision() -> None:
    identity = uuid4()
    assert EntityRef(kind=EntityKind.ORDER, id=identity).revision is None
    assert EntityRef(kind=EntityKind.ORDER, id=identity, revision=0).revision == 0
    with pytest.raises(InvalidInputError):
        EntityRef(kind=EntityKind.ORDER, id=identity, revision=-1)
    with pytest.raises(InvalidInputError):
        EntityRef(kind="order", id=identity)  # type: ignore[arg-type]
    with pytest.raises(InvalidInputError):
        EntityRef(kind=EntityKind.ORDER, id="not-a-uuid")  # type: ignore[arg-type]


def test_artifact_ref_requires_all_four_fields() -> None:
    ref = primitives.ArtifactRef(
        id=uuid4(), media_type="application/json", sha256="b" * 64, relative_path="artifacts/a.json"
    )
    assert ref.relative_path == "artifacts/a.json"
    with pytest.raises(InvalidInputError):
        primitives.ArtifactRef(id=uuid4(), media_type="", sha256="b" * 64, relative_path="a.json")
    with pytest.raises(InvalidInputError):
        primitives.ArtifactRef(id=uuid4(), media_type="application/json", sha256="z" * 64, relative_path="a.json")
    with pytest.raises(InvalidInputError):
        primitives.ArtifactRef(
            id=uuid4(), media_type="application/json", sha256="b" * 64, relative_path="../a.json"
        )


def test_domain_values_are_immutable_and_hashable() -> None:
    interval = CalendarInterval(0, 10, 1)
    with pytest.raises(FrozenInstanceError):
        interval.start_s = 5  # type: ignore[misc]
    # Equal value objects collapse in a set/dict key position.
    assert len({interval, CalendarInterval(0, 10, 1)}) == 1
    assert {EntityState.DRAFT: 1}[EntityState.DRAFT] == 1


def test_domain_errors_are_typed() -> None:
    assert issubclass(InvalidInputError, DomainError)
    assert issubclass(InvalidTransitionError, DomainError)
    assert InvalidInputError("x").code is ErrorCode.INVALID_INPUT
    assert InvalidTransitionError(
        state=EntityState.DELIVERED, to_state=EntityState.DRAFT, allowed=frozenset()
    ).code is ErrorCode.INVALID_TRANSITION


def test_transition_placeholder_names_are_not_left_in_the_public_surface() -> None:
    assert not [name for name in dir(states) if name.endswith("_PLACEHOLDER")]
    assert isinstance(EntityState.SUSPENDED, EntityState)
    assert isinstance(EntityState.DEPRECATED, EntityState)


def test_typed_code_names_are_strings_not_invented_vocabularies() -> None:
    # ConstraintCode/ViolationCode carry no frozen member list; P10-01 registers the codes.
    assert states.ConstraintCode("capacity") == "capacity"
    assert states.ViolationCode("capacity") == "capacity"


def test_uuid_scalar_helper_accepts_uuid_objects_returned_by_uuid4() -> None:
    assert isinstance(primitives.require_uuid(uuid4(), field="id"), UUID)
