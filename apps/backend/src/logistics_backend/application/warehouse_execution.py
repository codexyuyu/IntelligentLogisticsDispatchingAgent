"""Scope-safe warehouse execution and append-only inventory accounting.

A checked integration run supplies *planned* placement evidence.  Inventory moves only
when an operator explicitly completes the corresponding receive/load task.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Literal
from uuid import UUID, uuid5

from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import func, select, text, update
from sqlalchemy.dialects.postgresql import insert

from logistics_backend.errors import ServiceError
from logistics_backend.persistence.planning_models import inventory_ledger, warehouse_tasks
from logistics_backend.persistence.resource_models import warehouses
from logistics_backend.persistence.scenario_projection import resolve_storage_location
from logistics_contracts.planning import WarehouseTaskDTO
from logistics_domain.states import ErrorCode

LEDGER_NAMESPACE = UUID("4a63e6b8-9b33-4c37-9aa7-18b90929d4c2")
_NEXT = {"pending": "ready", "ready": "running", "running": "completed"}


class TaskTransition(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    schema_version: Literal["2.0.0"] = "2.0.0"
    run_id: UUID
    target_status: Literal["ready", "running", "completed"]
    expected_row_version: int = Field(ge=0)


class WarehouseTaskList(BaseModel):
    schema_version: Literal["2.0.0"] = "2.0.0"
    items: tuple[WarehouseTaskDTO, ...]
    total: int


class InventoryMovement(BaseModel):
    id: UUID
    cargo_id: UUID
    location_id: UUID
    source_location_id: UUID | None = None
    quantity_delta: int
    created_at: datetime
    run_id: UUID | None
    task_id: UUID | None
    operation_kind: str | None


class InventoryPosition(BaseModel):
    cargo_id: UUID
    location_id: UUID
    quantity_units: int


class InventoryView(BaseModel):
    schema_version: Literal["2.0.0"] = "2.0.0"
    items: tuple[InventoryMovement, ...]
    positions: tuple[InventoryPosition, ...]
    total_entries: int
    has_more: bool


def movement_from_checked_run(result, scenario, task_id):
    """Resolve a task to an actual allocation; reject ambiguous batch evidence."""
    if result.get("status") != "checked" or result.get("joint_validation", {}).get("valid") is not True:
        raise ServiceError(ErrorCode.UNVERIFIED_SOLVER_RESULT, "execution requires a checked joint plan")
    tasks = {task.id: task for task in scenario.warehouse_tasks}
    task = tasks.get(task_id)
    if task is None:
        raise ServiceError(ErrorCode.NOT_FOUND, "task absent from run scenario")
    if task.kind.value not in ("receive", "load"):
        return None
    cold = scenario.coldchain_fields or scenario.snapshot.coldchain
    if cold is None:
        raise ServiceError(ErrorCode.UNVERIFIED_SOLVER_RESULT, "coldchain evidence missing")
    matching = [
        occupancy
        for occupancy in cold.occupancies
        if (occupancy.inbound_operation_id if task.kind.value == "receive" else occupancy.outbound_operation_id)
        == task_id
    ]
    if len(matching) != 1:
        raise ServiceError(ErrorCode.UNVERIFIED_SOLVER_RESULT, "task occupancy is not unique")
    occupancy = matching[0]
    cargo = [
        item
        for item in scenario.snapshot.cargo
        if item.batch_ref == occupancy.batch_id and item.order_id == task.order_id
    ]
    allocations = [
        item
        for item in result["warehouse_solution"]["storage_allocations"]
        if item["cargo_id"] == str(occupancy.occupancy_id)
    ]
    if len(cargo) != 1 or len(allocations) != 1:
        raise ServiceError(ErrorCode.UNVERIFIED_SOLVER_RESULT, "cargo or storage allocation is ambiguous")
    allocation = allocations[0]
    # R05 storage intervals may specify capacity by volume only (quantity=0).
    # Ledger quantities always come from the validated cargo master record.
    if allocation["quantity_units"] not in (0, cargo[0].quantity_units):
        raise ServiceError(ErrorCode.UNVERIFIED_SOLVER_RESULT, "allocation quantity differs from cargo")
    amount = cargo[0].quantity_units if task.kind.value == "receive" else -cargo[0].quantity_units
    return cargo[0].id, UUID(allocation["location_id"]), amount


class WarehouseExecutionService:
    def __init__(self, uow_factory, scope_id: UUID, integration):
        self.uow_factory, self.scope_id, self.integration = uow_factory, scope_id, integration

    def _scope(self, actor):
        if actor.scope_id != self.scope_id:
            raise ServiceError(ErrorCode.FORBIDDEN, "scope mismatch")

    def tasks(self, warehouse_id, actor, *, status=None, order_id=None, limit=100):
        self._scope(actor)
        with self.uow_factory() as uow:
            warehouse = uow.connection.execute(
                select(warehouses.c.id).where(warehouses.c.id == warehouse_id, warehouses.c.scope_id == actor.scope_id)
            ).first()
            if warehouse is None:
                raise ServiceError(ErrorCode.NOT_FOUND, "warehouse not found")
            query = select(warehouse_tasks).where(
                warehouse_tasks.c.scope_id == actor.scope_id, warehouse_tasks.c.warehouse_id == warehouse_id
            )
            if status is not None:
                query = query.where(warehouse_tasks.c.status == status)
            if order_id is not None:
                query = query.where(warehouse_tasks.c.order_id == order_id)
            total = uow.connection.execute(select(func.count()).select_from(query.subquery())).scalar_one()
            rows = (
                uow.connection.execute(query.order_by(warehouse_tasks.c.created_at, warehouse_tasks.c.id).limit(limit))
                .mappings()
                .all()
            )
        return WarehouseTaskList(
            items=tuple(WarehouseTaskDTO.model_validate(row["payload"]) for row in rows), total=total
        )

    def inventory(self, actor, *, cargo_id=None, location_id=None, limit=100):
        self._scope(actor)
        conditions = [inventory_ledger.c.scope_id == actor.scope_id]
        if cargo_id is not None:
            conditions.append(inventory_ledger.c.cargo_id == cargo_id)
        if location_id is not None:
            conditions.append(inventory_ledger.c.location_id == location_id)
        query = select(inventory_ledger).where(*conditions)
        with self.uow_factory() as uow:
            total = uow.connection.execute(select(func.count()).select_from(query.subquery())).scalar_one()
            rows = (
                uow.connection.execute(
                    query.order_by(inventory_ledger.c.created_at.desc(), inventory_ledger.c.id).limit(limit)
                )
                .mappings()
                .all()
            )
            positions = uow.connection.execute(
                select(
                    inventory_ledger.c.cargo_id,
                    inventory_ledger.c.location_id,
                    func.sum(inventory_ledger.c.quantity_delta).label("balance"),
                )
                .where(*conditions)
                .group_by(inventory_ledger.c.cargo_id, inventory_ledger.c.location_id)
                .order_by(inventory_ledger.c.cargo_id, inventory_ledger.c.location_id)
            ).all()
        return InventoryView(
            items=tuple(
                InventoryMovement(
                    id=row["id"],
                    cargo_id=row["cargo_id"],
                    location_id=row["location_id"],
                    source_location_id=row["payload"].get("source_location_id"),
                    quantity_delta=row["quantity_delta"],
                    created_at=row["created_at"],
                    run_id=row["payload"].get("run_id"),
                    task_id=row["payload"].get("task_id"),
                    operation_kind=row["payload"].get("operation_kind"),
                )
                for row in rows
            ),
            positions=tuple(
                InventoryPosition(cargo_id=cargo_id, location_id=location_id, quantity_units=balance)
                for cargo_id, location_id, balance in positions
            ),
            total_entries=total,
            has_more=total > len(rows),
        )

    def transition(self, warehouse_id, task_id, command: TaskTransition, actor):
        self._scope(actor)
        result = self.integration.get(command.run_id, actor)
        scenario_id = result.get("request", {}).get("scenario_id")
        if not scenario_id:
            raise ServiceError(ErrorCode.UNVERIFIED_SOLVER_RESULT, "run has no scenario reference")
        scenario = self.integration.scenario(UUID(scenario_id), actor)
        # Verify the run before any write, including intermediate transitions.
        if result.get("status") != "checked" or result.get("joint_validation", {}).get("valid") is not True:
            raise ServiceError(ErrorCode.UNVERIFIED_SOLVER_RESULT, "execution requires a checked joint plan")
        task_by_id = {task.id: task for task in scenario.warehouse_tasks}
        if task_id not in task_by_id or task_by_id[task_id].warehouse_id != warehouse_id:
            raise ServiceError(ErrorCode.NOT_FOUND, "task absent from checked run")
        movement = (
            movement_from_checked_run(result, scenario, task_id) if command.target_status == "completed" else None
        )
        with self.uow_factory() as uow:
            connection = uow.connection
            row = (
                connection.execute(
                    select(warehouse_tasks)
                    .where(
                        warehouse_tasks.c.id == task_id,
                        warehouse_tasks.c.warehouse_id == warehouse_id,
                        warehouse_tasks.c.scope_id == actor.scope_id,
                    )
                    .with_for_update()
                )
                .mappings()
                .first()
            )
            if row is None:
                raise ServiceError(ErrorCode.NOT_FOUND, "warehouse task not found")
            if row["row_version"] != command.expected_row_version:
                raise ServiceError(ErrorCode.STALE_SNAPSHOT, "task revision changed")
            if _NEXT.get(row["status"]) != command.target_status:
                raise ServiceError(ErrorCode.INVALID_TRANSITION, "warehouse task state transition not allowed")
            # The predecessor chain is a business gate, not only a CP-SAT constraint.
            for predecessor_id in task_by_id[task_id].predecessor_ids:
                predecessor = connection.execute(
                    select(warehouse_tasks.c.status).where(
                        warehouse_tasks.c.id == predecessor_id, warehouse_tasks.c.scope_id == actor.scope_id
                    )
                ).scalar_one_or_none()
                if predecessor != "completed":
                    raise ServiceError(ErrorCode.INVALID_TRANSITION, "predecessor has not completed")
            now = datetime.now(UTC).replace(microsecond=0)
            payload = {
                **row["payload"],
                "status": command.target_status,
                "row_version": row["row_version"] + 1,
                "updated_at": now.isoformat(),
            }
            accepted = WarehouseTaskDTO.model_validate(payload)
            connection.execute(
                update(warehouse_tasks)
                .where(warehouse_tasks.c.id == task_id, warehouse_tasks.c.scope_id == actor.scope_id)
                .values(
                    status=command.target_status,
                    updated_at=now,
                    row_version=accepted.row_version,
                    payload=accepted.model_dump(mode="json"),
                )
            )
            if movement is not None:
                cargo_id, source_location_id, delta = movement
                location_id = resolve_storage_location(
                    connection, actor.scope_id, scenario.snapshot, source_location_id
                )
                # Serialize all writes to this stock position, even if multiple
                # independent tasks could target the same cargo/location.
                position_key = uuid5(LEDGER_NAMESPACE, f"{actor.scope_id}:{cargo_id}:{location_id}")
                lock_id = int.from_bytes(position_key.bytes[:8], "big", signed=True)
                connection.execute(text("SELECT pg_advisory_xact_lock(:lock_id)"), {"lock_id": lock_id})
                if delta < 0:
                    current = connection.execute(
                        select(func.coalesce(func.sum(inventory_ledger.c.quantity_delta), 0)).where(
                            inventory_ledger.c.scope_id == actor.scope_id,
                            inventory_ledger.c.cargo_id == cargo_id,
                            inventory_ledger.c.location_id == location_id,
                        )
                    ).scalar_one()
                    if current + delta < 0:
                        raise ServiceError(ErrorCode.RESOURCE_CONFLICT, "insufficient recorded stock for loading")
                identity = uuid5(
                    LEDGER_NAMESPACE, f"{actor.scope_id}:{command.run_id}:{task_id}:{cargo_id}:{location_id}"
                )
                detail = {
                    "schema_version": "2.0.0",
                    "id": str(identity),
                    "cargo_id": str(cargo_id),
                    "location_id": str(location_id),
                    "source_location_id": str(source_location_id),
                    "quantity_delta": delta,
                    "run_id": str(command.run_id),
                    "task_id": str(task_id),
                    "operation_kind": row["kind"],
                    "cause_event_id": None,
                    "version_ref": None,
                }
                connection.execute(
                    insert(inventory_ledger).values(
                        id=identity,
                        scope_id=actor.scope_id,
                        status="recorded",
                        created_at=now,
                        updated_at=now,
                        created_by=actor.actor_id,
                        row_version=0,
                        schema_version="2.0.0",
                        payload=detail,
                        cargo_id=cargo_id,
                        location_id=location_id,
                        quantity_delta=delta,
                        cause_event_id=None,
                        version_ref=None,
                    )
                )
        return accepted
