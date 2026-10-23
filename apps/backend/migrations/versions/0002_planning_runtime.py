"""Immutable jobs + planning versions, inventory, audit and outbox (frozen 0002).

Generated once from ``runtime_models``/``planning_models``; the literal DDL below is not
regenerated automatically, so editing a model cannot silently change this migration. The
file was never deployed when it was completed; it is frozen from this point on.
"""
from alembic import op

revision = "0002_planning_runtime"
down_revision = "0001_resources"
branch_labels = None
depends_on = None


def upgrade():
    op.execute("""CREATE TABLE job_requests (
	request_id UUID NOT NULL, 
	version BIGINT NOT NULL, 
	scope_id UUID NOT NULL, 
	family VARCHAR(32) NOT NULL, 
	schema_version VARCHAR(16) NOT NULL, 
	hash VARCHAR(64) NOT NULL, 
	content BYTEA NOT NULL, 
	CONSTRAINT pk_job_requests PRIMARY KEY (request_id, version), 
	CONSTRAINT ck_job_requests_request_version CHECK (version > 0 AND schema_version = '2.0.0')
)""")
    op.execute("""CREATE TABLE jobs (
	id UUID NOT NULL, 
	scope_id UUID NOT NULL, 
	actor_id UUID NOT NULL, 
	created_by UUID NOT NULL, 
	request_id UUID NOT NULL, 
	request_version BIGINT NOT NULL, 
	trace_id UUID NOT NULL, 
	schema_version VARCHAR(16) NOT NULL, 
	kind VARCHAR(32) NOT NULL, 
	status VARCHAR(32) NOT NULL, 
	command JSONB NOT NULL, 
	request_hash VARCHAR(64) NOT NULL, 
	row_version BIGINT NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	available_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	deadline_utc TIMESTAMP WITH TIME ZONE NOT NULL, 
	started_at TIMESTAMP WITH TIME ZONE, 
	finished_at TIMESTAMP WITH TIME ZONE, 
	attempt BIGINT NOT NULL, 
	max_attempts BIGINT NOT NULL, 
	cancel_requested BOOLEAN NOT NULL, 
	lease_owner UUID, 
	lease_epoch BIGINT NOT NULL, 
	lease_expires_at TIMESTAMP WITH TIME ZONE, 
	result_ref JSONB, 
	failure JSONB, 
	CONSTRAINT pk_jobs PRIMARY KEY (id), 
	CONSTRAINT fk_jobs_request_id_job_requests FOREIGN KEY(request_id, request_version) REFERENCES job_requests (request_id, version) ON DELETE RESTRICT, 
	CONSTRAINT ck_jobs_job_status CHECK (status IN ('queued','running','completed','failed','cancelled')), 
	CONSTRAINT ck_jobs_job_counters CHECK (attempt >= 0 AND max_attempts > 0 AND attempt <= max_attempts AND lease_epoch >= 0 AND row_version >= 0), 
	CONSTRAINT ck_jobs_job_result CHECK (status != 'completed' OR (result_ref IS NOT NULL AND failure IS NULL)), 
	CONSTRAINT ck_jobs_job_failure CHECK (status != 'failed' OR (failure IS NOT NULL AND result_ref IS NULL)), 
	CONSTRAINT ck_jobs_job_lease CHECK ((status = 'running') = (lease_owner IS NOT NULL AND lease_expires_at IS NOT NULL)), 
	CONSTRAINT ck_jobs_job_schema CHECK (schema_version = '2.0.0' AND command->>'schema_version' = schema_version)
)""")
    op.execute("""CREATE TABLE job_attempts (
	id UUID NOT NULL, 
	schema_version VARCHAR(16) NOT NULL, 
	status VARCHAR(32) NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	created_by UUID NOT NULL, 
	row_version BIGINT NOT NULL, 
	job_id UUID NOT NULL, 
	attempt_no BIGINT NOT NULL, 
	lease_owner UUID NOT NULL, 
	lease_epoch BIGINT NOT NULL, 
	started_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	finished_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	outcome VARCHAR(32) NOT NULL, 
	failure JSONB, 
	result_ref JSONB, 
	CONSTRAINT pk_job_attempts PRIMARY KEY (id), 
	CONSTRAINT uq_job_attempts_job_id UNIQUE (job_id, attempt_no), 
	CONSTRAINT ck_job_attempts_attempt_metadata CHECK (schema_version = '2.0.0' AND status = 'recorded' AND row_version = 0), 
	CONSTRAINT ck_job_attempts_attempt_times CHECK (finished_at >= started_at AND created_at = updated_at), 
	CONSTRAINT fk_job_attempts_job_id_jobs FOREIGN KEY(job_id) REFERENCES jobs (id) ON DELETE RESTRICT
)""")
    op.execute("""CREATE TABLE idempotency (
	scope_id UUID NOT NULL, 
	actor_id UUID NOT NULL, 
	operation VARCHAR(64) NOT NULL, 
	key VARCHAR(256) NOT NULL, 
	request_hash VARCHAR(64) NOT NULL, 
	receipt JSONB NOT NULL, 
	expires_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	CONSTRAINT pk_idempotency PRIMARY KEY (scope_id, actor_id, operation, key)
)""")
    op.execute("""CREATE TABLE planning_snapshots (
	id UUID NOT NULL, 
	scope_id UUID NOT NULL, 
	scope_hash VARCHAR(64) NOT NULL, 
	content_hash VARCHAR(64) NOT NULL, 
	status VARCHAR(32) NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	created_by UUID NOT NULL, 
	row_version BIGINT NOT NULL, 
	schema_version VARCHAR(16) NOT NULL, 
	payload JSONB NOT NULL, 
	CONSTRAINT pk_planning_snapshots PRIMARY KEY (id), 
	CONSTRAINT ck_planning_snapshots_record CHECK (status = 'recorded' AND row_version = 0), 
	CONSTRAINT ck_planning_snapshots_times CHECK (created_at = updated_at), 
	CONSTRAINT ck_planning_snapshots_schema CHECK (schema_version = '2.0.0'), 
	CONSTRAINT ck_planning_snapshots_identity CHECK (payload->>'id' = id::text AND payload->>'hash' = content_hash)
)""")
    op.execute("""CREATE TABLE schedules (
	id UUID NOT NULL, 
	scope_id UUID NOT NULL, 
	status VARCHAR(32) NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	created_by UUID NOT NULL, 
	row_version BIGINT NOT NULL, 
	schema_version VARCHAR(16) NOT NULL, 
	payload JSONB NOT NULL, 
	name VARCHAR(128) NOT NULL, 
	active_version_id UUID, 
	epoch_utc TIMESTAMP WITH TIME ZONE NOT NULL, 
	horizon_s BIGINT NOT NULL, 
	CONSTRAINT pk_schedules PRIMARY KEY (id), 
	CONSTRAINT uq_schedules_scope_name UNIQUE (scope_id, name), 
	CONSTRAINT ck_schedules_horizon CHECK (horizon_s > 0 AND horizon_s <= 604800), 
	CONSTRAINT ck_schedules_revision CHECK (row_version >= 0), 
	CONSTRAINT ck_schedules_schema CHECK (schema_version = '2.0.0' AND payload->>'schema_version' = schema_version), 
	CONSTRAINT ck_schedules_timestamps CHECK (updated_at >= created_at), 
	CONSTRAINT ck_schedules_status CHECK (status IN ('draft','active','suspended','completed','superseded')), 
	CONSTRAINT ck_schedules_payload_identity CHECK (payload->>'id' = id::text AND payload->>'status' = status AND (payload->>'row_version')::bigint = row_version)
)""")
    op.execute("""CREATE TABLE schedule_versions (
	id UUID NOT NULL, 
	scope_id UUID NOT NULL, 
	status VARCHAR(32) NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	created_by UUID NOT NULL, 
	row_version BIGINT NOT NULL, 
	schema_version VARCHAR(16) NOT NULL, 
	payload JSONB NOT NULL, 
	schedule_id UUID NOT NULL, 
	version_no BIGINT NOT NULL, 
	parent_version_id UUID, 
	snapshot_id UUID NOT NULL, 
	content_hash VARCHAR(64) NOT NULL, 
	reason VARCHAR(64) NOT NULL, 
	event_id UUID, 
	validation_report_ref UUID NOT NULL, 
	CONSTRAINT pk_schedule_versions PRIMARY KEY (id), 
	CONSTRAINT uq_schedule_versions_number UNIQUE (schedule_id, version_no), 
	CONSTRAINT ck_schedule_versions_positive_version CHECK (version_no > 0), 
	CONSTRAINT ck_schedule_versions_parent_not_self CHECK (parent_version_id IS NULL OR parent_version_id <> id), 
	CONSTRAINT ck_schedule_versions_revision CHECK (row_version >= 0), 
	CONSTRAINT ck_schedule_versions_schema CHECK (schema_version = '2.0.0' AND payload->>'schema_version' = schema_version), 
	CONSTRAINT ck_schedule_versions_timestamps CHECK (updated_at >= created_at), 
	CONSTRAINT ck_schedule_versions_status CHECK (status IN ('candidate','validated','committed','superseded','rejected','expired')), 
	CONSTRAINT ck_schedule_versions_payload_identity CHECK (payload->>'id' = id::text AND payload->>'status' = status AND (payload->>'row_version')::bigint = row_version), 
	CONSTRAINT fk_schedule_versions_schedule_id_schedules FOREIGN KEY(schedule_id) REFERENCES schedules (id) ON DELETE RESTRICT, 
	CONSTRAINT fk_schedule_versions_parent_version_id_schedule_versions FOREIGN KEY(parent_version_id) REFERENCES schedule_versions (id) ON DELETE RESTRICT, 
	CONSTRAINT fk_schedule_versions_snapshot_id_planning_snapshots FOREIGN KEY(snapshot_id) REFERENCES planning_snapshots (id) ON DELETE RESTRICT
)""")
    op.execute("""CREATE TABLE schedule_tasks (
	id UUID NOT NULL, 
	scope_id UUID NOT NULL, 
	status VARCHAR(32) NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	created_by UUID NOT NULL, 
	row_version BIGINT NOT NULL, 
	schema_version VARCHAR(16) NOT NULL, 
	payload JSONB NOT NULL, 
	version_id UUID NOT NULL, 
	task_id UUID NOT NULL, 
	task_kind VARCHAR(32) NOT NULL, 
	planned_start_s BIGINT NOT NULL, 
	planned_end_s BIGINT NOT NULL, 
	sequence BIGINT, 
	CONSTRAINT pk_schedule_tasks PRIMARY KEY (id), 
	CONSTRAINT uq_schedule_tasks_version_task UNIQUE (version_id, task_id), 
	CONSTRAINT ck_schedule_tasks_task_interval CHECK (planned_start_s >= 0 AND planned_end_s > planned_start_s), 
	CONSTRAINT ck_schedule_tasks_task_kind CHECK (task_kind IN ('transport_task','warehouse_task')), 
	CONSTRAINT ck_schedule_tasks_revision CHECK (row_version >= 0), 
	CONSTRAINT ck_schedule_tasks_schema CHECK (schema_version = '2.0.0' AND payload->>'schema_version' = schema_version), 
	CONSTRAINT ck_schedule_tasks_timestamps CHECK (updated_at >= created_at), 
	CONSTRAINT ck_schedule_tasks_status CHECK (status IN ('planned','dispatched','running','completed','cancelled','interrupted')), 
	CONSTRAINT ck_schedule_tasks_payload_identity CHECK (payload->>'id' = id::text AND payload->>'status' = status AND (payload->>'row_version')::bigint = row_version), 
	CONSTRAINT fk_schedule_tasks_version_id_schedule_versions FOREIGN KEY(version_id) REFERENCES schedule_versions (id) ON DELETE RESTRICT
)""")
    op.execute("""CREATE TABLE transport_tasks (
	id UUID NOT NULL, 
	scope_id UUID NOT NULL, 
	status VARCHAR(32) NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	created_by UUID NOT NULL, 
	row_version BIGINT NOT NULL, 
	schema_version VARCHAR(16) NOT NULL, 
	payload JSONB NOT NULL, 
	order_id UUID NOT NULL, 
	leg_no BIGINT NOT NULL, 
	pickup_node_id UUID NOT NULL, 
	delivery_node_id UUID NOT NULL, 
	service_s BIGINT NOT NULL, 
	CONSTRAINT pk_transport_tasks PRIMARY KEY (id), 
	CONSTRAINT ck_transport_tasks_revision CHECK (row_version >= 0), 
	CONSTRAINT ck_transport_tasks_schema CHECK (schema_version = '2.0.0' AND payload->>'schema_version' = schema_version), 
	CONSTRAINT ck_transport_tasks_timestamps CHECK (updated_at >= created_at), 
	CONSTRAINT ck_transport_tasks_status CHECK (status IN ('pending','ready','running','completed','cancelled','interrupted','failed')), 
	CONSTRAINT ck_transport_tasks_payload_identity CHECK (payload->>'id' = id::text AND payload->>'status' = status AND (payload->>'row_version')::bigint = row_version), 
	CONSTRAINT fk_transport_tasks_order_id_orders FOREIGN KEY(order_id) REFERENCES orders (id) ON DELETE RESTRICT
)""")
    op.execute("""CREATE TABLE warehouse_tasks (
	id UUID NOT NULL, 
	scope_id UUID NOT NULL, 
	status VARCHAR(32) NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	created_by UUID NOT NULL, 
	row_version BIGINT NOT NULL, 
	schema_version VARCHAR(16) NOT NULL, 
	payload JSONB NOT NULL, 
	order_id UUID, 
	warehouse_id UUID NOT NULL, 
	kind VARCHAR(32) NOT NULL, 
	duration_s BIGINT NOT NULL, 
	setup_class VARCHAR(128) NOT NULL, 
	CONSTRAINT pk_warehouse_tasks PRIMARY KEY (id), 
	CONSTRAINT ck_warehouse_tasks_task_duration CHECK (duration_s >= 0), 
	CONSTRAINT ck_warehouse_tasks_operation_kind CHECK (kind IN ('receive','dispatch','sort','load','unload','setup')), 
	CONSTRAINT ck_warehouse_tasks_revision CHECK (row_version >= 0), 
	CONSTRAINT ck_warehouse_tasks_schema CHECK (schema_version = '2.0.0' AND payload->>'schema_version' = schema_version), 
	CONSTRAINT ck_warehouse_tasks_timestamps CHECK (updated_at >= created_at), 
	CONSTRAINT ck_warehouse_tasks_status CHECK (status IN ('pending','ready','running','completed','cancelled','interrupted','failed')), 
	CONSTRAINT ck_warehouse_tasks_payload_identity CHECK (payload->>'id' = id::text AND payload->>'status' = status AND (payload->>'row_version')::bigint = row_version), 
	CONSTRAINT fk_warehouse_tasks_order_id_orders FOREIGN KEY(order_id) REFERENCES orders (id) ON DELETE RESTRICT, 
	CONSTRAINT fk_warehouse_tasks_warehouse_id_warehouses FOREIGN KEY(warehouse_id) REFERENCES warehouses (id) ON DELETE RESTRICT
)""")
    op.execute("""CREATE TABLE routes (
	id UUID NOT NULL, 
	scope_id UUID NOT NULL, 
	status VARCHAR(32) NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	created_by UUID NOT NULL, 
	row_version BIGINT NOT NULL, 
	schema_version VARCHAR(16) NOT NULL, 
	payload JSONB NOT NULL, 
	version_id UUID NOT NULL, 
	vehicle_id UUID NOT NULL, 
	driver_id UUID NOT NULL, 
	start_node_id UUID NOT NULL, 
	end_node_id UUID NOT NULL, 
	total_distance_m BIGINT NOT NULL, 
	matrix_id UUID NOT NULL, 
	matrix_version BIGINT NOT NULL, 
	CONSTRAINT pk_routes PRIMARY KEY (id), 
	CONSTRAINT ck_routes_revision CHECK (row_version >= 0), 
	CONSTRAINT ck_routes_schema CHECK (schema_version = '2.0.0' AND payload->>'schema_version' = schema_version), 
	CONSTRAINT ck_routes_timestamps CHECK (updated_at >= created_at), 
	CONSTRAINT ck_routes_status CHECK (status IN ('candidate','validated','published','superseded')), 
	CONSTRAINT ck_routes_payload_identity CHECK (payload->>'id' = id::text AND payload->>'status' = status AND (payload->>'row_version')::bigint = row_version), 
	CONSTRAINT fk_routes_version_id_schedule_versions FOREIGN KEY(version_id) REFERENCES schedule_versions (id) ON DELETE RESTRICT, 
	CONSTRAINT fk_routes_vehicle_id_vehicles FOREIGN KEY(vehicle_id) REFERENCES vehicles (id) ON DELETE RESTRICT, 
	CONSTRAINT fk_routes_driver_id_drivers FOREIGN KEY(driver_id) REFERENCES drivers (id) ON DELETE RESTRICT
)""")
    op.execute("""CREATE TABLE route_stops (
	id UUID NOT NULL, 
	scope_id UUID NOT NULL, 
	status VARCHAR(32) NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	created_by UUID NOT NULL, 
	row_version BIGINT NOT NULL, 
	schema_version VARCHAR(16) NOT NULL, 
	payload JSONB NOT NULL, 
	route_id UUID NOT NULL, 
	sequence BIGINT NOT NULL, 
	node_id UUID NOT NULL, 
	arrival_s BIGINT NOT NULL, 
	service_start_s BIGINT NOT NULL, 
	departure_s BIGINT NOT NULL, 
	CONSTRAINT pk_route_stops PRIMARY KEY (id), 
	CONSTRAINT uq_route_stops_sequence UNIQUE (route_id, sequence), 
	CONSTRAINT ck_route_stops_stop_times CHECK (arrival_s >= 0 AND arrival_s <= service_start_s AND service_start_s <= departure_s), 
	CONSTRAINT ck_route_stops_revision CHECK (row_version >= 0), 
	CONSTRAINT ck_route_stops_schema CHECK (schema_version = '2.0.0' AND payload->>'schema_version' = schema_version), 
	CONSTRAINT ck_route_stops_timestamps CHECK (updated_at >= created_at), 
	CONSTRAINT ck_route_stops_status CHECK (status IN ('planned','reached','servicing','completed','cancelled')), 
	CONSTRAINT ck_route_stops_payload_identity CHECK (payload->>'id' = id::text AND payload->>'status' = status AND (payload->>'row_version')::bigint = row_version), 
	CONSTRAINT fk_route_stops_route_id_routes FOREIGN KEY(route_id) REFERENCES routes (id) ON DELETE RESTRICT
)""")
    op.execute("""CREATE TABLE optimization_requests (
	id UUID NOT NULL, 
	scope_id UUID NOT NULL, 
	status VARCHAR(32) NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	created_by UUID NOT NULL, 
	row_version BIGINT NOT NULL, 
	schema_version VARCHAR(16) NOT NULL, 
	payload JSONB NOT NULL, 
	kind VARCHAR(32) NOT NULL, 
	snapshot_id UUID NOT NULL, 
	job_id UUID NOT NULL, 
	request_hash VARCHAR(64) NOT NULL, 
	CONSTRAINT pk_optimization_requests PRIMARY KEY (id), 
	CONSTRAINT uq_optimization_requests_job UNIQUE (job_id), 
	CONSTRAINT ck_optimization_requests_request_kind CHECK (kind IN ('transport','warehouse','joint')), 
	CONSTRAINT ck_optimization_requests_revision CHECK (row_version >= 0), 
	CONSTRAINT ck_optimization_requests_schema CHECK (schema_version = '2.0.0' AND payload->>'schema_version' = schema_version), 
	CONSTRAINT ck_optimization_requests_timestamps CHECK (updated_at >= created_at), 
	CONSTRAINT ck_optimization_requests_status CHECK (status IN ('accepted','queued','running','completed','cancelled','failed')), 
	CONSTRAINT ck_optimization_requests_payload_identity CHECK (payload->>'id' = id::text AND payload->>'status' = status AND (payload->>'row_version')::bigint = row_version), 
	CONSTRAINT fk_optimization_requests_snapshot_id_planning_snapshots FOREIGN KEY(snapshot_id) REFERENCES planning_snapshots (id) ON DELETE RESTRICT, 
	CONSTRAINT fk_optimization_requests_job_id_jobs FOREIGN KEY(job_id) REFERENCES jobs (id) ON DELETE RESTRICT
)""")
    op.execute("""CREATE TABLE optimization_results (
	id UUID NOT NULL, 
	scope_id UUID NOT NULL, 
	status VARCHAR(32) NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	created_by UUID NOT NULL, 
	row_version BIGINT NOT NULL, 
	schema_version VARCHAR(16) NOT NULL, 
	payload JSONB NOT NULL, 
	request_id UUID NOT NULL, 
	solve_status VARCHAR(32) NOT NULL, 
	candidate_id UUID, 
	CONSTRAINT pk_optimization_results PRIMARY KEY (id), 
	CONSTRAINT ck_optimization_results_revision CHECK (row_version >= 0), 
	CONSTRAINT ck_optimization_results_schema CHECK (schema_version = '2.0.0' AND payload->>'schema_version' = schema_version), 
	CONSTRAINT ck_optimization_results_timestamps CHECK (updated_at >= created_at), 
	CONSTRAINT ck_optimization_results_status CHECK (status IN ('recorded','invalidated')), 
	CONSTRAINT ck_optimization_results_payload_identity CHECK (payload->>'id' = id::text AND payload->>'status' = status AND (payload->>'row_version')::bigint = row_version), 
	CONSTRAINT fk_optimization_results_request_id_optimization_requests FOREIGN KEY(request_id) REFERENCES optimization_requests (id) ON DELETE RESTRICT
)""")
    op.execute("""CREATE TABLE candidate_plans (
	id UUID NOT NULL, 
	scope_id UUID NOT NULL, 
	schedule_id UUID NOT NULL, 
	base_version_id UUID, 
	snapshot_id UUID NOT NULL, 
	snapshot_hash VARCHAR(64) NOT NULL, 
	content_hash VARCHAR(64) NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	payload JSONB NOT NULL, 
	CONSTRAINT pk_candidate_plans PRIMARY KEY (id), 
	CONSTRAINT ck_candidate_plans_identity CHECK (payload->>'id' = id::text AND payload->>'content_hash' = content_hash), 
	CONSTRAINT uq_candidate_plans_schedule_content UNIQUE (schedule_id, content_hash), 
	CONSTRAINT fk_candidate_plans_schedule_id_schedules FOREIGN KEY(schedule_id) REFERENCES schedules (id) ON DELETE RESTRICT, 
	CONSTRAINT fk_candidate_plans_base_version_id_schedule_versions FOREIGN KEY(base_version_id) REFERENCES schedule_versions (id) ON DELETE RESTRICT, 
	CONSTRAINT fk_candidate_plans_snapshot_id_planning_snapshots FOREIGN KEY(snapshot_id) REFERENCES planning_snapshots (id) ON DELETE RESTRICT
)""")
    op.execute("""CREATE TABLE travel_matrices (
	id UUID NOT NULL, 
	version BIGINT NOT NULL, 
	scope_id UUID NOT NULL, 
	hash VARCHAR(64) NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	payload JSONB NOT NULL, 
	CONSTRAINT pk_travel_matrices PRIMARY KEY (id, version), 
	CONSTRAINT ck_travel_matrices_version CHECK (version > 0), 
	CONSTRAINT ck_travel_matrices_identity CHECK (payload->>'id' = id::text AND (payload->>'version')::bigint = version AND payload->>'hash' = hash)
)""")
    op.execute("""CREATE TABLE inventory_ledger (
	id UUID NOT NULL, 
	scope_id UUID NOT NULL, 
	status VARCHAR(32) NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	created_by UUID NOT NULL, 
	row_version BIGINT NOT NULL, 
	schema_version VARCHAR(16) NOT NULL, 
	payload JSONB NOT NULL, 
	cargo_id UUID NOT NULL, 
	location_id UUID NOT NULL, 
	quantity_delta BIGINT NOT NULL, 
	cause_event_id UUID, 
	version_ref UUID, 
	CONSTRAINT pk_inventory_ledger PRIMARY KEY (id), 
	CONSTRAINT ck_inventory_ledger_record CHECK (status = 'recorded' AND row_version = 0 AND created_at = updated_at), 
	CONSTRAINT ck_inventory_ledger_schema CHECK (schema_version = '2.0.0' AND payload->>'schema_version' = schema_version), 
	CONSTRAINT ck_inventory_ledger_identity CHECK (payload->>'id' = id::text), 
	CONSTRAINT fk_inventory_ledger_cargo_id_cargo FOREIGN KEY(cargo_id) REFERENCES cargo (id) ON DELETE RESTRICT, 
	CONSTRAINT fk_inventory_ledger_location_id_locations FOREIGN KEY(location_id) REFERENCES locations (id) ON DELETE RESTRICT
)""")
    op.execute("""CREATE TABLE reservations (
	id UUID NOT NULL, 
	scope_id UUID NOT NULL, 
	status VARCHAR(32) NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	created_by UUID NOT NULL, 
	row_version BIGINT NOT NULL, 
	schema_version VARCHAR(16) NOT NULL, 
	payload JSONB NOT NULL, 
	resource_kind VARCHAR(32) NOT NULL, 
	resource_id UUID NOT NULL, 
	start_s BIGINT NOT NULL, 
	end_s BIGINT NOT NULL, 
	quantity BIGINT NOT NULL, 
	version_id UUID, 
	epoch_utc TIMESTAMP WITH TIME ZONE NOT NULL, 
	expires_at_utc TIMESTAMP WITH TIME ZONE NOT NULL, 
	CONSTRAINT pk_reservations PRIMARY KEY (id), 
	CONSTRAINT ck_reservations_resource_kind CHECK (resource_kind IN ('zone','location','dock','worker','equipment')), 
	CONSTRAINT ck_reservations_reservation_interval CHECK (start_s >= 0 AND end_s > start_s AND quantity >= 0), 
	CONSTRAINT ck_reservations_revision CHECK (row_version >= 0), 
	CONSTRAINT ck_reservations_schema CHECK (schema_version = '2.0.0' AND payload->>'schema_version' = schema_version), 
	CONSTRAINT ck_reservations_timestamps CHECK (updated_at >= created_at), 
	CONSTRAINT ck_reservations_status CHECK (status IN ('held','committed','released','expired')), 
	CONSTRAINT ck_reservations_payload_identity CHECK (payload->>'id' = id::text AND payload->>'status' = status AND (payload->>'row_version')::bigint = row_version), 
	CONSTRAINT fk_reservations_version_id_schedule_versions FOREIGN KEY(version_id) REFERENCES schedule_versions (id) ON DELETE RESTRICT
)""")
    op.execute("""CREATE TABLE audit_entries (
	id UUID NOT NULL, 
	scope_id UUID NOT NULL, 
	status VARCHAR(32) NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	created_by UUID NOT NULL, 
	row_version BIGINT NOT NULL, 
	schema_version VARCHAR(16) NOT NULL, 
	payload JSONB NOT NULL, 
	actor_id UUID NOT NULL, 
	action VARCHAR(64) NOT NULL, 
	entity_kind VARCHAR(32) NOT NULL, 
	entity_id UUID NOT NULL, 
	trace_id UUID NOT NULL, 
	before_hash VARCHAR(64), 
	after_hash VARCHAR(64), 
	CONSTRAINT pk_audit_entries PRIMARY KEY (id), 
	CONSTRAINT ck_audit_entries_record CHECK (status = 'recorded' AND row_version = 0 AND created_at = updated_at), 
	CONSTRAINT ck_audit_entries_schema CHECK (schema_version = '2.0.0' AND payload->>'schema_version' = schema_version), 
	CONSTRAINT ck_audit_entries_identity CHECK (payload->>'id' = id::text)
)""")
    op.execute("""CREATE TABLE outbox (
	id UUID NOT NULL, 
	scope_id UUID NOT NULL, 
	status VARCHAR(32) NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	created_by UUID NOT NULL, 
	row_version BIGINT NOT NULL, 
	schema_version VARCHAR(16) NOT NULL, 
	payload JSONB NOT NULL, 
	topic VARCHAR(64) NOT NULL, 
	sequence BIGINT NOT NULL, 
	retry_after TIMESTAMP WITH TIME ZONE, 
	attempt BIGINT NOT NULL, 
	CONSTRAINT pk_outbox PRIMARY KEY (id), 
	CONSTRAINT uq_outbox_sequence UNIQUE (sequence), 
	CONSTRAINT ck_outbox_attempt CHECK (attempt >= 0), 
	CONSTRAINT ck_outbox_revision CHECK (row_version >= 0), 
	CONSTRAINT ck_outbox_schema CHECK (schema_version = '2.0.0' AND payload->>'schema_version' = schema_version), 
	CONSTRAINT ck_outbox_timestamps CHECK (updated_at >= created_at), 
	CONSTRAINT ck_outbox_status CHECK (status IN ('pending','delivering','delivered','dead_letter')), 
	CONSTRAINT ck_outbox_payload_identity CHECK (payload->>'id' = id::text AND payload->>'status' = status AND (payload->>'row_version')::bigint = row_version)
)""")
    op.execute("""CREATE TABLE lifecycle_events (
	id UUID NOT NULL, 
	scope_id UUID NOT NULL, 
	status VARCHAR(32) NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	created_by UUID NOT NULL, 
	row_version BIGINT NOT NULL, 
	schema_version VARCHAR(16) NOT NULL, 
	payload JSONB NOT NULL, 
	entity_kind VARCHAR(32) NOT NULL, 
	entity_id UUID NOT NULL, 
	from_state VARCHAR(32), 
	to_state VARCHAR(32) NOT NULL, 
	cause VARCHAR(256), 
	occurred_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	CONSTRAINT pk_lifecycle_events PRIMARY KEY (id), 
	CONSTRAINT ck_lifecycle_events_record CHECK (status = 'recorded' AND row_version = 0 AND created_at = updated_at), 
	CONSTRAINT ck_lifecycle_events_schema CHECK (schema_version = '2.0.0' AND payload->>'schema_version' = schema_version), 
	CONSTRAINT ck_lifecycle_events_identity CHECK (payload->>'id' = id::text)
)""")
    op.execute("""CREATE INDEX ix_jobs_claim ON jobs (status, available_at, created_at)""")
    op.execute("""CREATE INDEX ix_planning_snapshots_hash ON planning_snapshots (scope_id, content_hash)""")
    op.execute("""CREATE INDEX ix_planning_snapshots_scope ON planning_snapshots (scope_id, created_at, id)""")
    op.execute("""CREATE INDEX ix_schedules_page ON schedules (scope_id, created_at, id)""")
    op.execute("""CREATE INDEX ix_schedule_versions_page ON schedule_versions (scope_id, created_at, id)""")
    op.execute("""CREATE INDEX ix_schedule_versions_parent ON schedule_versions (parent_version_id)""")
    op.execute("""CREATE INDEX ix_schedule_versions_schedule ON schedule_versions (schedule_id, version_no)""")
    op.execute("""CREATE INDEX ix_schedule_tasks_page ON schedule_tasks (scope_id, created_at, id)""")
    op.execute("""CREATE INDEX ix_schedule_tasks_task ON schedule_tasks (task_id)""")
    op.execute("""CREATE INDEX ix_transport_tasks_page ON transport_tasks (scope_id, created_at, id)""")
    op.execute("""CREATE INDEX ix_warehouse_tasks_page ON warehouse_tasks (scope_id, created_at, id)""")
    op.execute("""CREATE INDEX ix_routes_page ON routes (scope_id, created_at, id)""")
    op.execute("""CREATE INDEX ix_routes_version ON routes (version_id)""")
    op.execute("""CREATE INDEX ix_route_stops_page ON route_stops (scope_id, created_at, id)""")
    op.execute("""CREATE INDEX ix_optimization_requests_page ON optimization_requests (scope_id, created_at, id)""")
    op.execute("""CREATE INDEX ix_optimization_results_page ON optimization_results (scope_id, created_at, id)""")
    op.execute("""CREATE INDEX ix_optimization_results_request ON optimization_results (request_id)""")
    op.execute("""CREATE INDEX ix_candidate_plans_snapshot ON candidate_plans (snapshot_id)""")
    op.execute("""CREATE INDEX ix_inventory_ledger_position ON inventory_ledger (cargo_id, location_id, created_at)""")
    op.execute("""CREATE INDEX ix_reservations_page ON reservations (scope_id, created_at, id)""")
    op.execute("""CREATE INDEX ix_reservations_resource ON reservations (resource_id, start_s, end_s, status)""")
    op.execute("""CREATE INDEX ix_audit_entries_entity ON audit_entries (entity_kind, entity_id)""")
    op.execute("""CREATE INDEX ix_audit_entries_trace ON audit_entries (trace_id, created_at)""")
    op.execute("""CREATE INDEX ix_outbox_dispatch ON outbox (status, sequence)""")
    op.execute("""CREATE INDEX ix_outbox_page ON outbox (scope_id, created_at, id)""")
    op.execute("""CREATE INDEX ix_lifecycle_events_entity ON lifecycle_events (entity_kind, entity_id, occurred_at)""")

    op.execute("CREATE SEQUENCE outbox_sequence")
    op.execute("""ALTER TABLE schedules ADD CONSTRAINT fk_schedules_active_version_id_schedule_versions
        FOREIGN KEY (active_version_id) REFERENCES schedule_versions (id) ON DELETE RESTRICT""")
    op.execute("""CREATE FUNCTION reject_immutable_change() RETURNS trigger LANGUAGE plpgsql AS $$
    BEGIN RAISE EXCEPTION 'immutable record'; END; $$""")
    for name in ("job_requests", "job_attempts", "planning_snapshots", "candidate_plans",
                 "travel_matrices", "inventory_ledger", "audit_entries", "lifecycle_events"):
        op.execute(f"CREATE TRIGGER immutable_{name} BEFORE UPDATE OR DELETE ON {name} "
                   "FOR EACH ROW EXECUTE FUNCTION reject_immutable_change()")
    op.execute("""CREATE FUNCTION protect_schedule_version_content() RETURNS trigger
        LANGUAGE plpgsql AS $$
        BEGIN
            IF (NEW.payload - 'status' - 'row_version' - 'updated_at')
                   IS DISTINCT FROM (OLD.payload - 'status' - 'row_version' - 'updated_at')
               OR NEW.schedule_id <> OLD.schedule_id
               OR NEW.version_no <> OLD.version_no
               OR NEW.parent_version_id IS DISTINCT FROM OLD.parent_version_id
               OR NEW.snapshot_id <> OLD.snapshot_id
               OR NEW.content_hash <> OLD.content_hash
               OR NEW.created_at <> OLD.created_at
               OR NEW.created_by <> OLD.created_by
               OR NEW.validation_report_ref <> OLD.validation_report_ref THEN
                RAISE EXCEPTION 'schedule version content is immutable';
            END IF;
            RETURN NEW;
        END; $$""")
    op.execute("""CREATE TRIGGER protect_schedule_version BEFORE UPDATE ON schedule_versions
        FOR EACH ROW EXECUTE FUNCTION protect_schedule_version_content()""")
    op.execute("""CREATE FUNCTION reject_schedule_version_delete() RETURNS trigger
        LANGUAGE plpgsql AS $$
        BEGIN RAISE EXCEPTION 'schedule versions are append-only'; END; $$""")
    op.execute("""CREATE TRIGGER no_delete_schedule_version BEFORE DELETE ON schedule_versions
        FOR EACH ROW EXECUTE FUNCTION reject_schedule_version_delete()""")

def downgrade():
    for name in ("no_delete_schedule_version", "protect_schedule_version"):
        op.execute(f"DROP TRIGGER IF EXISTS {name} ON schedule_versions")
    for name in ("job_requests", "job_attempts", "planning_snapshots", "candidate_plans",
                 "travel_matrices", "inventory_ledger", "audit_entries", "lifecycle_events"):
        op.execute(f"DROP TRIGGER IF EXISTS immutable_{name} ON {name}")
    for function in ("reject_schedule_version_delete", "protect_schedule_version_content",
                     "reject_immutable_change"):
        op.execute(f"DROP FUNCTION IF EXISTS {function}()")
    op.execute("DROP SEQUENCE IF EXISTS outbox_sequence")
    for table in ("lifecycle_events", "outbox", "audit_entries", "reservations",
                  "inventory_ledger", "travel_matrices", "candidate_plans",
                  "optimization_results", "optimization_requests", "route_stops", "routes",
                  "warehouse_tasks", "transport_tasks", "schedule_tasks", "schedule_versions",
                  "schedules", "planning_snapshots", "idempotency", "job_attempts", "jobs",
                  "job_requests"):
        op.execute(f"DROP TABLE {table}")

