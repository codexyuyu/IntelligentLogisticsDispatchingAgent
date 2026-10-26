-- R27: opt-in work standards, without inferred task durations, stock or positions.
-- Back up the database before applying; never modifies existing business rows.
BEGIN;
CREATE TABLE IF NOT EXISTS public.pg_r27_work_operations (
    operation_code text PRIMARY KEY CHECK (operation_code ~ '^[A-Za-z0-9_-]{1,55}$'),
    order_id bigint NOT NULL REFERENCES public.delivery_orders(id),
    warehouse_id bigint NOT NULL REFERENCES public.warehouses(id),
    resource_code text NOT NULL,
    operation_kind text NOT NULL CHECK (operation_kind IN ('pick','stage','load')),
    duration_s integer NOT NULL CHECK (duration_s > 0),
    release_at timestamptz NOT NULL,
    deadline_at timestamptz NOT NULL,
    predecessor_code text NULL REFERENCES public.pg_r27_work_operations(operation_code)
        DEFERRABLE INITIALLY DEFERRED,
    version integer NOT NULL DEFAULT 1 CHECK (version > 0),
    observed_at timestamptz NOT NULL,
    FOREIGN KEY (warehouse_id, resource_code)
        REFERENCES public.pg_r24_resources(warehouse_id, resource_code),
    CHECK (release_at < deadline_at),
    CHECK (predecessor_code IS NULL OR predecessor_code <> operation_code)
);
CREATE INDEX IF NOT EXISTS pg_r27_operations_order_idx ON public.pg_r27_work_operations(order_id);
CREATE INDEX IF NOT EXISTS pg_r27_operations_warehouse_idx ON public.pg_r27_work_operations(warehouse_id);
COMMIT;
