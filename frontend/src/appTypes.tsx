
import type { components } from './client/generated';

export type Snapshot = components['schemas']['PlanningSnapshot'];
export type Order = components['schemas']['Order'];
export type CandidatePlan = components['schemas']['CandidatePlan'];
export type JobResponse = components['schemas']['JobResponse'];
export type PlanResponse = components['schemas']['PlanResponse'];
export type RoutingResult = components['schemas']['RoutingResult'];
export type WarehouseScheduleResult = components['schemas']['WarehouseScheduleResult'];
export type VehicleRoute = components['schemas']['VehicleRoute'];
export type RouteStop = components['schemas']['RouteStop'];
export type SolveMetadata = components['schemas']['SolveMetadata'];
export type ValidationReport = components['schemas']['ValidationReport'];
export type Vehicle = components['schemas']['Vehicle'];
export type WarehouseResource = components['schemas']['WarehouseResource'];
export type Warehouse = components['schemas']['Warehouse'];
export type TravelMatrix = components['schemas']['TravelMatrix'];
export type StockLot = components['schemas']['StockLot'];

// API exchange types are aliases of the generated backend schema.
export type CoordinationRoundWire = components['schemas']['CoordinationRound'];
export type CoordinationReportWire = components['schemas']['CoordinationReport'];
export type EventPayloadWire = components['schemas']['EventPayload'];
export type DispatchEventWire = components['schemas']['DispatchEvent'];
export type ImpactAnalysisWire = components['schemas']['ImpactAnalysis'];
export type PlanDiffWire = components['schemas']['PlanDiff'];
export type LocalRescheduleResultWire = components['schemas']['LocalRescheduleResult'];
export type EventAcceptedWire = components['schemas']['EventAccepted'];
export type SimulationResultWire = components['schemas']['SimulationResult'];
export type CoordinatedPlan = CandidatePlan;
export type EventType = DispatchEventWire['event_type'];

export type SimulationResponseWire = {
  simulation: SimulationResultWire;
  status: 'completed';
};

export type AppNotice = {
  kind: 'success' | 'error' | 'info';
  text: string;
};

// ---- derived view models shared by pages (all fields traced back to API data) ----

export type TwinRouteStop = {
  nodeId: string;
  kind: RouteStop['stop_kind'];
  arrivalS: number;
  departureS: number;
  orderIds: string[];
};

export type TwinRoute = {
  vehicleId: string;
  zone: 'chilled' | 'frozen';
  warehouseId: string;
  distanceM: number;
  durationS: number;
  stops: TwinRouteStop[];
  /** OSRM full-route GeoJSON polyline when actually fetched from a road service. */
  roadCoordinates?: [number, number][];
  /** OSRM waypoint coordinates in exact route-stop order. */
  stopCoordinates?: [number, number][];
};

export function routesToTwinRoutes(plan: CandidatePlan | null | undefined, vehicles: Vehicle[]): TwinRoute[] {
  if (!plan) return [];
  const zoneByVehicle = new Map(vehicles.map((v) => [v.vehicle_id, v.temperature_zone]));
  const whByVehicle = new Map(vehicles.map((v) => [v.vehicle_id, v.warehouse_id]));
  return plan.routing.routes.map((route) => ({
    vehicleId: route.vehicle_id,
    zone: zoneByVehicle.get(route.vehicle_id) ?? 'chilled',
    warehouseId: whByVehicle.get(route.vehicle_id) ?? '',
    distanceM: route.distance_m,
    durationS: route.duration_s,
    stops: route.stops.map((stop) => ({
      nodeId: stop.node_id,
      kind: stop.stop_kind,
      arrivalS: stop.arrival_at_s,
      departureS: stop.departure_at_s,
      orderIds: [...stop.order_ids],
    })),
  }));
}
