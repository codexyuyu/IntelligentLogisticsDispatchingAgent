/** R25 deterministic, allocation-light, time-based path sampling. No Three.js/React. */
import type { TwinRoute, TwinRouteStop } from '../appTypes';
import type { Vec2 } from './twin';

export type Leg = { fromS: number; untilS: number; points: Vec2[]; cumulative: number[]; length: number };
export type RouteMotion = { legs: Leg[]; start: Vec2; end: Vec2 };

export function roadLikeLeg(a: Vec2, b: Vec2, offset = 0): Vec2[] {
  // Diagram roads ONLY. Right-angled streets are not claimed to be OSRM geometry.
  if (Math.abs(a.x - b.x) < 0.01 || Math.abs(a.z - b.z) < 0.01) return [a, b];
  return offset % 2 === 0
    ? [a, { x: b.x, z: a.z }, b]
    : [a, { x: a.x, z: b.z }, b];
}

function leg(fromS: number, untilS: number, points: Vec2[]): Leg {
  const cumulative = [0];
  for (let i = 1; i < points.length; i++) {
    cumulative.push(cumulative[i - 1] + Math.hypot(points[i].x - points[i - 1].x, points[i].z - points[i - 1].z));
  }
  return { fromS, untilS, points, cumulative, length: cumulative[cumulative.length - 1] };
}

function nearestForward(points: Vec2[], sought: Vec2, minIndex: number, isFinal: boolean): number {
  let best = minIndex;
  let dist = Number.POSITIVE_INFINITY;
  const until = isFinal ? points.length : points.length - 1;
  for (let i = minIndex; i < until; i++) {
    const d = (points[i].x - sought.x) ** 2 + (points[i].z - sought.z) ** 2;
    if (d < dist) { best = i; dist = d; }
  }
  return best;
}

export function buildRouteMotion(route: TwinRoute, positions: Record<string, Vec2>, roadPoints?: Vec2[]): RouteMotion | null {
  const stops = route.stops.filter((s) => Boolean(positions[s.nodeId]));
  if (stops.length < 2) return null;
  const legs: Leg[] = [];
  let indexes: number[] = [];
  if (roadPoints && roadPoints.length >= 2 && route.stopCoordinates?.length === stops.length) {
    // Stop coordinates already projected into `positions`; match points along the
    // solver-ordered road polyline, never re-order its stops.
    let cursor = 0;
    indexes = stops.map((stop, i) => {
      const k = nearestForward(roadPoints, positions[stop.nodeId], cursor, i === stops.length - 1);
      cursor = Math.min(k + 1, roadPoints.length - 1);
      return k;
    });
    indexes[indexes.length - 1] = roadPoints.length - 1;
  }
  for (let i = 0; i < stops.length - 1; i++) {
    const previous: TwinRouteStop = stops[i];
    const next: TwinRouteStop = stops[i + 1];
    const points = roadPoints && indexes.length
      ? roadPoints.slice(indexes[i], Math.max(indexes[i] + 2, indexes[i + 1] + 1))
      : roadLikeLeg(positions[previous.nodeId], positions[next.nodeId], i);
    if (points.length < 2) points.push(positions[next.nodeId]);
    legs.push(leg(previous.departureS, next.arrivalS, points));
  }
  return { legs, start: positions[stops[0].nodeId], end: positions[stops[stops.length - 1].nodeId] };
}

export type MotionPoint = { x: number; z: number; heading: number; moving: boolean };
export function sampleMotion(motion: RouteMotion, timeS: number): MotionPoint {
  const fallback = { x: motion.start.x, z: motion.start.z, heading: 0, moving: false };
  for (const item of motion.legs) {
    if (timeS < item.fromS) return fallback;
    if (timeS <= item.untilS) {
      if (item.length <= 0) return fallback;
      const ratio = item.untilS > item.fromS ? Math.min(1, Math.max(0, (timeS - item.fromS) / (item.untilS - item.fromS))) : 1;
      const target = ratio * item.length;
      let lo = 1, hi = item.cumulative.length - 1;
      while (lo < hi) {
        const mid = (lo + hi) >>> 1;
        if (item.cumulative[mid] < target) lo = mid + 1;
        else hi = mid;
      }
      const index = lo;
      const begin = item.points[index - 1], end = item.points[index];
      const length = item.cumulative[index] - item.cumulative[index - 1];
      const f = length > 0 ? (target - item.cumulative[index - 1]) / length : 0;
      return { x: begin.x + (end.x - begin.x) * f, z: begin.z + (end.z - begin.z) * f,
        heading: Math.atan2(-(end.z - begin.z), end.x - begin.x), moving: timeS > item.fromS && timeS < item.untilS };
    }
    fallback.x = item.points[item.points.length - 1].x;
    fallback.z = item.points[item.points.length - 1].z;
    fallback.moving = false;
  }
  return fallback;
}

export function geoProjection(routes: TwinRoute[]): ((lng: number, lat: number) => Vec2) | null {
  const all = routes.flatMap((r) => r.roadCoordinates ?? []);
  if (all.length < 2) return null;
  const lng0 = all.reduce((s, p) => s + p[0], 0) / all.length;
  const lat0 = all.reduce((s, p) => s + p[1], 0) / all.length;
  const scaleX = Math.cos(lat0 * Math.PI / 180);
  let range = 0.000001;
  for (const point of all) range = Math.max(range, Math.abs((point[0] - lng0) * scaleX), Math.abs(point[1] - lat0));
  return (lng, lat) => ({ x: (lng - lng0) * scaleX / range * 29, z: -(lat - lat0) / range * 29 });
}
