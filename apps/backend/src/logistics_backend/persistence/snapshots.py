"""Read-only consistent planning snapshot capture (P03-03).

One ``REPEATABLE READ`` transaction reads every in-scope entity plus its ``row_version``,
projects absolute resource calendars onto the planning scope window and derives the
inventory position from the append-only ledger. ORM rows never leave this adapter: the
result is a pure :class:`~logistics_domain.planning.PlanningSnapshot` whose hash is
recomputed from canonical content.
"""

from __future__ import annotations

import json
from dataclasses import replace
from uuid import UUID, uuid5

from sqlalchemy import select

from logistics_backend.errors import ServiceError
from logistics_backend.persistence.planning_models import inventory_ledger, travel_matrices
from logistics_backend.persistence.resource_models import TABLES
from logistics_contracts import entities
from logistics_contracts import planning as planning_dto
from logistics_domain import planning
from logistics_domain.primitives import EntityRef
from logistics_domain.resources import (
    ResourceBundle,
    ResourceCalendarBinding,
)
from logistics_domain.states import EntityKind, ErrorCode

#: Namespace for deterministic snapshot ids derived from canonical content.
SNAPSHOT_NAMESPACE = UUID("9c1b64e0-5a5b-5f4e-9a4e-1a0f4a6d0d21")

DTO = {
    "order": entities.OrderDTO, "cargo": entities.CargoDTO, "vehicle": entities.VehicleDTO,
    "driver": entities.DriverDTO, "warehouse": entities.WarehouseDTO, "zone": entities.ZoneDTO,
    "location": entities.StorageLocationDTO, "dock": entities.DockDTO,
    "worker": entities.WorkerDTO, "equipment": entities.EquipmentDTO,
}
ENTITY_KIND = {
    "order": EntityKind.ORDER, "cargo": EntityKind.CARGO, "vehicle": EntityKind.VEHICLE,
    "driver": EntityKind.DRIVER, "warehouse": EntityKind.WAREHOUSE,
    "zone": EntityKind.WAREHOUSE_ZONE, "location": EntityKind.STORAGE_LOCATION,
    "dock": EntityKind.DOCK, "worker": EntityKind.WORKER, "equipment": EntityKind.EQUIPMENT,
}


class PlanningSnapshotStore:
    """Concrete ``PlanningSnapshotStore`` protocol implementation over PostgreSQL."""

    def __init__(self, uow_factory, workspace_id: UUID):
        self.uow_factory = uow_factory
        self.workspace_id = workspace_id

    def _select(self, connection, kind, *, ids=None, where=None):
        table = TABLES[kind]
        statement = select(table).where(table.c.scope_id == self.workspace_id)
        if ids is not None:
            if not ids:
                return []
            statement = statement.where(table.c.id.in_(ids))
        if where is not None:
            statement = statement.where(where)
        return connection.execute(statement.order_by(table.c.id)).mappings().all()

    def _domain(self, kind, row):
        return DTO[kind].model_validate_json(json.dumps(row["payload"])).to_domain()

    def _require_scope_ids(self, found, requested, label):
        found_ids = {row["id"] for row in found}
        missing = set(requested) - found_ids
        if missing:
            raise ServiceError(ErrorCode.NOT_FOUND,
                               f"planning scope references unknown {label}: "
                               f"{sorted(map(str, missing))}")

    def list_matrices(self) -> tuple[planning_dto.TravelMatrixDTO, ...]:
        """Return the deterministic travel matrices visible to this scope."""
        with self.uow_factory() as active:
            rows = active.connection.execute(
                select(travel_matrices).where(travel_matrices.c.scope_id == self.workspace_id)
                .order_by(travel_matrices.c.id, travel_matrices.c.version)).mappings().all()
        return tuple(planning_dto.TravelMatrixDTO.model_validate_json(
            json.dumps(row["payload"])) for row in rows)

    def capture(self, scope: planning.PlanningScope) -> planning.PlanningSnapshot:
        if not isinstance(scope, planning.PlanningScope):
            raise ServiceError(ErrorCode.INVALID_INPUT, "capture expects a PlanningScope")
        with self.uow_factory(isolation="REPEATABLE READ") as active:
            connection = active.connection
            order_rows = self._select(connection, "order", ids=scope.order_ids)
            self._require_scope_ids(order_rows, scope.order_ids, "orders")
            order_ids = [row["id"] for row in order_rows]
            cargo_rows = self._select(connection, "cargo",
                where=TABLES["cargo"].c.order_id.in_(order_ids))
            vehicle_rows = self._select(connection, "vehicle", ids=scope.vehicle_ids)
            self._require_scope_ids(vehicle_rows, scope.vehicle_ids, "vehicles")
            driver_ids = [row["driver_id"] for row in vehicle_rows if row["driver_id"] is not None]
            driver_rows = self._select(connection, "driver", ids=driver_ids)
            warehouse_rows = self._select(connection, "warehouse", ids=scope.warehouse_ids)
            self._require_scope_ids(warehouse_rows, scope.warehouse_ids, "warehouses")
            warehouse_ids = [row["id"] for row in warehouse_rows]
            zone_rows = self._select(connection, "zone",
                where=TABLES["zone"].c.warehouse_id.in_(warehouse_ids))
            zone_ids = [row["id"] for row in zone_rows]
            location_rows = self._select(connection, "location",
                where=TABLES["location"].c.zone_id.in_(zone_ids)) if zone_ids else []
            location_ids = [row["id"] for row in location_rows]
            dock_rows = self._select(connection, "dock",
                where=TABLES["dock"].c.warehouse_id.in_(warehouse_ids))
            worker_rows = self._select(connection, "worker",
                where=TABLES["worker"].c.warehouse_id.in_(warehouse_ids))
            equipment_rows = self._select(connection, "equipment",
                where=TABLES["equipment"].c.warehouse_id.in_(warehouse_ids))
            matrix_rows = connection.execute(
                select(travel_matrices).where(travel_matrices.c.scope_id == self.workspace_id)
                .order_by(travel_matrices.c.id, travel_matrices.c.version)).mappings().all()

            orders = tuple(self._domain("order", row) for row in order_rows)
            cargo = tuple(self._domain("cargo", row) for row in cargo_rows)
            drivers = tuple(self._domain("driver", row) for row in driver_rows)
            vehicles, vehicle_bindings = self._project_group(
                "vehicle", vehicle_rows, scope)
            warehouses, warehouse_bindings = self._project_group(
                "warehouse", warehouse_rows, scope)
            zones = tuple(self._domain("zone", row) for row in zone_rows)
            locations, location_bindings = self._project_group(
                "location", location_rows, scope)
            docks, dock_bindings = self._project_group("dock", dock_rows, scope)
            workers, worker_bindings = self._project_group("worker", worker_rows, scope)
            equipment, equipment_bindings = self._project_group("equipment", equipment_rows, scope)
            inventory = self._inventory(connection, cargo, location_ids)
            revisions = self._revisions((
                ("order", order_rows), ("cargo", cargo_rows), ("vehicle", vehicle_rows),
                ("driver", driver_rows), ("warehouse", warehouse_rows), ("zone", zone_rows),
                ("location", location_rows), ("dock", dock_rows), ("worker", worker_rows),
                ("equipment", equipment_rows),
            ))
            bindings = sorted(
                (*vehicle_bindings, *warehouse_bindings, *location_bindings,
                 *dock_bindings, *worker_bindings, *equipment_bindings),
                key=lambda binding: str(binding.resource_id))
            resources = ResourceBundle(warehouses=warehouses, zones=zones,
                locations=locations, docks=docks, workers=workers, equipment=equipment,
                calendars=tuple(bindings))
            matrices = tuple(planning_dto.TravelMatrixDTO.model_validate_json(
                json.dumps(row["payload"])).to_domain() for row in matrix_rows)

        body = dict(scope=scope, orders=orders, cargo=cargo, vehicles=vehicles, drivers=drivers,
                    resources=resources, inventory=inventory, revisions=revisions,
                    matrices=matrices)
        body_hash = planning.content_hash(body)
        snapshot_id = uuid5(SNAPSHOT_NAMESPACE, body_hash)
        return planning.PlanningSnapshot.create(id=snapshot_id, **body)

    def _project_group(self, kind, rows, scope):
        values, bindings = [], []
        for row in rows:
            value = self._domain(kind, row)
            projected = planning.project_calendar(value.calendar, scope)
            bindings.append(ResourceCalendarBinding(resource_id=value.id,
                source_calendar=value.calendar,
                source_hash=planning.content_hash(value.calendar), calendar=projected))
            values.append(replace(value, calendar=projected))
        return tuple(values), tuple(bindings)

    def _revisions(self, groups):
        revisions: list[planning.ResourceRevision] = []
        for kind, rows in groups:
            for row in rows:
                revisions.append(planning.ResourceRevision(
                    entity_ref=EntityRef(kind=ENTITY_KIND[kind], id=row["id"],
                                         revision=row["row_version"]),
                    row_version=row["row_version"]))
        revisions.sort(key=lambda item: (item.entity_ref.kind.value, str(item.entity_ref.id)))
        return tuple(revisions)

    def _inventory(self, connection, cargo, location_ids):
        cargo_by_id = {item.id: item for item in cargo}
        if not cargo_by_id or not location_ids:
            return ()
        rows = connection.execute(
            select(inventory_ledger.c.cargo_id, inventory_ledger.c.location_id,
                   inventory_ledger.c.quantity_delta)
            .where(inventory_ledger.c.cargo_id.in_(cargo_by_id),
                   inventory_ledger.c.location_id.in_(location_ids),
                   inventory_ledger.c.scope_id == self.workspace_id)).all()
        totals: dict[tuple[UUID, UUID], int] = {}
        for cargo_id, location_id, delta in rows:
            key = (cargo_id, location_id)
            totals[key] = totals.get(key, 0) + int(delta)
        entries: list[planning.InventoryEntry] = []
        for (cargo_id, location_id), quantity in sorted(totals.items(),
                key=lambda item: (str(item[0][0]), str(item[0][1]))):
            if quantity <= 0:
                continue
            item = cargo_by_id[cargo_id]
            weight = item.weight_g * quantity // item.quantity_units
            volume = item.volume_cm3 * quantity // item.quantity_units
            entries.append(planning.InventoryEntry(cargo_id=cargo_id, location_id=location_id,
                quantity_units=quantity, weight_g=weight, volume_cm3=volume))
        return tuple(entries)


__all__ = ["PlanningSnapshotStore", "SNAPSHOT_NAMESPACE"]
