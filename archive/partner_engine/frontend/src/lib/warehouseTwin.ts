/** R26 single-warehouse visualization projection. Never changes solver/database records.
 * Demo jobs and rack occupancy are explicitly synthetic, not WMS telemetry.
 */
import type { CandidatePlan, Snapshot } from '../appTypes';

export type TwinZoneId = 'receiving' | 'quality' | 'chilled' | 'frozen' | 'picking' | 'staging' | 'dock' | 'charging';
export type TwinMode = 'showcase' | 'plan';
export type GroundPoint = { x: number; z: number };
export type TwinZone = { id: TwinZoneId; name: string; temp: string; x: number; z: number; width: number; depth: number; color: number };
export type TwinRack = { id: string; zone: 'chilled' | 'frozen'; x: number; z: number; levels: number; bays: number; occupied: number };
export type TwinForkliftJob = {
  id: string; forkliftId: string; rackId: string; batchId: string; orderId: string;
  startS: number; endS: number; source: 'synthetic' | 'planned_timing';
};
export type TwinWarehouseData = {
  warehouseId: string;
  origin: 'synthetic_demo' | 'snapshot_projection';
  zones: TwinZone[]; racks: TwinRack[]; jobs: TwinForkliftJob[];
  stockLots: number; scheduledOps: number; handoffs: number;
  warehouseWarning: string | null;
};
export type ForkliftStage = 'waiting' | 'to_rack' | 'pickup' | 'to_dock' | 'dropoff' | 'returning' | 'done';
export type ForkliftPose = { x: number; z: number; heading: number; lift: number; carrying: boolean; stage: ForkliftStage; job: TwinForkliftJob | null };

export const ZONES: TwinZone[] = [
  { id: 'receiving', name: '收货区', temp: '到货验收', x: -24.5, z: -11.5, width: 9, depth: 12, color: 0x8a8f85 },
  { id: 'quality', name: '质检区', temp: '质量检验', x: -24.5, z: 1, width: 9, depth: 11, color: 0xb7943f },
  { id: 'chilled', name: '冷藏区', temp: '2–8°C · 演示设定', x: -9.5, z: -10.0, width: 19, depth: 18, color: 0x3f9a62 },
  { id: 'frozen', name: '冷冻区', temp: '-18°C · 演示设定', x: 11.5, z: -10.0, width: 19, depth: 18, color: 0xd4d6d0 },
  { id: 'picking', name: '分拣复核区', temp: '出库复核', x: -5.5, z: 9, width: 17, depth: 12, color: 0x6e7368 },
  { id: 'staging', name: '出库暂存区', temp: '待装车', x: 11.5, z: 9, width: 15, depth: 12, color: 0xc98a2a },
  { id: 'dock', name: '装卸月台', temp: '冷链交接', x: 25.5, z: 9, width: 9, depth: 12, color: 0x5c7d4a },
  { id: 'charging', name: '叉车充电区', temp: '设备待命', x: -23.5, z: 13, width: 11, depth: 9, color: 0x575a54 },
];

export const FORKLIFT_IDS = ['FK-01', 'FK-02', 'FK-03'] as const;
export const CHARGING_POINTS: GroundPoint[] = [{ x: -26, z: 12 }, { x: -23, z: 15 }, { x: -20, z: 12 }];

function racks(): TwinRack[] {
  const out: TwinRack[] = [];
  for (const zone of ['chilled', 'frozen'] as const) {
    for (let row = 0; row < 3; row++) for (let col = 0; col < 4; col++) {
      const id = `${zone === 'chilled' ? 'C' : 'F'}-R${row + 1}-B${String(col + 1).padStart(2, '0')}`;
      out.push({ id, zone, x: (zone === 'chilled' ? -16 : 5) + col * 4.0,
        z: -16.1 + row * 5.3, levels: 3, bays: 3,
        occupied: ((col * 7 + row * 5 + (zone === 'frozen' ? 3 : 1)) % 10) / 10 });
    }
  }
  return out;
}

const DEFAULT_RACKS = racks();

export function warehouseTwinData(snapshot: Snapshot | null, plan: CandidatePlan | null, mode: TwinMode): TwinWarehouseData {
  const active = snapshot?.warehouses ?? [];
  // Keep the display single-depot even if the user re-opens a historical snapshot.
  // A warning explains it rather than pretending that the underlying data was migrated.
  const warehouse = active.find((w) => w.warehouse_id === 'wh_1') ?? active[0];
  const warehouseId = warehouse?.warehouse_id ?? 'wh_1';
  const lots = (snapshot?.stock_lots ?? []).filter((x) => x.warehouse_id === warehouseId);
  const ops = plan?.warehouse.operations ?? [];
  const handoffs = plan?.warehouse.warehouse_handoffs ?? [];
  const chosen = DEFAULT_RACKS;
  let jobs: TwinForkliftJob[] = [];
  if (mode === 'showcase') {
    jobs = Array.from({ length: 9 }, (_, i) => ({
      id: `DEMO-FJ-${String(i + 1).padStart(2, '0')}`,
      forkliftId: FORKLIFT_IDS[i % 3], rackId: chosen[(i * 5 + 1) % chosen.length].id,
      batchId: lots[i % (lots.length || 1)]?.batch_id ?? `DEMO-LOT-${i + 1}`,
      orderId: snapshot?.orders[i % (snapshot.orders.length || 1)]?.order_id ?? `DEMO-ORDER-${i + 1}`,
      startS: i * 155 + (i % 3) * 15, endS: i * 155 + (i % 3) * 15 + 380,
      source: 'synthetic',
    }));
  } else {
    const operations = ops.filter((op) => op.end_s > op.start_s).sort((a,b) => a.start_s-b.start_s);
    const freeAt = [0, 0, 0];
    const sourceOperations = new Map((snapshot?.operations ?? []).map(op => [op.operation_id, op]));
    const sourceOrders = new Map((snapshot?.orders ?? []).map(order => [order.order_id, order]));
    // Preserve the CP-SAT timestamps exactly. If all three visual forklifts are
    // busy, omit extra operations instead of fabricating another machine or
    // silently shifting a solver-produced time window.
    for (const op of operations.slice(0, 32)) {
      const forkliftIdx = freeAt.findIndex(t => t <= op.start_s);
      if (forkliftIdx < 0 || jobs.length >= 18) continue;
      freeAt[forkliftIdx] = op.end_s;
      const i = jobs.length;
      const sourceOp = sourceOperations.get(op.operation_id);
      const orderId = sourceOp?.order_ids[0] ?? '未关联订单';
      const order = sourceOrders.get(orderId);
      const shelfCandidates = chosen.filter(rack => rack.zone === order?.temperature_zone);
      const displayRack = shelfCandidates.length ? shelfCandidates[i % shelfCandidates.length] : chosen[(i * 5 + 1) % chosen.length];
      jobs.push({ id: op.operation_id, forkliftId: FORKLIFT_IDS[forkliftIdx],
        rackId: displayRack.id,
        batchId: order?.batch_id ?? '未关联批次',
        orderId,
        startS: op.start_s, endS: op.end_s, source: 'planned_timing' });
    }
  }
  return { warehouseId, origin: mode === 'showcase' ? 'synthetic_demo' : 'snapshot_projection',
    zones: ZONES, racks: chosen, jobs, stockLots: lots.length, scheduledOps: ops.length, handoffs: handoffs.length,
    warehouseWarning: active.length > 1 ? `当前旧快照仍包含 ${active.length} 座仓库；本页仅展示 ${warehouseId}，请重新导入 R26 单仓场景。` : null };
}

const lerp = (a: GroundPoint, b: GroundPoint, ratio: number): GroundPoint => ({ x: a.x + (b.x - a.x) * ratio, z: a.z + (b.z - a.z) * ratio });
function follow(points: GroundPoint[], f: number): GroundPoint & { heading: number } {
  const lengths = points.slice(1).map((p,i) => Math.hypot(p.x-points[i].x, p.z-points[i].z));
  const full = lengths.reduce((a,b) => a+b,0);
  let target = Math.min(1,Math.max(0,f))*full;
  for (let i=0;i<lengths.length;i++) {
    if (target <= lengths[i] || i === lengths.length-1) {
      const a=points[i], b=points[i+1]; const p=lerp(a,b,lengths[i] ? target/lengths[i] : 0);
      return { ...p, heading: Math.atan2(-(b.z-a.z),b.x-a.x) };
    }
    target-=lengths[i];
  }
  return { ...points[0], heading: 0 };
}

export function forkliftPose(id: string, timeS: number, jobs: TwinForkliftJob[], layout: TwinRack[]): ForkliftPose {
  const index = FORKLIFT_IDS.indexOf(id as typeof FORKLIFT_IDS[number]);
  const home = CHARGING_POINTS[Math.max(0,index)];
  const ownJobs = jobs.filter((j) => j.forkliftId===id).sort((a,b) => a.startS-b.startS);
  let rest = home;
  for (const job of ownJobs) {
    const rack = layout.find((r)=>r.id===job.rackId);
    if (!rack) continue;
    const pickup = {x:rack.x, z:rack.z+1.7};
    const dock = {x:24.8-(index*2.4),z:9.0+(index-1)*3.2};
    const start = {x:rest.x,z:rest.z};
    if (timeS < job.startS) break;
    const p=(timeS-job.startS)/Math.max(1,job.endS-job.startS);
    if (p<=1) {
      if (p<0.28) { const q=follow([start,{x:start.x,z:0.0},{x:pickup.x,z:0.0},pickup],p/0.28);
        return {...q,lift:0.2,carrying:false,stage:'to_rack',job}; }
      if (p<0.38) return {...pickup,heading:-Math.PI/2,lift:0.2+(p-0.28)/0.1*1.1,carrying:p>=0.32,stage:'pickup',job};
      if (p<0.76) {const q=follow([pickup,{x:pickup.x,z:1.1},{x:8,z:1.1},{x:8,z:9},{x:dock.x,z:9},dock],(p-0.38)/0.38);
        return {...q,lift:1.2,carrying:true,stage:'to_dock',job};}
      if (p<0.84) return {...dock,heading:0,lift:1.2-(p-0.76)/0.08,carrying:p<0.81,stage:'dropoff',job};
      const q=follow([dock,{x:dock.x,z:18},{x:start.x,z:18},start],(p-0.84)/0.16);
      return {...q,lift:0.2,carrying:false,stage:'returning',job};
    }
    rest=start;
  }
  return {...rest,heading:0,lift:0.2,carrying:false,stage:ownJobs.length && timeS>=ownJobs[ownJobs.length-1].endS ? 'done' : 'waiting',job:null};
}

export const STAGE_LABELS: Record<ForkliftStage,string> = {
  waiting:'待命',to_rack:'前往库位',pickup:'取货举升',to_dock:'搬运至月台',dropoff:'月台卸货',returning:'返回充电区',done:'任务完成',
};
