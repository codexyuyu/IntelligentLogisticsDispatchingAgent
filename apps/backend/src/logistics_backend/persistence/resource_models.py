"""PostgreSQL master-data tables. Payloads are validated entity DTO projections."""
from sqlalchemy import (MetaData, Table, Column, String, BigInteger, DateTime,
                        ForeignKey, UniqueConstraint, CheckConstraint, Index)
from sqlalchemy.dialects.postgresql import UUID, JSONB

metadata = MetaData(naming_convention={"ix": "ix_%(table_name)s_%(column_0_name)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s", "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s", "ck": "ck_%(table_name)s_%(constraint_name)s"})


def entity_table(name, *columns, constraints=()):
    table = Table(name, metadata,
        Column("id", UUID(as_uuid=True), primary_key=True),
        Column("scope_id", UUID(as_uuid=True), nullable=False),
        Column("status", String(32), nullable=False),
        Column("created_at", DateTime(timezone=True), nullable=False),
        Column("updated_at", DateTime(timezone=True), nullable=False),
        Column("created_by", UUID(as_uuid=True), nullable=False),
        Column("row_version", BigInteger, nullable=False),
        Column("schema_version", String(16), nullable=False),
        Column("payload", JSONB(none_as_null=True), nullable=False), *columns,
        CheckConstraint("row_version >= 0", name="revision"),
        CheckConstraint("schema_version = '2.0.0' AND payload->>'schema_version' = schema_version", name="schema"),
        CheckConstraint("updated_at >= created_at", name="timestamps"),
        *constraints)
    Index(f"ix_{name}_page", table.c.scope_id, table.c.created_at, table.c.id)
    return table


drivers = entity_table("drivers", Column("code", String(128), nullable=False),
    constraints=(UniqueConstraint("scope_id", "code"),))
warehouses = entity_table("warehouses", Column("code", String(128), nullable=False),
    constraints=(UniqueConstraint("scope_id", "code"),))
orders = entity_table("orders", Column("external_ref", String(256), nullable=False))
cargo = entity_table("cargo", Column("order_id", UUID(as_uuid=True), ForeignKey("orders.id", ondelete="RESTRICT"), nullable=False),
    Column("quantity_units", BigInteger, nullable=False), Column("weight_g", BigInteger, nullable=False),
    Column("volume_cm3", BigInteger, nullable=False), Column("min_temp_decic", BigInteger, nullable=False),
    Column("max_temp_decic", BigInteger, nullable=False),
    constraints=(CheckConstraint("quantity_units > 0 AND weight_g > 0 AND volume_cm3 > 0", name="positive_cargo"),
                 CheckConstraint("min_temp_decic <= max_temp_decic", name="temperature")))
vehicles = entity_table("vehicles", Column("code", String(128), nullable=False),
    Column("driver_id", UUID(as_uuid=True), ForeignKey("drivers.id", ondelete="RESTRICT")),
    Column("capacity_weight_g", BigInteger, nullable=False), Column("capacity_volume_cm3", BigInteger, nullable=False),
    constraints=(UniqueConstraint("scope_id", "code"),
        CheckConstraint("capacity_weight_g > 0 AND capacity_volume_cm3 > 0", name="capacity")))
zones = entity_table("zones", Column("warehouse_id", UUID(as_uuid=True), ForeignKey("warehouses.id", ondelete="RESTRICT"), nullable=False),
    Column("code", String(128), nullable=False), Column("capacity_weight_g", BigInteger, nullable=False),
    Column("capacity_volume_cm3", BigInteger, nullable=False),
    constraints=(UniqueConstraint("warehouse_id", "code"), CheckConstraint("capacity_weight_g >= 0 AND capacity_volume_cm3 >= 0", name="capacity")))
locations = entity_table("locations", Column("zone_id", UUID(as_uuid=True), ForeignKey("zones.id", ondelete="RESTRICT"), nullable=False),
    Column("code", String(128), nullable=False), Column("capacity_weight_g", BigInteger, nullable=False),
    Column("capacity_volume_cm3", BigInteger, nullable=False),
    constraints=(UniqueConstraint("zone_id", "code"), CheckConstraint("capacity_weight_g >= 0 AND capacity_volume_cm3 >= 0", name="capacity")))
docks = entity_table("docks", Column("warehouse_id", UUID(as_uuid=True), ForeignKey("warehouses.id", ondelete="RESTRICT"), nullable=False),
    Column("code", String(128), nullable=False), constraints=(UniqueConstraint("warehouse_id", "code"),))
workers = entity_table("workers", Column("warehouse_id", UUID(as_uuid=True), ForeignKey("warehouses.id", ondelete="RESTRICT"), nullable=False),
    Column("pool_id", UUID(as_uuid=True)))
equipment = entity_table("equipment", Column("warehouse_id", UUID(as_uuid=True), ForeignKey("warehouses.id", ondelete="RESTRICT"), nullable=False),
    Column("kind", String(32), nullable=False), Column("quantity_capacity", BigInteger, nullable=False),
    constraints=(CheckConstraint("quantity_capacity > 0", name="capacity"),))

TABLES = {"order": orders, "cargo": cargo, "vehicle": vehicles, "driver": drivers,
          "warehouse": warehouses, "zone": zones, "location": locations,
          "dock": docks, "worker": workers, "equipment": equipment}


# Named lifecycle and JSON identity constraints are shared with the domain catalog.
from logistics_domain.states import LIFECYCLE_TRANSITIONS
LIFECYCLE_KEYS = {"zone": "warehouse_zone", "location": "storage_location"}
for kind, table in TABLES.items():
    values = ",".join("'" + state.value + "'" for state in LIFECYCLE_TRANSITIONS[LIFECYCLE_KEYS.get(kind, kind)])
    table.append_constraint(CheckConstraint(f"status IN ({values})", name="entity_status"))
    table.append_constraint(CheckConstraint(
        "payload->>'id' = id::text AND payload->>'status' = status "
        "AND (payload->>'row_version')::bigint = row_version", name="payload_identity"))
