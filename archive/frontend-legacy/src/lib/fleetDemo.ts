/** R25 presentation ONLY: four independent trucks, not a solver output or executable plan. */
import type { Order, TwinRoute, Vehicle, Warehouse } from '../appTypes';

export function buildFourVehicleShowcase(orders: Order[], vehicles: Vehicle[], warehouses: Warehouse[]): TwinRoute[] {
  const fleet = vehicles.slice(0, 4);
  if (fleet.length !== 4 || !orders.length) return [];
  const byWarehouse = new Map(warehouses.map((w) => [w.warehouse_id, w.node_id]));
  const buckets: Order[][] = fleet.map(() => []);
  const zoneCursor = { chilled: 0, frozen: 0 };
  for (let i = 0; i < orders.length; i++) {
    const order = orders[i];
    // R26: simulated loads must at least respect each vehicle's cold-chain
    // zone; earlier round-robin assignment mixed chilled/frozen parcels.
    const zone = order.temperature_zone;
    const matches = fleet.map((v, index) => ({ v, index }))
      .filter(({ v }) => !zone || v.temperature_zone === zone);
    if (!matches.length) return []; // no fabricated compatible vehicle
    const target = zone ? matches[zoneCursor[zone]++ % matches.length].index : i % fleet.length;
    buckets[target].push(order);
  }
  return fleet.map((vehicle, index) => {
    const depot = byWarehouse.get(vehicle.warehouse_id);
    if (!depot) return null;
    const assigned = buckets[index];
    const depart = index * 75;
    const stops: TwinRoute['stops'] = [{ nodeId: depot, kind: 'depot_start', arrivalS: 0, departureS: depart, orderIds: [] }];
    assigned.forEach((order, i) => {
      const arrivalS = depart + (i + 1) * 180;
      stops.push({ nodeId: order.delivery_node_id, kind: 'delivery', arrivalS, departureS: arrivalS + 40, orderIds: [order.order_id] });
    });
    const endAt = depart + (assigned.length + 1) * 180;
    stops.push({ nodeId: depot, kind: 'depot_end', arrivalS: endAt, departureS: endAt, orderIds: [] });
    return { vehicleId: vehicle.vehicle_id, zone: vehicle.temperature_zone, warehouseId: vehicle.warehouse_id,
      distanceM: 0, durationS: endAt, stops };
  }).filter((route): route is TwinRoute => route !== null);
}
