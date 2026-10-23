"""PostgreSQL mappings for planning versions, tasks, inventory, audit and outbox.

The frozen migration ``0002_planning_runtime`` is generated from these definitions once and
then kept immutable. Relations and concurrency keys (schedule/version/task/resource ids,
statuses, hashes, counters) are real columns so they can be constrained, locked and indexed;
the versioned JSONB payload holds the typed DTO projection and repeats schema_version. No
ORM session is exposed outside this adapter package.
"""

from __future__ import annotations

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    Column,
    DateTime,
    ForeignKey,
    Index,
    String,
    Table,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID

from logistics_backend.persistence.resource_models import metadata
from logistics_domain.states import LIFECYCLE_TRANSITIONS


def _status_values(lifecycle: str) -> str:
    return ",".join("'" + state.value + "'" for state in LIFECYCLE_TRANSITIONS[lifecycle])


def entity_table(name: str, *columns, lifecycle: str | None = None,
                 statuses: str | None = None, constraints=()):
    """One append/update entity table with the frozen common columns."""
    if lifecycle is not None:
        statuses = _status_values(lifecycle)
    if statuses is None:
        raise ValueError(f"{name} needs a lifecycle or explicit status list")
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
        CheckConstraint("schema_version = '2.0.0' AND payload->>'schema_version' = schema_version",
                        name="schema"),
        CheckConstraint("updated_at >= created_at", name="timestamps"),
        CheckConstraint(f"status IN ({statuses})", name="status"),
        CheckConstraint("payload->>'id' = id::text AND payload->>'status' = status "
                        "AND (payload->>'row_version')::bigint = row_version",
                        name="payload_identity"),
        *constraints)
    Index(f"ix_{name}_page", table.c.scope_id, table.c.created_at, table.c.id)
    return table


# ---------------------------------------------------------------- planning versions

planning_snapshots = Table("planning_snapshots", metadata,
    Column("id", UUID(as_uuid=True), primary_key=True),
    Column("scope_id", UUID(as_uuid=True), nullable=False),
    Column("scope_hash", String(64), nullable=False),
    Column("content_hash", String(64), nullable=False),
    Column("status", String(32), nullable=False),
    Column("created_at", DateTime(timezone=True), nullable=False),
    Column("updated_at", DateTime(timezone=True), nullable=False),
    Column("created_by", UUID(as_uuid=True), nullable=False),
    Column("row_version", BigInteger, nullable=False),
    Column("schema_version", String(16), nullable=False),
    Column("payload", JSONB(none_as_null=True), nullable=False),
    CheckConstraint("status = 'recorded' AND row_version = 0", name="record"),
    CheckConstraint("created_at = updated_at", name="times"),
    CheckConstraint("schema_version = '2.0.0'", name="schema"),
    CheckConstraint("payload->>'id' = id::text AND payload->>'hash' = content_hash",
                    name="identity"),
    Index("ix_planning_snapshots_scope", "scope_id", "created_at", "id"),
    Index("ix_planning_snapshots_hash", "scope_id", "content_hash"))

schedules = entity_table("schedules", Column("name", String(128), nullable=False),
    # CAS pointer; the FK is added by migration 0002 after schedule_versions exists.
    Column("active_version_id", UUID(as_uuid=True)),
    Column("epoch_utc", DateTime(timezone=True), nullable=False),
    Column("horizon_s", BigInteger, nullable=False), lifecycle="schedule",
    constraints=(UniqueConstraint("scope_id", "name", name="uq_schedules_scope_name"),
                 CheckConstraint("horizon_s > 0 AND horizon_s <= 604800", name="horizon")))

schedule_versions = entity_table("schedule_versions",
    Column("schedule_id", UUID(as_uuid=True), ForeignKey("schedules.id", ondelete="RESTRICT"),
           nullable=False),
    Column("version_no", BigInteger, nullable=False),
    Column("parent_version_id", UUID(as_uuid=True),
           ForeignKey("schedule_versions.id", ondelete="RESTRICT")),
    Column("snapshot_id", UUID(as_uuid=True),
           ForeignKey("planning_snapshots.id", ondelete="RESTRICT"), nullable=False),
    Column("content_hash", String(64), nullable=False),
    Column("reason", String(64), nullable=False),
    Column("event_id", UUID(as_uuid=True)),
    Column("validation_report_ref", UUID(as_uuid=True), nullable=False),
    lifecycle="schedule_version",
    constraints=(UniqueConstraint("schedule_id", "version_no", name="uq_schedule_versions_number"),
                 CheckConstraint("version_no > 0", name="positive_version"),
                 CheckConstraint("parent_version_id IS NULL OR parent_version_id <> id",
                                 name="parent_not_self")))
Index("ix_schedule_versions_parent", schedule_versions.c.parent_version_id)
Index("ix_schedule_versions_schedule", schedule_versions.c.schedule_id, schedule_versions.c.version_no)

schedule_tasks = entity_table("schedule_tasks",
    Column("version_id", UUID(as_uuid=True),
           ForeignKey("schedule_versions.id", ondelete="RESTRICT"), nullable=False),
    Column("task_id", UUID(as_uuid=True), nullable=False),
    Column("task_kind", String(32), nullable=False),
    Column("planned_start_s", BigInteger, nullable=False),
    Column("planned_end_s", BigInteger, nullable=False),
    Column("sequence", BigInteger),
    lifecycle="schedule_task",
    constraints=(UniqueConstraint("version_id", "task_id", name="uq_schedule_tasks_version_task"),
                 CheckConstraint("planned_start_s >= 0 AND planned_end_s > planned_start_s",
                                 name="task_interval"),
                 CheckConstraint("task_kind IN ('transport_task','warehouse_task')",
                                 name="task_kind")))
Index("ix_schedule_tasks_task", schedule_tasks.c.task_id)

# ------------------------------------------------------------------ planning tasks

transport_tasks = entity_table("transport_tasks",
    Column("order_id", UUID(as_uuid=True), ForeignKey("orders.id", ondelete="RESTRICT"), nullable=False),
    Column("leg_no", BigInteger, nullable=False),
    Column("pickup_node_id", UUID(as_uuid=True), nullable=False),
    Column("delivery_node_id", UUID(as_uuid=True), nullable=False),
    Column("service_s", BigInteger, nullable=False),
    lifecycle="transport_task",
    constraints=(CheckConstraint("leg_no > 0 AND service_s >= 0", name="task_values")))

warehouse_tasks = entity_table("warehouse_tasks",
    Column("order_id", UUID(as_uuid=True), ForeignKey("orders.id", ondelete="RESTRICT")),
    Column("warehouse_id", UUID(as_uuid=True), ForeignKey("warehouses.id", ondelete="RESTRICT"),
           nullable=False),
    Column("kind", String(32), nullable=False),
    Column("duration_s", BigInteger, nullable=False),
    Column("setup_class", String(128), nullable=False),
    lifecycle="warehouse_task",
    constraints=(CheckConstraint("duration_s >= 0", name="task_duration"),
                 CheckConstraint("kind IN ('receive','dispatch','sort','load','unload','setup')",
                                 name="operation_kind")))

routes = entity_table("routes",
    Column("version_id", UUID(as_uuid=True),
           ForeignKey("schedule_versions.id", ondelete="RESTRICT"), nullable=False),
    Column("vehicle_id", UUID(as_uuid=True), ForeignKey("vehicles.id", ondelete="RESTRICT"),
           nullable=False),
    Column("driver_id", UUID(as_uuid=True), ForeignKey("drivers.id", ondelete="RESTRICT"),
           nullable=False),
    Column("start_node_id", UUID(as_uuid=True), nullable=False),
    Column("end_node_id", UUID(as_uuid=True), nullable=False),
    Column("total_distance_m", BigInteger, nullable=False),
    Column("matrix_id", UUID(as_uuid=True), nullable=False),
    Column("matrix_version", BigInteger, nullable=False),
    lifecycle="route",
    constraints=(CheckConstraint("total_distance_m >= 0 AND matrix_version > 0",
                                 name="route_values")))
Index("ix_routes_version", routes.c.version_id)

route_stops = entity_table("route_stops",
    Column("route_id", UUID(as_uuid=True), ForeignKey("routes.id", ondelete="RESTRICT"),
           nullable=False),
    Column("sequence", BigInteger, nullable=False),
    Column("node_id", UUID(as_uuid=True), nullable=False),
    Column("arrival_s", BigInteger, nullable=False),
    Column("service_start_s", BigInteger, nullable=False),
    Column("departure_s", BigInteger, nullable=False),
    lifecycle="route_stop",
    constraints=(UniqueConstraint("route_id", "sequence", name="uq_route_stops_sequence"),
                 CheckConstraint("arrival_s >= 0 AND arrival_s <= service_start_s "
                                 "AND service_start_s <= departure_s", name="stop_times")))

# ----------------------------------------------------------------- optimization

optimization_requests = entity_table("optimization_requests",
    Column("kind", String(32), nullable=False),
    Column("snapshot_id", UUID(as_uuid=True),
           ForeignKey("planning_snapshots.id", ondelete="RESTRICT"), nullable=False),
    Column("job_id", UUID(as_uuid=True), ForeignKey("jobs.id", ondelete="RESTRICT"), nullable=False),
    Column("request_hash", String(64), nullable=False),
    lifecycle="optimization_request",
    constraints=(UniqueConstraint("job_id", name="uq_optimization_requests_job"),
                 CheckConstraint("kind IN ('transport','warehouse','joint')", name="request_kind")))

optimization_results = entity_table("optimization_results",
    Column("request_id", UUID(as_uuid=True),
           ForeignKey("optimization_requests.id", ondelete="RESTRICT"), nullable=False),
    Column("solve_status", String(32), nullable=False),
    Column("candidate_id", UUID(as_uuid=True)),
    lifecycle="optimization_result",
    constraints=(CheckConstraint("solve_status IN ('optimal','feasible','infeasible','timeout',"
                                 "'unknown','invalid_input','error','cancelled')", name="solve_status")))
Index("ix_optimization_results_request", optimization_results.c.request_id)

candidate_plans = Table("candidate_plans", metadata,
    Column("id", UUID(as_uuid=True), primary_key=True),
    Column("scope_id", UUID(as_uuid=True), nullable=False),
    Column("schedule_id", UUID(as_uuid=True), ForeignKey("schedules.id", ondelete="RESTRICT"),
           nullable=False),
    Column("base_version_id", UUID(as_uuid=True),
           ForeignKey("schedule_versions.id", ondelete="RESTRICT")),
    Column("snapshot_id", UUID(as_uuid=True),
           ForeignKey("planning_snapshots.id", ondelete="RESTRICT"), nullable=False),
    Column("snapshot_hash", String(64), nullable=False),
    Column("content_hash", String(64), nullable=False),
    Column("created_at", DateTime(timezone=True), nullable=False),
    Column("payload", JSONB(none_as_null=True), nullable=False),
    CheckConstraint("payload->>'id' = id::text AND payload->>'content_hash' = content_hash",
                    name="identity"),
    UniqueConstraint("schedule_id", "content_hash", name="uq_candidate_plans_schedule_content"))
Index("ix_candidate_plans_snapshot", candidate_plans.c.snapshot_id)

travel_matrices = Table("travel_matrices", metadata,
    Column("id", UUID(as_uuid=True), primary_key=True),
    Column("version", BigInteger, primary_key=True),
    Column("scope_id", UUID(as_uuid=True), nullable=False),
    Column("hash", String(64), nullable=False),
    Column("created_at", DateTime(timezone=True), nullable=False),
    Column("payload", JSONB(none_as_null=True), nullable=False),
    CheckConstraint("version > 0", name="version"),
    CheckConstraint("payload->>'id' = id::text AND (payload->>'version')::bigint = version "
                    "AND payload->>'hash' = hash", name="identity"))

# --------------------------------------------------------- inventory / reservation

inventory_ledger = Table("inventory_ledger", metadata,
    Column("id", UUID(as_uuid=True), primary_key=True),
    Column("scope_id", UUID(as_uuid=True), nullable=False),
    Column("status", String(32), nullable=False),
    Column("created_at", DateTime(timezone=True), nullable=False),
    Column("updated_at", DateTime(timezone=True), nullable=False),
    Column("created_by", UUID(as_uuid=True), nullable=False),
    Column("row_version", BigInteger, nullable=False),
    Column("schema_version", String(16), nullable=False),
    Column("payload", JSONB(none_as_null=True), nullable=False),
    Column("cargo_id", UUID(as_uuid=True), ForeignKey("cargo.id", ondelete="RESTRICT"),
           nullable=False),
    Column("location_id", UUID(as_uuid=True), ForeignKey("locations.id", ondelete="RESTRICT"),
           nullable=False),
    Column("quantity_delta", BigInteger, nullable=False),
    Column("cause_event_id", UUID(as_uuid=True)),
    Column("version_ref", UUID(as_uuid=True)),
    CheckConstraint("status = 'recorded' AND row_version = 0 AND created_at = updated_at",
                    name="record"),
    CheckConstraint("schema_version = '2.0.0' AND payload->>'schema_version' = schema_version",
                    name="schema"),
    CheckConstraint("payload->>'id' = id::text", name="identity"))
Index("ix_inventory_ledger_position", inventory_ledger.c.cargo_id, inventory_ledger.c.location_id,
      inventory_ledger.c.created_at)

reservations = entity_table("reservations",
    Column("resource_kind", String(32), nullable=False),
    Column("resource_id", UUID(as_uuid=True), nullable=False),
    Column("start_s", BigInteger, nullable=False),
    Column("end_s", BigInteger, nullable=False),
    Column("quantity", BigInteger, nullable=False),
    Column("version_id", UUID(as_uuid=True),
           ForeignKey("schedule_versions.id", ondelete="RESTRICT")),
    Column("epoch_utc", DateTime(timezone=True), nullable=False),
    Column("expires_at_utc", DateTime(timezone=True), nullable=False),
    lifecycle="reservation",
    constraints=(CheckConstraint("resource_kind IN ('zone','location','dock','worker','equipment')",
                                 name="resource_kind"),
                 CheckConstraint("start_s >= 0 AND end_s > start_s AND quantity >= 0",
                                 name="reservation_interval")))
Index("ix_reservations_resource", reservations.c.resource_id, reservations.c.start_s,
      reservations.c.end_s, reservations.c.status)

# ------------------------------------------------------------- audit / outbox / event

audit_entries = Table("audit_entries", metadata,
    Column("id", UUID(as_uuid=True), primary_key=True),
    Column("scope_id", UUID(as_uuid=True), nullable=False),
    Column("status", String(32), nullable=False),
    Column("created_at", DateTime(timezone=True), nullable=False),
    Column("updated_at", DateTime(timezone=True), nullable=False),
    Column("created_by", UUID(as_uuid=True), nullable=False),
    Column("row_version", BigInteger, nullable=False),
    Column("schema_version", String(16), nullable=False),
    Column("payload", JSONB(none_as_null=True), nullable=False),
    Column("actor_id", UUID(as_uuid=True), nullable=False),
    Column("action", String(64), nullable=False),
    Column("entity_kind", String(32), nullable=False),
    Column("entity_id", UUID(as_uuid=True), nullable=False),
    Column("trace_id", UUID(as_uuid=True), nullable=False),
    Column("before_hash", String(64)),
    Column("after_hash", String(64)),
    CheckConstraint("status = 'recorded' AND row_version = 0 AND created_at = updated_at",
                    name="record"),
    CheckConstraint("schema_version = '2.0.0' AND payload->>'schema_version' = schema_version",
                    name="schema"),
    CheckConstraint("payload->>'id' = id::text", name="identity"))
Index("ix_audit_entries_trace", audit_entries.c.trace_id, audit_entries.c.created_at)
Index("ix_audit_entries_entity", audit_entries.c.entity_kind, audit_entries.c.entity_id)

outbox = entity_table("outbox",
    Column("topic", String(64), nullable=False),
    Column("sequence", BigInteger, nullable=False),
    Column("retry_after", DateTime(timezone=True)),
    Column("attempt", BigInteger, nullable=False),
    lifecycle="outbox",
    constraints=(UniqueConstraint("sequence", name="uq_outbox_sequence"),
                 CheckConstraint("attempt >= 0", name="attempt")))
Index("ix_outbox_dispatch", outbox.c.status, outbox.c.sequence)

lifecycle_events = Table("lifecycle_events", metadata,
    Column("id", UUID(as_uuid=True), primary_key=True),
    Column("scope_id", UUID(as_uuid=True), nullable=False),
    Column("status", String(32), nullable=False),
    Column("created_at", DateTime(timezone=True), nullable=False),
    Column("updated_at", DateTime(timezone=True), nullable=False),
    Column("created_by", UUID(as_uuid=True), nullable=False),
    Column("row_version", BigInteger, nullable=False),
    Column("schema_version", String(16), nullable=False),
    Column("payload", JSONB(none_as_null=True), nullable=False),
    Column("entity_kind", String(32), nullable=False),
    Column("entity_id", UUID(as_uuid=True), nullable=False),
    Column("from_state", String(32)),
    Column("to_state", String(32), nullable=False),
    Column("cause", String(256)),
    Column("occurred_at", DateTime(timezone=True), nullable=False),
    CheckConstraint("status = 'recorded' AND row_version = 0 AND created_at = updated_at",
                    name="record"),
    CheckConstraint("schema_version = '2.0.0' AND payload->>'schema_version' = schema_version",
                    name="schema"),
    CheckConstraint("payload->>'id' = id::text", name="identity"))
Index("ix_lifecycle_events_entity", lifecycle_events.c.entity_kind, lifecycle_events.c.entity_id,
      lifecycle_events.c.occurred_at)

PLANNING_TABLES = (
    planning_snapshots, schedules, schedule_versions, schedule_tasks, transport_tasks,
    warehouse_tasks, routes, route_stops, optimization_requests, optimization_results,
    candidate_plans, travel_matrices, inventory_ledger, reservations, audit_entries, outbox,
    lifecycle_events,
)

#: Tables whose rows are content-immutable after insert (trigger enforced by migration 0002).
IMMUTABLE_TABLES = (
    "planning_snapshots", "candidate_plans", "travel_matrices", "inventory_ledger",
    "audit_entries", "lifecycle_events",
)
