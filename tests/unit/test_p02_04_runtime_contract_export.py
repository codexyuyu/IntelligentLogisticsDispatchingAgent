"""Unit checks for P02-04 event/job runtime values (no database)."""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

import pytest

from logistics_domain.errors import InvalidInputError
from logistics_domain.execution import AtNodeLocation, VehicleFailurePayload
from logistics_domain.primitives import EntityRef
from logistics_domain.runtime import (
    JobCommand,
    MetricJobPayload,
    RequestRef,
    ScenarioSize,
    ScenarioSpec,
)
from logistics_domain.states import (
    CargoCondition,
    EntityKind,
    GenerationPolicy,
    JobKind,
)

EPOCH = datetime(2026, 1, 1, tzinfo=timezone.utc)
HASH = "a" * 64


def test_vehicle_failure_requires_vehicle_id() -> None:
    with pytest.raises(TypeError):
        VehicleFailurePayload(  # type: ignore[call-arg]
            kind="vehicle_failure",
            entity_ref=EntityRef(kind=EntityKind.VEHICLE, id=uuid4(), revision=None),
            effective_at_s=0, reason="engine", location=AtNodeLocation(
                kind="at_node", node_id=uuid4()),
            unavailable_until_s=None, cargo_condition=CargoCondition.INTACT)


def test_job_command_rejects_mismatched_kind_and_family() -> None:
    reference = RequestRef(request_id=uuid4(), version=1, schema_version="2.0.0",
                           hash=HASH, family=JobKind.METRIC)
    payload = MetricJobPayload(family="metric", request_ref=reference)
    with pytest.raises(InvalidInputError):
        JobCommand(schema_version="2.0.0", kind=JobKind.SIMULATION, payload=payload,
                   deadline_utc=EPOCH)


def test_scenario_spec_rejects_event_after_horizon() -> None:
    from logistics_domain.execution import OrderCancellationPayload
    from logistics_domain.runtime import ScenarioEventSpec
    from logistics_domain.states import ReturnPolicy

    order_id = uuid4()
    payload = OrderCancellationPayload(
        kind="order_cancellation",
        entity_ref=EntityRef(kind=EntityKind.ORDER, id=order_id, revision=None),
        effective_at_s=61, reason="cancelled", order_id=order_id,
        disposition_policy=ReturnPolicy.RETURN_TO_ORIGIN)
    with pytest.raises(InvalidInputError):
        ScenarioSpec(
            id=uuid4(), version=1, schema_version="2.0.0", generator_version="1.0.0",
            seed=0, epoch_utc=EPOCH, horizon_s=60,
            size=ScenarioSize(0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0),
            generation_policy=GenerationPolicy.CANONICAL_T1,
            event_specs=(ScenarioEventSpec(event_id=uuid4(), payload=payload),))
