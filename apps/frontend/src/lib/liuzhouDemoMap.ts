/**
 * Fixed LIUZHOU DEMO georeferencing. No geocoder, AMap key, GPS or routing API.
 * Coordinates use WGS84 for OpenStreetMap. The campus anchor is an approximate
 * GCJ-02 -> WGS84 conversion of the published Wenchang-campus AMap POI; it is
 * NOT a surveyed warehouse position. All other POIs are FICTITIOUS demo stops.
 * Solver stops/timing remain authoritative; the map polyline is presentation only.
 */
import type { TwinRoute } from '../appTypes';

export type LatLng = [number, number];
export type DemoMapNode = { id: string; point: LatLng; label: string; isDepot: boolean };
export type DemoMapLeg = { fromS: number; toS: number; points: LatLng[]; cum: number[]; length: number };
export type DemoMapMotion = { vehicleId: string; legs: DemoMapLeg[]; start: LatLng; end: LatLng; stops: TwinRoute['stops']; polyline: LatLng[] };
export type DemoPose = { point: LatLng; headingDeg: number; state: 'waiting' | 'driving' | 'unloading' | 'completed'; nextNodeId: string | null };

export const WENCHANG_CAMPUS: LatLng = [24.33261, 109.44196];
// A *virtual* demonstration depot near the campus' southern side, not a claim
// of a real warehouse or permission to dispatch trucks inside the university.
export const DEMO_DEPOT: LatLng = [24.3269, 109.4453];

const DEMO_STOPS: LatLng[] = [
  [24.3435, 109.4210], [24.3511, 109.4487],
  [24.3427, 109.4701], [24.3277, 109.4760],
  [24.3107, 109.4665], [24.3077, 109.4437],
  [24.3192, 109.4207], [24.3371, 109.4088],
  [24.3573, 109.4331], [24.3534, 109.4723],
  [24.3018, 109.4258], [24.3210, 109.4851],
];

function round(v: number): number { return Math.round(v * 1e7) / 1e7; }
function isLatLng(coord: unknown): coord is LatLng {
  return Array.isArray(coord) && coord.length === 2 && Number.isFinite(coord[0]) && Number.isFinite(coord[1]);
}

/** The union of base/candidate stops MUST be passed to keep node placement stable between views. */
export function createDemoNodes(routes: TwinRoute[], allNodeIds: string[] = []): Record<string, DemoMapNode> {
  const firstStops = new Set(routes.map(route => route.stops[0]?.nodeId).filter((id): id is string => Boolean(id)));
  const lastStops = new Set(routes.map(route => route.stops.at(-1)?.nodeId).filter((id): id is string => Boolean(id)));
  // Depot is inferred from actual first stops; do not guess from opaque UUIDs.
  const depotIds = new Set([...firstStops, ...[...lastStops].filter(id => firstStops.has(id))]);
  const ids = [...new Set([...allNodeIds, ...routes.flatMap(route => route.stops.map(stop => stop.nodeId))])].sort();
  const regular = ids.filter(id => !depotIds.has(id));
  const nodes: Record<string, DemoMapNode> = {};
  [...depotIds].sort().forEach((id, i) => {
    nodes[id] = { id, point: [round(DEMO_DEPOT[0] + i * 0.00045), round(DEMO_DEPOT[1] + i * 0.00052)],
      label: i ? `虚拟仓库 ${i + 1}` : '文昌校区附近 · 虚拟配送中心', isDepot: true };
  });
  regular.forEach((id, i) => {
    const point = DEMO_STOPS[i] ?? (() => {
      const theta = (i - DEMO_STOPS.length) * 2.39996;
      const radius = 0.027 + 0.004 * Math.floor((i - DEMO_STOPS.length) / 10);
      return [WENCHANG_CAMPUS[0] + radius * Math.sin(theta), WENCHANG_CAMPUS[1] + radius * Math.cos(theta)] as LatLng;
    })();
    nodes[id] = { id, point, label: `模拟配送点 ${String(i + 1).padStart(2, '0')}`, isDepot: false };
  });
  return nodes;
}

function distance(a: LatLng, b: LatLng): number {
  const latFactor = 111_000, lngFactor = 111_000 * Math.cos(((a[0] + b[0]) / 2) * Math.PI / 180);
  return Math.hypot((b[0] - a[0]) * latFactor, (b[1] - a[1]) * lngFactor);
}
function near(a: LatLng, b: LatLng): boolean { return distance(a, b) < 1; }
function pushPoint(points: LatLng[], point: LatLng) {
  if (!points.length || !near(points[points.length - 1], point)) points.push(point);
}

/**
 * Geographically coherent but synthetic corridors. These lines are NOT
 * calculated against the OSM road network; they may not follow each street.
 * They will be replaceable with provider routing leg geometry later.
 */
export function demoLegGeometry(a: LatLng, b: LatLng, salt: number): LatLng[] {
  if (near(a, b)) return [a, b];
  const horizontalFirst = salt % 2 === 0;
  const midLat = round((a[0] + b[0]) / 2);
  const midLng = round((a[1] + b[1]) / 2);
  const points: LatLng[] = [a];
  if (horizontalFirst) {
    pushPoint(points, [a[0] * 0.78 + midLat * 0.22, midLng]);
    pushPoint(points, [midLat, midLng]);
    pushPoint(points, [midLat, b[1] * 0.80 + midLng * 0.20]);
  } else {
    pushPoint(points, [midLat, a[1] * 0.80 + midLng * 0.20]);
    pushPoint(points, [midLat, midLng]);
    pushPoint(points, [b[0] * 0.78 + midLat * 0.22, midLng]);
  }
  pushPoint(points, b);
  return points;
}

function lengthTable(points: LatLng[]): { cum: number[]; length: number } {
  const cum = [0];
  for (let i = 1; i < points.length; i++) cum.push(cum[i-1] + distance(points[i-1], points[i]));
  return { cum, length: cum[cum.length - 1] };
}

export function buildDemoMotion(route: TwinRoute, nodes: Record<string, DemoMapNode>): DemoMapMotion | null {
  const stops = route.stops.filter(stop => Boolean(nodes[stop.nodeId]));
  if (!stops.length) return null;
  const legs: DemoMapLeg[] = [];
  const polyline: LatLng[] = [nodes[stops[0].nodeId].point];
  for (let i = 0; i + 1 < stops.length; i++) {
    const a = nodes[stops[i].nodeId].point, b = nodes[stops[i + 1].nodeId].point;
    // The incident showcase freezes a vehicle at an interpolated mid-arc
    // coordinate. Its geometry must be affine as well: the baseline arc and
    // its two split pieces then coincide exactly before the incident.
    // These are still synthetic paths, NOT real road navigation.
    const points = route.vehicleId.startsWith('demo-truck-') ? [a, b] :
      demoLegGeometry(a, b, i + route.vehicleId.length);
    const { cum, length } = lengthTable(points);
    legs.push({ fromS: stops[i].departureS, toS: stops[i + 1].arrivalS, points, cum, length });
    for (const point of points.slice(1)) pushPoint(polyline, point);
  }
  return { vehicleId: route.vehicleId, stops, legs, polyline,
    start: nodes[stops[0].nodeId].point, end: nodes[stops[stops.length - 1].nodeId].point };
}

function alongLeg(leg: DemoMapLeg, ratio: number): { point: LatLng; headingDeg: number } {
  const target = Math.max(0, Math.min(1, ratio)) * leg.length;
  for (let i = 1; i < leg.points.length; i++) {
    if (target <= leg.cum[i] || i === leg.points.length - 1) {
      const start = leg.points[i-1], end = leg.points[i];
      const len = leg.cum[i] - leg.cum[i-1];
      const fraction = len > 0 ? (target - leg.cum[i-1]) / len : 0;
      return { point: [start[0] + (end[0] - start[0])*fraction,
        start[1] + (end[1] - start[1])*fraction],
        headingDeg: Math.atan2(end[1] - start[1], end[0] - start[0]) * 180 / Math.PI };
    }
  }
  return { point: leg.points[0], headingDeg: 0 };
}

export function sampleDemoMotion(motion: DemoMapMotion, timeS: number): DemoPose {
  if (!motion.legs.length) return { point: motion.start, headingDeg: 0, state: 'waiting', nextNodeId: null };
  let last = motion.start;
  if (timeS < motion.legs[0].fromS) return { point: motion.start, headingDeg: 0, state: 'waiting', nextNodeId: motion.stops[1]?.nodeId ?? null };
  for (let i = 0; i < motion.legs.length; i++) {
    const leg = motion.legs[i];
    if (timeS < leg.fromS) return { point: last, headingDeg: 0, state: 'unloading', nextNodeId: motion.stops[i + 1]?.nodeId ?? null };
    if (timeS <= leg.toS) {
      const ratio = leg.toS > leg.fromS ? (timeS - leg.fromS) / (leg.toS - leg.fromS) : 1;
      const here = alongLeg(leg, ratio);
      return { ...here, state: timeS > leg.fromS && timeS < leg.toS ? 'driving' : 'unloading', nextNodeId: motion.stops[i + 1]?.nodeId ?? null };
    }
    last = leg.points[leg.points.length - 1];
  }
  return { point: motion.end, headingDeg: 0, state: 'completed', nextNodeId: null };
}

/**
 * Deterministic *display-only* parking spread. The previous algorithm moved a
 * truck suddenly by 24-88 screen pixels whenever another icon came within a
 * threshold. That made the truck appear to teleport while its solver pose was
 * moving continuously. Here the offset depends only on vehicle and time and
 * fades continuously while it leaves/enters the shared depot. On road, the
 * marker follows the route line exactly.
 */
export function visualMarkerOffset(motion: DemoMapMotion, timeS: number, index: number, count: number): {x:number;y:number} {
  if (count < 2 || !motion.legs.length) return {x:0, y:0};
  const first = motion.legs[0], last = motion.legs[motion.legs.length - 1];
  const fadeS = 45;
  const departure = Math.max(0, Math.min(1, (timeS - first.fromS) / fadeS));
  const arrival = Math.max(0, Math.min(1, (last.toS - timeS) / fadeS));
  const startFactor = 1 - departure;
  // Only spread returned vehicles if the route actually ends at its start depot.
  const depotReturn = Math.abs(motion.start[0] - motion.end[0]) < .00001 &&
    Math.abs(motion.start[1] - motion.end[1]) < .00001;
  const endFactor = depotReturn ? 1 - arrival : 0;
  const factor = Math.max(startFactor, endFactor);
  const angle = index * 2.399963229728653;
  const radius = 48 + Math.floor(index / 7) * 24;
  return {x: Math.cos(angle) * radius * factor, y: Math.sin(angle) * radius * factor};
}

export function demoRouteColor(index: number): string {
  return ['#168779', '#377bd6', '#eb8d2c', '#9062d9', '#d7586c', '#178ca9', '#8d9d39'][index % 7];
}

export function countDemoVehicles(routes: TwinRoute[]): number {
  return new Set(routes.map(route => route.vehicleId)).size;
}

export function assertDemoRouteIntegrity(route: TwinRoute, motion: DemoMapMotion): boolean {
  // A fast pure-data invariant for smoke tests: count/time/ends unchanged.
  return motion.stops.length === route.stops.length &&
    motion.legs.every((leg, i) => leg.fromS === route.stops[i].departureS && leg.toS === route.stops[i+1].arrivalS) &&
    near(motion.start, motion.polyline[0]) && near(motion.end, motion.polyline[motion.polyline.length - 1]);
}
export const isValidDemoPoint = isLatLng;

/** Presentation mode only: a separate, explicitly-labelled four-truck animation.
 * Never mix these routes into persisted solver/API results or KPI calculations. */
export function buildWenchangFourTruckShowcase(horizonS: number): TwinRoute[] {
  const horizon = Math.max(900, horizonS);
  const depot = 'wenchang_demo_depot';
  return Array.from({length:4}, (_,i) => {
    const first = `wenchang_demo_delivery_${String(i*2+1).padStart(2,'0')}`;
    const second = `wenchang_demo_delivery_${String(i*2+2).padStart(2,'0')}`;
    const startS = 25 + i * Math.min(80, Math.floor(horizon * 0.035));
    const one = Math.round(horizon * (0.26 + i*0.018));
    const two = Math.round(horizon * (0.58 + i*0.013));
    const end = Math.round(horizon * (0.81 + i*0.015));
    return { vehicleId: `SHOWCASE_TRUCK_${i+1}`, warehouseId: depot, zone: i === 3 ? 'frozen' : 'chilled',
      distanceM: 0, durationS: end-startS,
      stops: [
        {nodeId:depot, kind:'depot_start' as const, arrivalS:0, departureS:startS, orderIds:[]},
        {nodeId:first, kind:'delivery' as const, arrivalS:one, departureS:one+Math.round(horizon*.045), orderIds:[]},
        {nodeId:second, kind:'delivery' as const, arrivalS:two, departureS:two+Math.round(horizon*.035), orderIds:[]},
        {nodeId:depot, kind:'depot_end' as const, arrivalS:end, departureS:end, orderIds:[]},
      ]};
  });
}
