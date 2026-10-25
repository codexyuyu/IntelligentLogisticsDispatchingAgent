-- R22 OPTIONAL setup; one isolated demo table, no changes to production planning tables.
-- Apply explicitly only to your local demonstration database.
CREATE TABLE IF NOT EXISTS public.pg_simulation_previews (
    preview_code text PRIMARY KEY,
    created_at timestamptz NOT NULL DEFAULT now(),
    warehouse_code text NOT NULL,
    temperature_zone text NOT NULL CHECK (temperature_zone IN ('chilled', 'frozen')),
    selected_orders integer NOT NULL CHECK (selected_orders > 0),
    selected_vehicles integer NOT NULL CHECK (selected_vehicles > 0),
    request_parameters jsonb NOT NULL,
    preview_payload jsonb NOT NULL
);
COMMENT ON TABLE public.pg_simulation_previews IS
'R22 SIMULATION ONLY. Not dispatch_plans. Never to be confirmed/executed.';
