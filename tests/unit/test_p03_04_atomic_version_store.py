"""Unit checks for the pure reservation capacity helper (P03-04, no database)."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from logistics_backend.persistence.reservations import calendar_capacity
from logistics_contracts.entities import CalendarDTO, CalendarIntervalDTO

EPOCH = datetime(2026, 1, 1, tzinfo=timezone.utc)


def _payload(*intervals: CalendarIntervalDTO) -> dict:
    return {"calendar": CalendarDTO(schema_version="2.0.0", epoch_utc=EPOCH,
                                    version=1, intervals=intervals).model_dump(mode="json")}


def test_calendar_capacity_requires_full_coverage() -> None:
    payload = _payload(CalendarIntervalDTO(start_s=0, end_s=60, available_units=1))
    assert calendar_capacity(payload, EPOCH, EPOCH + timedelta(seconds=30)) == 1
    assert calendar_capacity(payload, EPOCH + timedelta(seconds=50),
                             EPOCH + timedelta(seconds=70)) == 0


def test_calendar_capacity_uses_minimum_available_units() -> None:
    payload = _payload(
        CalendarIntervalDTO(start_s=0, end_s=30, available_units=2),
        CalendarIntervalDTO(start_s=30, end_s=60, available_units=1))
    assert calendar_capacity(payload, EPOCH, EPOCH + timedelta(seconds=60)) == 1
