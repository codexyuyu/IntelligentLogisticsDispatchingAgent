/** Stage A verified simulation endpoints (01-14 acceptance evidence). All operations are scoped to a checked run. */
import { request } from '../../api';
import type { TwinRoute } from '../../appTypes';

export type TrackSegment = { from_node_id: string; to_node_id: string; start_s: number; end_s: number };
export type VehicleTrack = { vehicle_id: string; start_node_id?: string; end_node_id: string; segments: TrackSegment[];
  stops?: { node_id: string; sequence: number; kind?: string; order_id?: string | null; arrival_s: number; departure_s: number }[] };
export type ReplayEvent = { id?: string; kind: string; time_s: number; vehicle_id?: string | null; order_id?: string | null };
export type SimIncident = {
  id: string; event_id?: string; status: 'pending' | 'approved' | 'rejected'; row_version: number;
  vehicle_id?: string; time_s?: number; delay_s?: number; proposal_valid?: boolean;
  strategy?: 'simulated_local_reroute' | 'simulated_local_retimed' | 'simulated_hold_resume';
  route_changed?: boolean; candidate_tracks?: VehicleTrack[];
  s1_local_solver?: { status?: string; reason?: string; applied_to_simulation?: boolean; route_changed?: boolean };
  impact?: { affected_order_ids?: string[]; before_eta_s?: Record<string, number>; after_eta_s?: Record<string, number> };
};
export type Simulation = {
  run_id?: string; simulation_id: string; horizon_s: number; active_version: number;
  tracks: VehicleTrack[]; events: ReplayEvent[];
  reconciliation?: { passed: boolean; scope_orders: number; checks?: Record<string, boolean> };
  incident?: SimIncident | null; incidents?: SimIncident[];
};
export type Position = { node_id?: string; from_node_id?: string; to_node_id?: string; progress?: number; x?: number; z?: number } | string;
export type SimulationState = {
  time_s: number; view: 'baseline' | 'candidate'; active_version: number;
  source_kind?: string; vehicle_positions: Record<string, Position>;
  events: ReplayEvent[];
  in_transit_vehicle_ids?: string[]; completed_order_ids?: string[];
  completed_operation_ids?: string[]; active_operation_ids?: string[];
};
const route = (runId: string) => `/integration/runs/${encodeURIComponent(runId)}/simulation`;
export function loadSimulation(runId: string, signal?: AbortSignal) { return request<Simulation>(route(runId), { signal }); }
export function startSimulation(runId: string) { return request<Simulation>(route(runId), { method: 'POST', body: '{}' }); }
export function loadSimulationState(runId: string, timeS: number, view: 'active' | 'baseline' | 'candidate', signal?: AbortSignal) {
  return request<SimulationState>(`${route(runId)}/state-at?time_s=${Math.floor(timeS)}&view=${view}`, { signal });
}
export function submitDelay(runId: string, vehicleId: string, timeS: number, delayS: number, reason: string) {
  return request<SimIncident>(`${route(runId)}/incidents`, { method: 'POST', body: JSON.stringify({
    vehicle_id: vehicleId, time_s: timeS, delay_s: delayS, reason,
    source_event_id: crypto.randomUUID(), budget_ms: 2000,
  }) });
}
export function decideDelay(runId: string, incident: SimIncident, action: 'approve' | 'reject') {
  return request<SimIncident>(`${route(runId)}/incidents/${encodeURIComponent(incident.id)}/${action}`, {
    method: 'POST', body: JSON.stringify({ expected_row_version: incident.row_version }),
  });
}
export const runKey = 'integration_last_run';
export const short = (value?: string | null) => value ? `${value.slice(0, 8)}…${value.slice(-4)}` : '—';

/** Map persisted solver-ordered segments to the EXISTING schematic 3D renderer. */
export function tracksToTwinRoutes(tracks: VehicleTrack[]): TwinRoute[] {
  return tracks.map(track => {
    const segments = track.segments.filter(s => typeof s.from_node_id === 'string' && typeof s.to_node_id === 'string'
      && Number.isFinite(s.start_s) && Number.isFinite(s.end_s) && s.end_s >= s.start_s);
    if (!segments.length) return null;
    const stops: TwinRoute['stops'] = [{ nodeId: segments[0].from_node_id, kind: 'depot_start', arrivalS: segments[0].start_s,
      departureS: segments[0].start_s, orderIds: [] }];
    for (const segment of segments) {
      const last = stops[stops.length - 1];
      if (last.nodeId !== segment.from_node_id) stops.push({ nodeId: segment.from_node_id, kind: 'delivery',
        arrivalS: segment.start_s, departureS: segment.start_s, orderIds: [] });
      else last.departureS = Math.max(last.arrivalS, segment.start_s);
      stops.push({ nodeId: segment.to_node_id, kind: segment.to_node_id === track.end_node_id ? 'depot_end' : 'delivery', arrivalS: segment.end_s,
        departureS: segment.end_s, orderIds: [] });
    }
    return { vehicleId: track.vehicle_id, zone: 'chilled' as const, warehouseId: segments[0].from_node_id,
      distanceM: 0, durationS: Math.max(0, segments[segments.length - 1].end_s - segments[0].start_s), stops };
  }).filter(value => value !== null) as TwinRoute[];
}

export function selectIncident(sim: Simulation | null): SimIncident | null {
  if (!sim) return null;
  return sim.incident ?? sim.incidents?.[0] ?? null;
}
export function candidateAllowed(incident: SimIncident | null): boolean {
  return Boolean(incident && incident.proposal_valid === true && incident.status === 'pending');
}
