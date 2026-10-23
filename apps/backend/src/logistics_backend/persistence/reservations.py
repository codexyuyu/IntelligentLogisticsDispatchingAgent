"""Resource reservation checks and append-only reservation rows (P03-04).

The caller locks the schedule row first; this module then locks every referenced resource
row in ascending UUID order, re-checks the calendar capacity and the sum of overlapping
``held``/``committed`` reservations, and only then inserts the new reservations. Two
commits that compete for the last dock therefore serialize instead of both succeeding.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from uuid import UUID, uuid4

from sqlalchemy import select, insert

from logistics_backend.errors import ServiceError
from logistics_backend.persistence.planning_models import reservations
from logistics_backend.persistence.resource_models import TABLES
from logistics_contracts.entities import CalendarDTO
from logistics_domain.planning import ScheduleTask
from logistics_domain.states import ErrorCode

RESOURCE_TABLES = {
    "zone": TABLES["zone"], "location": TABLES["location"], "dock": TABLES["dock"],
    "worker": TABLES["worker"], "equipment": TABLES["equipment"],
}
# Vehicles/drivers are locked in the same fixed order but their exclusivity is expressed by
# the route assignment, not by a warehouse reservation row.
TRANSPORT_TABLES = {"vehicle": TABLES["vehicle"], "driver": TABLES["driver"]}
LOCKED_TABLES = {**RESOURCE_TABLES, **TRANSPORT_TABLES}
EXCLUSIVE_KINDS = frozenset({"location", "dock", "worker"})


def _absolute(epoch: datetime, offset_s: int) -> datetime:
    return epoch + timedelta(seconds=offset_s)


def calendar_capacity(payload, start_utc: datetime, end_utc: datetime) -> int:
    """Minimum available units over the fully covered absolute interval; 0 when uncovered."""
    calendar = CalendarDTO.model_validate(payload["calendar"]).to_domain()
    covered_from = start_utc
    units: list[int] = []
    for interval in calendar.intervals:
        interval_start = _absolute(calendar.epoch_utc, interval.start_s)
        interval_end = _absolute(calendar.epoch_utc, interval.end_s)
        if interval_end <= start_utc or interval_start >= end_utc:
            continue
        start = max(interval_start, start_utc)
        end = min(interval_end, end_utc)
        if start > covered_from:
            return 0
        if end > covered_from:
            covered_from = end
        units.append(interval.available_units)
    if covered_from < end_utc or not units:
        return 0
    return min(units)


def resource_capacity(kind: str, row) -> int:
    capacity = 1 if kind in EXCLUSIVE_KINDS or kind == "zone" else int(
        row["payload"].get("quantity_capacity", 1))
    return max(0, capacity)


class ReservationStore:
    def lock_resources(self, connection, workspace_id: UUID, resource_ids):
        locked = {}
        for resource_id in sorted(set(resource_ids), key=str):
            found = None
            for kind, table in LOCKED_TABLES.items():
                row = connection.execute(select(table).where(
                    table.c.id == resource_id, table.c.scope_id == workspace_id)
                    .with_for_update()).mappings().first()
                if row is not None:
                    found = (kind, row)
                    break
            if found is None:
                raise ServiceError(ErrorCode.RESOURCE_CONFLICT,
                                   f"reserved resource {resource_id} is not in this scope")
            locked[resource_id] = found
        return locked

    def _used(self, connection, workspace_id, resource_id, start_utc, end_utc) -> int:
        rows = connection.execute(select(reservations.c.epoch_utc, reservations.c.start_s,
                                         reservations.c.end_s, reservations.c.quantity)
            .where(reservations.c.scope_id == workspace_id,
                   reservations.c.resource_id == resource_id,
                   reservations.c.status.in_(("held", "committed")),
                   reservations.c.expires_at_utc > datetime.now(timezone.utc))).all()
        used = 0
        for epoch, row_start_s, row_end_s, quantity in rows:
            row_start = _absolute(epoch, int(row_start_s))
            row_end = _absolute(epoch, int(row_end_s))
            if row_start < end_utc and start_utc < row_end:
                used += int(quantity)
        return used

    def assert_and_reserve(self, connection, *, workspace_id: UUID, schedule_epoch: datetime,
                           assignments, version_id: UUID, actor_id: UUID,
                           now: datetime, expires_at: datetime) -> int:
        requested = []
        for assignment in assignments:
            if not isinstance(assignment, ScheduleTask):
                raise ServiceError(ErrorCode.INVALID_INPUT, "reservation expects ScheduleTask values")
            for resource_id in assignment.assigned_resource_ids:
                requested.append((resource_id, _absolute(schedule_epoch, assignment.planned_start_s),
                                  _absolute(schedule_epoch, assignment.planned_end_s)))
        locked = self.lock_resources(connection, workspace_id,
                                     [item[0] for item in requested])
        inserted = 0
        for resource_id, start_utc, end_utc in requested:
            kind, row = locked[resource_id]
            if kind in TRANSPORT_TABLES:
                # The route document is the exclusive vehicle/driver assignment; the row
                # lock above still serializes concurrent commits that touch it.
                continue
            if kind == "zone":
                # Zones carry weight/volume capacities, not an editable calendar; a
                # reservation on a zone is an exclusive occupancy of the zone itself.
                capacity = 1
            else:
                capacity = min(resource_capacity(kind, row),
                               calendar_capacity(row["payload"], start_utc, end_utc))
            # Own uncommitted inserts are visible to this transaction, so the overlap sum
            # already includes earlier reservations created by this same commit.
            used = self._used(connection, workspace_id, resource_id, start_utc, end_utc)
            if used + 1 > capacity:
                raise ServiceError(ErrorCode.RESOURCE_CONFLICT,
                                   f"resource {resource_id} has no remaining capacity")
            reservation_id = uuid4()
            start_s = int((start_utc - schedule_epoch).total_seconds())
            end_s = int((end_utc - schedule_epoch).total_seconds())
            payload = {
                "id": str(reservation_id), "status": "held", "schema_version": "2.0.0",
                "row_version": 0, "created_at": now.isoformat().replace("+00:00", "Z"),
                "updated_at": now.isoformat().replace("+00:00", "Z"),
                "created_by": str(actor_id), "resource_kind": kind,
                "resource_id": str(resource_id), "start_s": start_s, "end_s": end_s,
                "quantity": 1, "version_id": str(version_id),
                "expires_at_utc": expires_at.isoformat().replace("+00:00", "Z"),
            }
            connection.execute(insert(reservations).values(
                id=reservation_id, scope_id=workspace_id, status="held", row_version=0,
                created_at=now, updated_at=now, created_by=actor_id, schema_version="2.0.0",
                payload=payload, resource_kind=kind, resource_id=resource_id,
                start_s=start_s, end_s=end_s, quantity=1, version_id=version_id,
                epoch_utc=schedule_epoch, expires_at_utc=expires_at))
            inserted += 1
        return inserted


def utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(microsecond=0)


__all__ = ["ReservationStore", "calendar_capacity", "resource_capacity", "utcnow"]
