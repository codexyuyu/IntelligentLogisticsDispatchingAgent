"""事件契约测试：证明工具读取的载荷是契约允许的，而不是自造的。

背景：早先的实现使用 ``kind="vehicle_delay"``，但 ``EventKind`` 没有这个取值，
``POST /events`` 永远产生不出它——集成测试用手工 dict 绕过了契约，属假通过。
本文件把契约边界钉死。
"""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

import pytest

from logistics_domain.errors import InvalidInputError
from logistics_domain.execution import EventKind, TransportDelayPayload
from logistics_domain.events import EventEnvelope
from logistics_domain.primitives import EntityRef
from logistics_domain.states import EntityKind

OCCURRED_AT = datetime(2026, 1, 1, 0, 0, 0, tzinfo=UTC)


def _payload(*, task_id=None, additional_seconds: int = 60, effective_at_s: int = 0):
    task_id = task_id or uuid4()
    return TransportDelayPayload(
        kind="transport_delay",
        entity_ref=EntityRef(kind=EntityKind.TRANSPORT_TASK, id=task_id),
        effective_at_s=effective_at_s,
        reason="vehicle held at gate",
        transport_task_id=task_id,
        additional_seconds=additional_seconds,
    )


def _envelope(payload) -> EventEnvelope:
    return EventEnvelope(
        schema_version="2.0.0",
        source="operator-ui",
        source_event_id=f"evt-{uuid4().hex[:8]}",
        kind=EventKind.TRANSPORT_DELAY,
        occurred_at_utc=OCCURRED_AT,
        simulation_id=None,
        payload=payload,
    )


def test_transport_delay_is_a_legal_event_kind():
    assert EventKind("transport_delay") is EventKind.TRANSPORT_DELAY


def test_vehicle_delay_is_not_a_legal_event_kind():
    """旧实现用的取值不在枚举里——这正是它在真实入口不可达的原因。"""

    with pytest.raises(ValueError):
        EventKind("vehicle_delay")


def test_transport_delay_payload_and_envelope_construct():
    payload = _payload()
    envelope = _envelope(payload)
    assert envelope.kind is EventKind.TRANSPORT_DELAY
    assert envelope.payload.additional_seconds == 60
    assert envelope.payload.transport_task_id == envelope.payload.entity_ref.id


def test_payload_rejects_non_positive_delay():
    with pytest.raises(InvalidInputError):
        _payload(additional_seconds=0)


def test_payload_rejects_entity_ref_mismatch():
    """entity_ref 必须就是那个运输任务，否则事件指向不明。"""

    with pytest.raises(InvalidInputError):
        TransportDelayPayload(
            kind="transport_delay",
            entity_ref=EntityRef(kind=EntityKind.TRANSPORT_TASK, id=uuid4()),
            effective_at_s=0,
            reason="mismatch",
            transport_task_id=uuid4(),
            additional_seconds=30,
        )


def test_envelope_rejects_unknown_kind():
    from logistics_domain.events import EventEnvelope as Envelope

    with pytest.raises(InvalidInputError):
        Envelope(
            schema_version="2.0.0",
            source="operator-ui",
            source_event_id="evt-bad",
            kind="vehicle_delay",  # type: ignore[arg-type]
            occurred_at_utc=OCCURRED_AT,
            simulation_id=None,
            payload=_payload(),
        )


def test_tool_reads_the_same_field_names_as_the_contract():
    """工具读取的键必须与 TransportDelayPayload 的字段名一致，防止再次漂移。"""

    from dataclasses import fields

    names = {f.name for f in fields(TransportDelayPayload)}
    assert {"transport_task_id", "additional_seconds", "effective_at_s"} <= names
    # 旧实现对外的字段名已不再使用，避免有人按旧格式回归
    assert "vehicle_id" not in names
    assert "delay_s" not in names
    assert "event_time_s" not in names
