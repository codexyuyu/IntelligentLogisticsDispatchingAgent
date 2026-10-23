"""Transactional master-data CRUD with optimistic revision and stable cursors."""
import base64
import hashlib
import json
from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy import select, insert, update, tuple_
from pydantic import BaseModel
from logistics_contracts import entities, http
from logistics_domain.errors import DomainError
from logistics_domain.states import ErrorCode


class ServiceError(DomainError):
    def __init__(self, code: ErrorCode, message: str, status: int | None = None):
        super().__init__(message)
        self.code = code
        self.status = status


PagePosition = http.PagePosition

DTO = {"order": entities.OrderDTO, "cargo": entities.CargoDTO, "vehicle": entities.VehicleDTO,
       "driver": entities.DriverDTO, "warehouse": entities.WarehouseDTO, "zone": entities.ZoneDTO,
       "location": entities.StorageLocationDTO, "dock": entities.DockDTO,
       "worker": entities.WorkerDTO, "equipment": entities.EquipmentDTO}
PAGES = {"order": http.OrderPage, "vehicle": http.VehiclePage, "driver": http.DriverPage,
         "warehouse": http.WarehousePage, "zone": http.ZonePage, "location": http.LocationPage,
         "dock": http.DockPage, "worker": http.WorkerPage, "equipment": http.EquipmentPage}
INITIAL = {"order": "draft", "cargo": "registered", "driver": "active", "warehouse": "active",
           "zone": "active", "vehicle": "available", "location": "available", "dock": "available",
           "worker": "available", "equipment": "available"}


class MasterDataService:
    def __init__(self, uow_factory, tables):
        self.uow_factory = uow_factory
        self.tables = tables

    def _row(self, connection, kind, entity_id, scope_id, lock=False):
        table = self.tables[kind]
        query = select(table).where(table.c.id == entity_id, table.c.scope_id == scope_id)
        if lock:
            query = query.with_for_update()
        row = connection.execute(query).mappings().first()
        if row is None:
            raise ServiceError(ErrorCode.NOT_FOUND, "entity not found")
        return row

    def get(self, kind, entity_id, actor):
        with self.uow_factory() as uow:
            return DTO[kind].model_validate_json(json.dumps(self._row(uow.connection, kind, entity_id, actor.scope_id)["payload"]))

    def _relations(self, connection, kind, value, scope_id, warehouse_id=None):
        if kind == "vehicle" and value.driver_id is not None:
            self._row(connection, "driver", value.driver_id, scope_id)
        if kind in ("zone", "dock", "worker", "equipment"):
            self._row(connection, "warehouse", value.warehouse_id, scope_id)
            if warehouse_id is not None and value.warehouse_id != warehouse_id:
                raise ServiceError(ErrorCode.INVALID_INPUT, "warehouse mismatch")
        if kind == "location":
            zone = self._row(connection, "zone", value.zone_id, scope_id)
            if warehouse_id is not None and zone["warehouse_id"] != warehouse_id:
                raise ServiceError(ErrorCode.INVALID_INPUT, "zone outside warehouse")
        for zone_id in getattr(value, "allowed_zone_ids", ()):
            zone = self._row(connection, "zone", zone_id, scope_id)
            if zone["warehouse_id"] != value.warehouse_id:
                raise ServiceError(ErrorCode.INVALID_INPUT, "zone outside warehouse")

    def _values(self, kind, value, scope_id):
        values = {"scope_id": scope_id, "payload": value.model_dump(mode="json")}
        for column in self.tables[kind].c:
            if column.name not in values:
                values[column.name] = getattr(value, column.name)
        return values

    def create(self, kind, command, actor, warehouse_id=None):
        now = datetime.now(timezone.utc).replace(microsecond=0)
        data = command.model_dump(mode="python")
        cargo_data = data.pop("cargo", ())
        data.update(id=uuid4(), status=INITIAL[kind], created_at=now, updated_at=now,
                    created_by=actor.actor_id, row_version=0)
        if kind in ("zone", "dock", "worker", "equipment"):
            data["warehouse_id"] = warehouse_id
        cargo_ids = tuple(uuid4() for _ in cargo_data)
        if kind == "order":
            data["cargo_ids"] = cargo_ids
        value = DTO[kind].model_validate_json(json.dumps(data, default=str))
        with self.uow_factory() as uow:
            self._relations(uow.connection, kind, value, actor.scope_id, warehouse_id)
            uow.connection.execute(insert(self.tables[kind]).values(**self._values(kind, value, actor.scope_id)))
            for cargo_id, item in zip(cargo_ids, cargo_data):
                cargo = entities.CargoDTO.model_validate({**item, "id": cargo_id, "order_id": value.id,
                    "status": "registered", "created_at": now, "updated_at": now,
                    "created_by": actor.actor_id, "row_version": 0, "schema_version": "2.0.0"})
                uow.connection.execute(insert(self.tables["cargo"]).values(**self._values("cargo", cargo, actor.scope_id)))
        return value

    def update(self, kind, entity_id, changes, expected_revision, actor):
        with self.uow_factory() as uow:
            row = self._row(uow.connection, kind, entity_id, actor.scope_id, lock=True)
            if row["row_version"] != expected_revision:
                raise ServiceError(ErrorCode.STALE_SNAPSHOT, "row revision changed")
            if kind == "order" and row["status"] != "draft":
                raise ServiceError(ErrorCode.INVALID_TRANSITION, "only draft order demand can be edited")
            patch = changes.model_dump(mode="json", exclude_unset=True, exclude={"schema_version"})
            value = DTO[kind].model_validate_json(json.dumps({**row["payload"], **patch,
                "updated_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
                "row_version": expected_revision + 1}))
            self._relations(uow.connection, kind, value, actor.scope_id)
            table = self.tables[kind]
            result = uow.connection.execute(update(table).where(table.c.id == entity_id,
                table.c.scope_id == actor.scope_id, table.c.row_version == expected_revision)
                .values(**self._values(kind, value, actor.scope_id)))
            if result.rowcount != 1:
                raise ServiceError(ErrorCode.STALE_SNAPSHOT, "row revision changed")
            return value

    def put_calendar(self, kind, entity_id, calendar, expected_revision, actor):
        if kind not in ("location", "dock", "worker", "equipment"):
            raise ServiceError(ErrorCode.INVALID_INPUT, "resource has no editable calendar")
        # N02-F03: If-Match pins the row and DTO.version must equal the current calendar
        # version; the accepted write produces calendar.version+1 and row_version+1.
        with self.uow_factory() as uow:
            row = self._row(uow.connection, kind, entity_id, actor.scope_id, lock=True)
            current = entities.CalendarDTO.model_validate(row["payload"]["calendar"])
            if (row["row_version"] != expected_revision or calendar.version != current.version
                    or calendar.epoch_utc != current.epoch_utc):
                raise ServiceError(ErrorCode.STALE_SNAPSHOT,
                                   "calendar version or row revision changed")
        next_calendar = entities.CalendarDTO(schema_version="2.0.0", epoch_utc=current.epoch_utc,
            version=current.version + 1, intervals=calendar.intervals)

        class CalendarChange(BaseModel):
            calendar: entities.CalendarDTO
        return self.update(kind, entity_id, CalendarChange(calendar=next_calendar), expected_revision, actor)

    def list(self, kind, query, actor, warehouse_id=None):
        filters = query.model_dump(mode="json", exclude={"cursor", "limit"}, exclude_none=True)
        filter_hash = hashlib.sha256(json.dumps({"filters": filters, "warehouse_id": str(warehouse_id)}, sort_keys=True).encode()).hexdigest()
        table = self.tables[kind]
        statement = select(table).where(table.c.scope_id == actor.scope_id)
        for key, value in filters.items():
            statement = statement.where(table.c.payload[key].astext == str(value))
        if warehouse_id is not None:
            if kind == "location":
                zones = self.tables["zone"]
                statement = statement.where(table.c.zone_id.in_(select(zones.c.id).where(zones.c.warehouse_id == warehouse_id, zones.c.scope_id == actor.scope_id)))
            else:
                statement = statement.where(table.c.warehouse_id == warehouse_id)
        if query.cursor:
            try:
                position = PagePosition.model_validate_json(base64.urlsafe_b64decode(query.cursor + "=" * (-len(query.cursor) % 4)))
            except (ValueError, TypeError) as exc:
                raise ServiceError(ErrorCode.INVALID_INPUT, "invalid cursor") from exc
            if (position.scope_id != actor.scope_id
                    or position.entity_kind.value != kind or position.filter_hash != filter_hash):
                raise ServiceError(ErrorCode.INVALID_INPUT, "cursor does not match query")
            statement = statement.where(tuple_(table.c.created_at, table.c.id)
                > tuple_(position.after_created_at, position.after_id))
        with self.uow_factory() as uow:
            if warehouse_id is not None:
                self._row(uow.connection, "warehouse", warehouse_id, actor.scope_id)
            rows = uow.connection.execute(statement.order_by(table.c.created_at, table.c.id).limit(query.limit + 1)).mappings().all()
        has_more = len(rows) > query.limit
        rows = rows[:query.limit]
        cursor = None
        if has_more:
            position = PagePosition(version=1, scope_id=actor.scope_id, entity_kind=kind,
                filter_hash=filter_hash, after_created_at=rows[-1]["created_at"], after_id=rows[-1]["id"])
            cursor = base64.urlsafe_b64encode(position.model_dump_json().encode()).decode().rstrip("=")
        return PAGES[kind](schema_version="2.0.0", items=tuple(DTO[kind].model_validate_json(json.dumps(r["payload"])) for r in rows), next_cursor=cursor, has_more=has_more)
