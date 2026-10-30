"""Project checked scenario facts into FK-backed execution tables.

Imported optimization snapshots are immutable evidence.  Projection never overwrites
existing master-data revisions, and a duplicate id in a *different* scope is given a
scope-local surrogate id rather than being rejected as an ownership conflict.
"""

from __future__ import annotations

from uuid import UUID, uuid5

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert

from logistics_backend.errors import ServiceError
from logistics_backend.persistence.planning_models import warehouse_tasks
from logistics_backend.persistence.resource_models import TABLES, locations, warehouses, zones
from logistics_domain.states import ErrorCode

# Entity tables are keyed by a single surrogate id, yet generated scenarios carry
# deterministic UUIDs: importing the same scenario into a second scope collides on
# that id with the row the first scope owns.  The namespace below derives a stable
# scope-local id for the importing scope, so re-imports stay idempotent and no scope
# can read another scope's master data through a shared UUID.
_SCOPE_SURROGATE_NAMESPACE = UUID("b3f1c0d2-5a4e-4c7b-9d8e-1f2a3b4c5d6e")

# Only catalogued natural keys are aliases. Workers, equipment, orders and cargo
# have no DB business uniqueness constraint and must remain distinct by UUID.
BUSINESS_KEYS = {
    "warehouse": ("scope_id", "code"),
    "driver": ("scope_id", "code"),
    "vehicle": ("scope_id", "code"),
    "zone": ("warehouse_id", "code"),
    "location": ("zone_id", "code"),
    "dock": ("warehouse_id", "code"),
}
PARENT_KEYS = ("warehouse_id", "zone_id", "order_id", "driver_id")


def _master_groups(snapshot):
    resource = snapshot.resources
    # Foreign-key insertion order; do not synthesize missing master facts.
    return (
        ("warehouse", resource.warehouses),
        ("driver", snapshot.drivers),
        ("zone", resource.zones),
        ("location", resource.locations),
        ("dock", resource.docks),
        ("worker", resource.workers),
        ("equipment", resource.equipment),
        ("vehicle", snapshot.vehicles),
        ("order", snapshot.orders),
        ("cargo", snapshot.cargo),
    )


def _common(value, scope_id):
    return {
        "id": value.id,
        "scope_id": scope_id,
        "status": value.status.value,
        "created_at": value.created_at,
        "updated_at": value.updated_at,
        "created_by": value.created_by,
        "row_version": value.row_version,
        "schema_version": value.schema_version,
        "payload": value.model_dump(mode="json"),
    }


def _scope_surrogate_id(scope_id: UUID, entity_id: UUID) -> UUID:
    return uuid5(_SCOPE_SURROGATE_NAMESPACE, f"{scope_id}:{entity_id}")


def _find_existing(connection, table, values, scope_id, business_keys=()):
    """Return the row this scope already owns for `values`, or None.

    A row keyed by the scenario's id but owned by another scope is not this
    scope's entity.  The lookup continues through the scope-local surrogate and
    then the business key, so a second scope importing the same deterministic
    scenario gets its own copy instead of a bogus ownership conflict.  Only a row
    this scope owns can conflict on business identity.
    """
    row = connection.execute(select(table).where(table.c.id == values["id"])).mappings().first()
    if row is not None:
        if row["scope_id"] == scope_id:
            if any(row[name] != values[name] for name in business_keys):
                raise ServiceError(ErrorCode.RESOURCE_CONFLICT, "scenario id has conflicting business identity")
            return row
        surrogate = connection.execute(
            select(table).where(table.c.id == _scope_surrogate_id(scope_id, values["id"]))
        ).mappings().first()
        if surrogate is not None and surrogate["scope_id"] == scope_id:
            return surrogate
    if not business_keys:
        return None
    # Business keys are unique inside one owner: warehouses by (scope, code),
    # zones/docks by (warehouse, code) and locations by (zone, code).  The parent
    # reference has already been aliased to a row this scope owns, and an explicit
    # scope predicate keeps the match from reaching across scopes.
    conditions = [table.c[name] == values[name] for name in business_keys]
    if "scope_id" in table.c:
        conditions.append(table.c.scope_id == scope_id)
    return connection.execute(select(table).where(*conditions)).mappings().first()


def _insert_checked(connection, table, values, scope_id, business_keys=()):
    # Without a conflict target, *both* (id) and domain unique keys may be
    # safely resolved. An unmatched conflict remains a clear resource conflict.
    connection.execute(insert(table).values(**values).on_conflict_do_nothing())
    row = _find_existing(connection, table, values, scope_id, business_keys)
    if row is None:
        # Nothing landed: the scenario id is already owned by another scope and
        # the primary key cannot be reused.  Retry once under this scope's own
        # surrogate id.  (rowcount is -1 under psycopg, so the row itself is the
        # only evidence that an insert took.)
        surrogate = _scope_surrogate_id(scope_id, values["id"])
        values = {
            **values,
            "id": surrogate,
            # Every entity table asserts payload->>'id' = id, so the stored
            # evidence has to agree with the surrogate id it now lives under.
            # Cross-references still resolve through the alias map.
            "payload": {**values["payload"], "id": str(surrogate)},
        }
        connection.execute(insert(table).values(**values).on_conflict_do_nothing())
        row = _find_existing(connection, table, values, scope_id, business_keys)
    if row is None:
        raise ServiceError(ErrorCode.RESOURCE_CONFLICT, "scenario master-data uniqueness conflict")
    return row


def _resolve_parent_refs(values, aliases):
    for name in PARENT_KEYS:
        if name not in values or values[name] is None:
            continue
        canonical = aliases.get(values[name], values[name])
        values[name] = canonical
        if name in values["payload"]:
            values["payload"][name] = str(canonical)
    if "allowed_zone_ids" in values["payload"]:
        values["payload"]["allowed_zone_ids"] = [
            str(aliases.get(UUID(value), UUID(value))) for value in values["payload"]["allowed_zone_ids"]
        ]


def resolve_storage_location(connection, scope_id: UUID, snapshot, source_location_id: UUID) -> UUID:
    """Resolve solver-side location ID to the physical FK used by the ledger.

    A checked run retains the original scenario UUIDs. The master projection may
    reuse a previously seeded location with the same (zone, code) business key.
    """
    try:
        source_location = next(v for v in snapshot.resources.locations if v.id == source_location_id)
        source_zone = next(v for v in snapshot.resources.zones if v.id == source_location.zone_id)
        source_warehouse = next(v for v in snapshot.resources.warehouses if v.id == source_zone.warehouse_id)
    except StopIteration as exc:
        raise ServiceError(ErrorCode.UNVERIFIED_SOLVER_RESULT, "storage location lacks master evidence") from exc

    warehouse = _find_existing(
        connection,
        warehouses,
        {"id": source_warehouse.id, "scope_id": scope_id, "code": source_warehouse.code},
        scope_id,
        BUSINESS_KEYS["warehouse"],
    )
    if warehouse is None:
        raise ServiceError(ErrorCode.NOT_FOUND, "projected warehouse not found")
    zone = _find_existing(
        connection,
        zones,
        {"id": source_zone.id, "warehouse_id": warehouse["id"], "code": source_zone.code},
        scope_id,
        BUSINESS_KEYS["zone"],
    )
    if zone is None:
        raise ServiceError(ErrorCode.NOT_FOUND, "projected storage zone not found")
    location = _find_existing(
        connection,
        locations,
        {"id": source_location.id, "zone_id": zone["id"], "code": source_location.code},
        scope_id,
        BUSINESS_KEYS["location"],
    )
    if location is None:
        raise ServiceError(ErrorCode.NOT_FOUND, "projected storage location not found")
    return location["id"]


def project_checked_scenario(connection, scope_id: UUID, command) -> None:
    """Idempotent single-transaction insertion; caller commits alongside scenario row."""
    aliases: dict[UUID, UUID] = {}
    for kind, items in _master_groups(command.snapshot):
        table = TABLES[kind]
        for item in items:
            values = _common(item, scope_id)
            for column in table.c:
                if column.name not in values:
                    values[column.name] = getattr(item, column.name)
            _resolve_parent_refs(values, aliases)
            # Existing master data is never overwritten; the snapshot retains
            # its own UUIDs and the execution projection resolves canonical IDs.
            row = _insert_checked(connection, table, values, scope_id, BUSINESS_KEYS.get(kind, ()))
            aliases[item.id] = row["id"]

    for task in command.warehouse_tasks:
        values = _common(task, scope_id)
        values.update(
            order_id=aliases.get(task.order_id, task.order_id),
            warehouse_id=aliases.get(task.warehouse_id, task.warehouse_id),
            kind=task.kind.value,
            duration_s=task.duration_s,
            setup_class=task.setup_class,
        )
        _resolve_parent_refs(values, aliases)
        for requirement in values["payload"]["requirements"]:
            requirement["eligible_ids"] = [
                str(aliases.get(UUID(value), UUID(value))) for value in requirement["eligible_ids"]
            ]
        row = _insert_checked(connection, warehouse_tasks, values, scope_id)
        original = row["payload"]
        supplied = values["payload"]
        # A repeated import must not silently redefine a task already being executed.
        for field in (
            "order_id",
            "warehouse_id",
            "kind",
            "duration_s",
            "setup_class",
            "window",
            "predecessor_ids",
            "requirements",
            "required_skills",
        ):
            if original.get(field) != supplied.get(field):
                raise ServiceError(ErrorCode.RESOURCE_CONFLICT, f"warehouse task {task.id} has conflicting evidence")
