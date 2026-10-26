-- R24 opt-in ADDITIVE metadata. Run in pgAdmin after database backup.
-- Never changes or drops existing 7 business tables or historical plan rows.
-- No default quantity, volumes, operational location or handoff times are fabricated.
BEGIN;
CREATE TABLE IF NOT EXISTS public.pg_r24_warehouse_zones (
 warehouse_id bigint NOT NULL REFERENCES public.warehouses(id),
 temperature_zone text NOT NULL CHECK (temperature_zone IN ('chilled','frozen')),
 capacity_volume_l integer NOT NULL CHECK (capacity_volume_l > 0),
 PRIMARY KEY (warehouse_id, temperature_zone)
);
CREATE TABLE IF NOT EXISTS public.pg_r24_stock_lots (
 lot_code text PRIMARY KEY,
 warehouse_id bigint NOT NULL REFERENCES public.warehouses(id),
 temperature_zone text NOT NULL CHECK (temperature_zone IN ('chilled','frozen')),
 quantity_units integer NOT NULL CHECK (quantity_units > 0),
 best_before_at timestamptz NOT NULL,
 observed_at timestamptz NOT NULL,
 version integer NOT NULL DEFAULT 1 CHECK (version > 0),
 FOREIGN KEY (warehouse_id, temperature_zone)
   REFERENCES public.pg_r24_warehouse_zones(warehouse_id, temperature_zone),
 CHECK (best_before_at > observed_at)
);
CREATE TABLE IF NOT EXISTS public.pg_r24_order_details (
 order_id bigint PRIMARY KEY REFERENCES public.delivery_orders(id),
 warehouse_id bigint NOT NULL REFERENCES public.warehouses(id),
 lot_code text NOT NULL REFERENCES public.pg_r24_stock_lots(lot_code),
 quantity_units integer NOT NULL CHECK (quantity_units > 0),
 volume_l integer NOT NULL CHECK (volume_l > 0),
 freshness_deadline timestamptz NOT NULL,
 temperature_zone text NOT NULL CHECK (temperature_zone IN ('chilled','frozen')),
 version integer NOT NULL DEFAULT 1 CHECK (version > 0),
 observed_at timestamptz NOT NULL,
 FOREIGN KEY (warehouse_id, temperature_zone)
   REFERENCES public.pg_r24_warehouse_zones(warehouse_id, temperature_zone)
);
CREATE TABLE IF NOT EXISTS public.pg_r24_vehicle_details (
 vehicle_id bigint PRIMARY KEY REFERENCES public.vehicles(id),
 capacity_volume_l integer NOT NULL CHECK (capacity_volume_l > 0),
 remaining_weight_kg integer NOT NULL CHECK (remaining_weight_kg >= 0),
 remaining_volume_l integer NOT NULL CHECK (remaining_volume_l >= 0),
 temperature_zone text NOT NULL CHECK (temperature_zone IN ('chilled','frozen')),
 shift_start timestamptz NOT NULL,
 shift_end timestamptz NOT NULL,
 available_at timestamptz NOT NULL,
 current_node_key text NOT NULL,
 version integer NOT NULL DEFAULT 1 CHECK (version > 0),
 observed_at timestamptz NOT NULL,
 CHECK (shift_start < shift_end),
 CHECK (available_at <= shift_end),
 CHECK (remaining_volume_l <= capacity_volume_l)
);
CREATE TABLE IF NOT EXISTS public.pg_r24_resources (
 warehouse_id bigint NOT NULL REFERENCES public.warehouses(id),
 resource_code text NOT NULL,
 resource_kind text NOT NULL CHECK (resource_kind IN ('cold_room','loading_dock','pre_cooler')),
 temperature_zone text NOT NULL CHECK (temperature_zone IN ('chilled','frozen')),
 capacity_units integer NOT NULL CHECK (capacity_units > 0),
 available_from timestamptz NOT NULL,
 available_until timestamptz NOT NULL,
 version integer NOT NULL DEFAULT 1 CHECK (version > 0),
 PRIMARY KEY (warehouse_id,resource_code),
 CHECK (available_from < available_until),
 FOREIGN KEY (warehouse_id,temperature_zone)
    REFERENCES public.pg_r24_warehouse_zones(warehouse_id, temperature_zone)
);
CREATE TABLE IF NOT EXISTS public.pg_r24_dock_operations (
 order_id bigint PRIMARY KEY REFERENCES public.delivery_orders(id),
 warehouse_id bigint NOT NULL REFERENCES public.warehouses(id),
 ready_at timestamptz NOT NULL,
 loading_window_end timestamptz NOT NULL,
 operation_status text NOT NULL CHECK (operation_status IN ('ready','planned')),
 resource_code text NOT NULL,
 FOREIGN KEY (warehouse_id,resource_code) REFERENCES public.pg_r24_resources(warehouse_id,resource_code),
 version integer NOT NULL DEFAULT 1 CHECK (version > 0),
 observed_at timestamptz NOT NULL,
 CHECK (ready_at < loading_window_end)
);
CREATE INDEX IF NOT EXISTS pg_r24_order_details_wh_idx ON public.pg_r24_order_details(warehouse_id);
CREATE INDEX IF NOT EXISTS pg_r24_lots_wh_idx ON public.pg_r24_stock_lots(warehouse_id);
COMMIT;
