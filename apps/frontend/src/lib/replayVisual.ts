/** Pure visual-layout helpers. Never affect solver routes, state or timing. */
import type { Vec2 } from './twin';
import type { TwinRoute } from '../appTypes';
import { sampleMotion, type MotionPoint, type RouteMotion } from './replayPaths';

export const TRUCK_COLORS = [0x2d9b80, 0x398bd1, 0xd99a42, 0x9c83d6, 0xd46873, 0x57aeb4, 0x859b55];

export function vehicleDisplayName(vehicleId: string, routes: TwinRoute[]): string {
  const index = routes.findIndex(route => route.vehicleId === vehicleId);
  return index >= 0 ? `冷链车 ${String(index + 1).padStart(2, '0')}` : '冷链车辆';
}

export function routeDisplayColor(vehicleId: string, routes: TwinRoute[]): number {
  const index = routes.findIndex(route => route.vehicleId === vehicleId);
  return TRUCK_COLORS[(index < 0 ? 0 : index) % TRUCK_COLORS.length];
}

export function currentLegIndex(motion: RouteMotion, timeS: number): number {
  return motion.legs.findIndex(leg => timeS >= leg.fromS && timeS <= leg.untilS);
}

export function vehicleReplayStatus(motion: RouteMotion, timeS: number): 'waiting' | 'moving' | 'stopped' | 'completed' {
  if (!motion.legs.length) return 'waiting';
  if (timeS < motion.legs[0].fromS) return 'waiting';
  if (timeS >= motion.legs[motion.legs.length - 1].untilS) return 'completed';
  return currentLegIndex(motion, timeS) >= 0 ? 'moving' : 'stopped';
}

/**
 * Give vehicles occupying a common schematic depot/road a stable VISUAL lane.
 * Do not mutate motion geometry, event times or authoritative node positions.
 */
export function visualVehiclePose(
  motion: RouteMotion,
  timeS: number,
  laneIndex: number,
  laneCount: number,
  depot: Vec2,
  isSchematic: boolean,
): MotionPoint {
  const p = sampleMotion(motion, timeS);
  if (!isSchematic || laneCount <= 1) return p;
  const slot = laneIndex - (laneCount - 1) / 2;
  const status = vehicleReplayStatus(motion, timeS);
  const parked = { x: depot.x + 5.1 + Math.floor(laneIndex / 4) * 2.5,
    z: depot.z - 4.4 + (laneIndex % 4) * 2.65 };
  const atDepot = Math.hypot(p.x - depot.x, p.z - depot.z) < 0.1;
  if ((status === 'waiting' || status === 'completed') && atDepot) {
    return { ...p, ...parked };
  }
  // Merge gracefully from the parking bay onto the actual route. The visual
  // approach is deliberately short and is NOT added to solver travel time.
  const first = motion.legs[0];
  const last = motion.legs[motion.legs.length - 1];
  if (first && timeS >= first.fromS && timeS < first.fromS + 8 &&
      Math.hypot(motion.start.x - depot.x, motion.start.z - depot.z) < 0.1) {
    const weight = Math.max(0, 1 - (timeS - first.fromS) / 8);
    return { ...p, x: p.x + (parked.x - depot.x) * weight,
      z: p.z + (parked.z - depot.z) * weight };
  }
  if (last && timeS > last.untilS - 8 && timeS < last.untilS &&
      Math.hypot(motion.end.x - depot.x, motion.end.z - depot.z) < 0.1) {
    const weight = Math.min(1, (timeS - (last.untilS - 8)) / 8);
    return { ...p, x: p.x + (parked.x - depot.x) * weight,
      z: p.z + (parked.z - depot.z) * weight };
  }
  // Both trucks use exactly the same logical path; offset ONLY their visible
  // mesh by a lane amount. Solver times/distances and node IDs are unchanged.
  return { ...p, x: p.x + Math.sin(p.heading) * slot * 1.28,
    z: p.z + Math.cos(p.heading) * slot * 1.28 };

}

export function countDistinctVehicles(routes: TwinRoute[]): number {
  return new Set(routes.map(route => route.vehicleId)).size;
}
