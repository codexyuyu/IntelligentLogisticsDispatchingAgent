/** R23 local-only adapter for the existing R21/R22 PostgreSQL sub-app.
 *  This is deliberately not the versioned /api/v1 shared planning contract.
 */
export const pgBase = '/local-pg/pg-preview';

export type PgRow = Record<string, unknown>;
export type ResourceResponse = { mode: string; count: number; rows: PgRow[] };
export type PgSummary = {
  mode: string; orders: number; vehicles: number; nodes: number; distance_pairs: number;
  warehouses: string[]; warehouse_nodes?: string[]; r26_single_warehouse_ready?: boolean; r29_active_warehouse?: { active_warehouses: string[]; retired_historical_fk_warehouse: string; physical_historical_warehouse_retained: boolean } | null; distance_type: string; database_mutated: boolean;
};
export type PgRouteStop = {
  node_id: string; stop_kind: string; order_ids: string[];
  arrival_at_s: number; service_start_at_s: number; departure_at_s: number;
};
export type PgVehicleRoute = {
  vehicle_id: string; stops: PgRouteStop[]; distance_m: number; duration_s: number;
};
export type PgPreview = {
  mode: string; solver: string; solver_status: string; independent_validation: string; business_fact_origin?: string;
  selected_orders: number; selected_vehicles: number; read_orders: number; read_vehicles: number;
  database_mutated: boolean; plan_written: boolean; distance_type: string; assumptions: string[];
  travel_mode?: 'straight_line_simulation' | 'osrm_road_estimate'; business_mode?: 'legacy_simulation' | 'verified_r24';
  demo_route_geojson?: { type: 'FeatureCollection'; features: {
    type: 'Feature'; geometry: { type: 'LineString'; coordinates: [number, number][] };
    properties: { vehicle_id: string; distance_type: string; stop_coordinates?: [number, number][] };
  }[] };
  result: { routes: PgVehicleRoute[]; unserved_orders: unknown[]; metadata: { has_solution: boolean } };
};
export type PgParameters = {
  warehouse_code: string; temperature_zone: 'chilled' | 'frozen'; speed_kmh: number;
  budget_ms: number; max_orders: number; acknowledge_simulation_only: true;
  travel_mode: 'straight_line_simulation' | 'osrm_road_estimate';
  business_mode: 'legacy_simulation' | 'verified_r24';
};
export type PgReadiness = {
  mode: string; tables_installed: boolean; complete: boolean; message?: string;
  counts?: Record<string, number>; missing?: Record<string, number>; note?: string; provenance?: {source_kind:string;installed?:boolean};
};
export type PgSavedItem = {
  preview_code: string; created_at: string; warehouse_code: string; temperature_zone: string;
  selected_orders: number; selected_vehicles: number;
};
export type PgSavedList = { count: number; items: PgSavedItem[] };
export type PgSavedDetail = { preview_code: string; created_at: string; preview: PgPreview; mode: string };
export type PgSaveResult = { preview_code: string; business_plans_mutated: boolean; database_mutated: boolean; independent_validation: string };

export async function pgRequest<T>(_path: string, _body?: unknown): Promise<T> {
  throw new Error('旧演练服务已退出部署；当前数据库功能请使用「运输计划」和「联合调度」。');
}

export function safeText(value: unknown): string {
  return value === undefined || value === null || value === '' ? '—' : String(value);
}

export function prettyDate(value: unknown): string {
  if (!value) return '—';
  const time = new Date(String(value));
  return Number.isFinite(time.getTime()) ? time.toLocaleString('zh-CN', { hour12: false }) : String(value);
}

export function secondsLabel(value: number): string {
  return Number.isFinite(value) ? `${Math.floor(value / 3600)}时${String(Math.floor((value % 3600) / 60)).padStart(2,'0')}分` : '—';
}
