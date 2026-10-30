import { describe, expect, it } from 'vitest';
import { candidateAllowed, selectIncident, tracksToTwinRoutes } from './api';
import type { Simulation } from './api';

const run: Simulation = {
  simulation_id: 'sim-1', horizon_s: 700, active_version: 0,
  tracks: [{ vehicle_id: 'vehicle-1', end_node_id: 'depot', segments: [
    { from_node_id: 'depot', to_node_id: 'market', start_s: 100, end_s: 220 },
    { from_node_id: 'market', to_node_id: 'depot', start_s: 240, end_s: 400 },
  ] }], events: [],
  reconciliation: { passed: true, scope_orders: 1 },
};

describe('Stage B: persistence-backed simulated transport', () => {
  it('adapts Stage A route segments to existing 3D route geometry without changing order or timestamps', () => {
    const [route] = tracksToTwinRoutes(run.tracks);
    expect(route.vehicleId).toBe('vehicle-1');
    expect(route.stops.map(stop => stop.nodeId)).toEqual(['depot', 'market', 'depot']);
    expect(route.stops[0].departureS).toBe(100);
    expect(route.stops[1].arrivalS).toBe(220);
    expect(route.stops[1].departureS).toBe(240);
    expect(route.stops[2].arrivalS).toBe(400);
  });
  it('rejects unusable track spans rather than fabricating coordinates', () => {
    expect(tracksToTwinRoutes([{ vehicle_id: 'bad', end_node_id: 'B', segments: [
      { from_node_id: 'A', to_node_id: 'B', start_s: 8, end_s: 4 },
    ] }])).toEqual([]);
  });
  it('only enables approval for a pending independently validated proposal', () => {
    const proposed = { id: 'incident', status: 'pending' as const, row_version: 0, proposal_valid: true };
    expect(candidateAllowed(proposed)).toBe(true);
    expect(candidateAllowed({ ...proposed, proposal_valid: false })).toBe(false);
    expect(candidateAllowed({ ...proposed, status: 'approved' })).toBe(false);
    expect(candidateAllowed(null)).toBe(false);
  });
  it('keeps incident information associated with the same simulation', () => {
    expect(selectIncident(run)).toBeNull();
    expect(selectIncident({ ...run, incident: { id: 'event-1', status: 'approved', row_version: 1 } })?.id).toBe('event-1');
  });
});
