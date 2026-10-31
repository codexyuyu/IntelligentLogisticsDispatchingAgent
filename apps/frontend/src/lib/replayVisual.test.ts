import { describe, expect, it } from 'vitest';
import type { TwinRoute } from '../appTypes';
import { buildRouteMotion } from './replayPaths';
import { countDistinctVehicles, vehicleDisplayName, vehicleReplayStatus, visualVehiclePose } from './replayVisual';

const positions = { depot: { x: -16, z: 0 }, a: { x: 14, z: 0 } };
const route = (id: string): TwinRoute => ({ vehicleId: id, warehouseId: 'depot', zone: 'chilled', distanceM: 1000, durationS: 100,
  stops: [
    { nodeId: 'depot', kind: 'depot_start', arrivalS: 0, departureS: 10, orderIds: [] },
    { nodeId: 'a', kind: 'delivery', arrivalS: 90, departureS: 95, orderIds: [] },
  ],
});

describe('transport replay vehicle independence', () => {
  it('counts distinct trucks and gives each a stable label', () => {
    expect(countDistinctVehicles([route('v1'), route('v2')])).toBe(2);
    expect(vehicleDisplayName('v2', [route('v1'), route('v2')])).toBe('冷链车 02');
  });
  it('separates parked trucks without changing their logical path', () => {
    const motion = buildRouteMotion(route('v1'), positions)!;
    const first = visualVehiclePose(motion, 0, 0, 2, positions.depot, true);
    const second = visualVehiclePose(motion, 0, 1, 2, positions.depot, true);
    expect(first.z).not.toBe(second.z);
    expect(motion.start).toEqual(positions.depot);
    expect(vehicleReplayStatus(motion, 0)).toBe('waiting');
  });
  it('makes co-timed vehicles visible in separate schematic lanes', () => {
    const motion = buildRouteMotion(route('v1'), positions)!;
    const first = visualVehiclePose(motion, 40, 0, 2, positions.depot, true);
    const second = visualVehiclePose(motion, 40, 1, 2, positions.depot, true);
    expect(Math.hypot(first.x - second.x, first.z - second.z)).toBeGreaterThan(0.6);
    expect(vehicleReplayStatus(motion, 40)).toBe('moving');
  });
  it('keeps real road geometry on the authoritative unshifted motion', () => {
    const motion = buildRouteMotion(route('v1'), positions)!;
    const first = visualVehiclePose(motion, 40, 0, 2, positions.depot, false);
    const second = visualVehiclePose(motion, 40, 1, 2, positions.depot, false);
    expect(first).toEqual(second);
  });
});
