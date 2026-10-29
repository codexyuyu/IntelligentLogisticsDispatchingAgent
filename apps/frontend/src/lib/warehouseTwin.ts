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
  sourceStartS?: number; sourceEndS?: number;
};
export type TwinWarehouseData = {
  warehouseId: string;
  origin: 'synthetic_demo' | 'snapshot_projection';
  zones: TwinZone[]; racks: TwinRack[]; jobs: TwinForkliftJob[];
  stockLots: number; scheduledOps: number; handoffs: number;
  warehouseWarning: string | null;
};
export type ForkliftStage = 'waiting' | 'yielding' | 'to_rack' | 'pickup' | 'to_dock' | 'dropoff' | 'returning' | 'done';
export type ForkliftPose = { x: number; z: number; heading: number; lift: number; reach?: number; carrying: boolean; stage: ForkliftStage; job: TwinForkliftJob | null };

export const ZONES: TwinZone[] = [
  { id: 'receiving', name: '收货区', temp: '到货验收', x: -24.5, z: -11.5, width: 9, depth: 12, color: 0x8a8f85 },
  { id: 'quality', name: '质检区', temp: '质量检验', x: -5.5, z: 4.5, width: 17, depth: 4, color: 0xb7943f },
  { id: 'chilled', name: '冷藏区', temp: '2–8°C · 演示设定', x: -9.5, z: -10.0, width: 19, depth: 18, color: 0x3f9a62 },
  { id: 'frozen', name: '冷冻区', temp: '-18°C · 演示设定', x: 11.5, z: -10.0, width: 19, depth: 18, color: 0xd4d6d0 },
  { id: 'picking', name: '分拣复核区', temp: '出库复核', x: -5.5, z: 11.5, width: 17, depth: 10, color: 0x6e7368 },
  { id: 'staging', name: '出库暂存区', temp: '待装车', x: 11.5, z: 9, width: 15, depth: 12, color: 0xc98a2a },
  { id: 'dock', name: '装卸月台', temp: '冷链交接', x: 25.5, z: 9, width: 9, depth: 12, color: 0x5c7d4a },
  { id: 'charging', name: '叉车充电区', temp: '设备待命', x: -27, z: 12, width: 8, depth: 18, color: 0x575a54 },
];

export const FORKLIFT_IDS = ['FK-01', 'FK-02', 'FK-03'] as const;
export const CHARGING_POINTS: GroundPoint[] = [{ x: -27, z: 6 }, { x: -27, z: 12 }, { x: -27, z: 18 }];

// Includes the carried pallet (nose at x=2.485), wheels and a clearance margin.
// Every travel waypoint must clear rack footprints by this turning radius.
export const FORKLIFT_CLEARANCE_RADIUS = 2.65;
export const FORKLIFT_SEPARATION = FORKLIFT_CLEARANCE_RADIUS * 2 + .1;
export const RACK_HALF_WIDTH = 1.65;
export const RACK_HALF_DEPTH = 0.775;
const RACK_ROW_SPACING = 7;
const LEFT_CORRIDOR_X = -21;
const RIGHT_CORRIDOR_X = 22;
const RETURN_AISLE_Z = 18;
export const DOCK_TRANSFER_PROGRESS = 0.83;
export const DOCK_FORK_LIFT = 0.15;
export const COLD_PARTITION_X = 1;
export const COLD_PARTITION_PANELS = [
  { startZ: -20, endZ: -16.5 },
  { startZ: -10.5, endZ: -9.5 },
  { startZ: -3.5, endZ: -2.5 },
];
export const DOCK_CONVEYOR_END_X = 38;
export const QUALITY_SORTING_PATH: GroundPoint[] = [
  {x:-13.6,z:4.8},{x:-9,z:4.8},{x:-9,z:8},{x:11.6,z:8},
];

export function dockStop(job: TwinForkliftJob, jobs: TwinForkliftJob[]): GroundPoint {
  const index = Math.max(0, FORKLIFT_IDS.indexOf(job.forkliftId as typeof FORKLIFT_IDS[number]));
  const own = jobs.filter(j => j.forkliftId === job.forkliftId).sort((a,b) => a.startS-b.startS);
  const slot = Math.max(0, own.findIndex(j => j.id === job.id));
  // Three loading positions across each powered conveyor lane.
  return { x: 25, z: 4 + index * 4.45 + (slot % 3 - 1) * 1.05 };
}

export function depositedCargo(job: TwinForkliftJob, timeS: number, jobs: TwinForkliftJob[]) {
  const stop = dockStop(job, jobs);
  return { x: stop.x + 2, z: stop.z, y: 0.08 + DOCK_FORK_LIFT,
    visible: timeS >= job.startS + (job.endS - job.startS) * DOCK_TRANSFER_PROGRESS };
}

export function conveyorPosition(index: number, timeS: number) {
  const length = QUALITY_SORTING_PATH.slice(1).reduce((sum,p,i)=>sum+Math.hypot(p.x-QUALITY_SORTING_PATH[i].x,p.z-QUALITY_SORTING_PATH[i].z),0);
  const distance = index * length / 4 + Math.max(0, timeS) * 0.12;
  const phase = (distance % length) / length;
  // 浮点误差可能让整圈余量落到 0.999999…，直接取 1 会停在传送带末端而不是回到起点。
  return { ...follow(QUALITY_SORTING_PATH, phase > 1 - 1e-9 ? 0 : phase), rollerAngle: -Math.max(0, timeS) * 0.8 };
}

export function dockConveyorPosition(job: TwinForkliftJob, timeS: number, jobs: TwinForkliftJob[]) {
  const cargo = depositedCargo(job,timeS,jobs);
  const transfer = job.startS+(job.endS-job.startS)*DOCK_TRANSFER_PROGRESS;
  const x = cargo.x+Math.max(0,timeS-transfer)*.12;
  return {...cargo,x,visible:cargo.visible && x<=DOCK_CONVEYOR_END_X};
}

function racks(): TwinRack[] {
  const out: TwinRack[] = [];
  for (const zone of ['chilled', 'frozen'] as const) {
    for (let row = 0; row < 3; row++) for (let col = 0; col < 4; col++) {
      const id = `${zone === 'chilled' ? 'C' : 'F'}-R${row + 1}-B${String(col + 1).padStart(2, '0')}`;
      out.push({ id, zone, x: (zone === 'chilled' ? -16 : 5) + col * 4.0,
        z: -17 + row * RACK_ROW_SPACING, levels: 3, bays: 3,
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
  jobs=reserveForkliftTraffic(jobs,chosen);
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

function tripRoutes(job:TwinForkliftJob,jobs:TwinForkliftJob[],layout:TwinRack[]) {
  const rack=layout.find(r=>r.id===job.rackId);
  if(!rack)return null;
  const index=Math.max(0,FORKLIFT_IDS.indexOf(job.forkliftId as typeof FORKLIFT_IDS[number]));
  const home=CHARGING_POINTS[index],pickup={x:rack.x,z:rack.z+RACK_ROW_SPACING/2},dock=dockStop(job,jobs);
  const entrance={x:LEFT_CORRIDOR_X,z:home.z},exit={x:RIGHT_CORRIDOR_X,z:dock.z};
  return {home,pickup,dock,
    approach:[home,entrance,{x:LEFT_CORRIDOR_X,z:pickup.z},pickup],
    outbound:[pickup,{x:RIGHT_CORRIDOR_X,z:pickup.z},exit,dock],
    reverse:[dock,exit],
    returning:[exit,{x:RIGHT_CORRIDOR_X,z:RETURN_AISLE_Z},{x:LEFT_CORRIDOR_X,z:RETURN_AISLE_Z},entrance],
    parking:[entrance,home]};
}

export function forkliftPose(id: string, timeS: number, jobs: TwinForkliftJob[], layout: TwinRack[]): ForkliftPose {
  const index = FORKLIFT_IDS.indexOf(id as typeof FORKLIFT_IDS[number]);
  const home = CHARGING_POINTS[Math.max(0,index)];
  const ownJobs = jobs.filter((j) => j.forkliftId===id).sort((a,b) => a.startS-b.startS);
  let rest = home;
  for (const job of ownJobs) {
    const routes=tripRoutes(job,jobs,layout);
    if (!routes) continue;
    const {pickup,dock}=routes;
    const start=routes.home;
    if (timeS < job.startS) {
      if(job.sourceStartS!==undefined && timeS>=job.sourceStartS)
        return {...rest,heading:0,lift:.2,carrying:false,stage:'yielding',job};
      break;
    }
    const p=(timeS-job.startS)/Math.max(1,job.endS-job.startS);
    if (p<=1) {
      if (p<0.28) { const q=follow(routes.approach,p/0.28);
        return {...q,lift:0.2,carrying:false,stage:'to_rack',job}; }
      if (p<0.38) {
        const u=(p-.28)/.1;
        const reach=u<.2?0:u<.5?(u-.2)/.3*1.5:u<.7?1.5:(1-u)/.3*1.5;
        const lift=u<.2?.2+u/.2*.08:u<.5?.28:u<.7?.28+(u-.5)/.2*.92:1.2;
        return {...pickup,heading:Math.PI/2,lift,reach,carrying:u>=.5,stage:'pickup',job};
      }
      if (p<0.76) {const q=follow(routes.outbound,(p-0.38)/0.38);
        return {...q,lift:1.2,carrying:true,stage:'to_dock',job};}
      if (p<0.84) {
        const lowering = Math.min(1, (p-0.76)/(DOCK_TRANSFER_PROGRESS-0.76));
        const targetLift = DOCK_FORK_LIFT;
        return {...dock,heading:0,lift:1.2+(targetLift-1.2)*lowering,
          carrying:p<DOCK_TRANSFER_PROGRESS,stage:'dropoff',job};
      }
      // Back away from the deposited pallet before turning into the return aisle.
      if (p<0.88) return {...follow(routes.reverse,(p-0.84)/0.04),
        heading:0,lift:0.15,carrying:false,stage:'returning',job};
      if(p>=.96)return {...follow(routes.parking,(p-.96)/.04),heading:0,lift:.2,carrying:false,stage:'returning',job};
      const q=follow(routes.returning,(p-0.88)/0.08);
      return {...q,lift:0.2,carrying:false,stage:'returning',job};
    }
    rest=start;
  }
  return {...rest,heading:0,lift:0.2,carrying:false,stage:ownJobs.length && timeS>=ownJobs[ownJobs.length-1].endS ? 'done' : 'waiting',job:null};
}

function motionTimes(job:TwinForkliftJob,jobs:TwinForkliftJob[],layout:TwinRack[]) {
  const routes=tripRoutes(job,jobs,layout);
  if(!routes)return [job.startS,job.endS];
  const duration=job.endS-job.startS;
  const times=[job.startS,job.endS];
  for(const [from,to,path] of [[0,.28,routes.approach],[.38,.76,routes.outbound],
    [.84,.88,routes.reverse],[.88,.96,routes.returning],[.96,1,routes.parking]] as const) {
    const lengths=path.slice(1).map((p,i)=>Math.hypot(p.x-path[i].x,p.z-path[i].z));
    const total=lengths.reduce((a,b)=>a+b,0);let travelled=0;
    times.push(job.startS+duration*from);
    for(const length of lengths){travelled+=length;times.push(job.startS+duration*(from+(to-from)*(total?travelled/total:1)));}
  }
  return times;
}

/** Exact minimum of relative linear motion, split at every turn and stop.
 * Centre discs contain the complete forklift, forks and pallet in every heading.
 */
export function minimumForkliftSeparation(a:string,b:string,from:number,to:number,jobs:TwinForkliftJob[],layout:TwinRack[]) {
  const times=[from,to,...jobs.filter(j=>(j.forkliftId===a||j.forkliftId===b)&&j.endS>=from&&j.startS<=to)
    .flatMap(j=>motionTimes(j,jobs,layout)).filter(t=>t>from&&t<to)].sort((x,y)=>x-y);
  let minimum=Infinity;
  for(let i=1;i<times.length;i++) {
    const a0=forkliftPose(a,times[i-1],jobs,layout),b0=forkliftPose(b,times[i-1],jobs,layout);
    const a1=forkliftPose(a,times[i],jobs,layout),b1=forkliftPose(b,times[i],jobs,layout);
    const x=a0.x-b0.x,z=a0.z-b0.z,dx=a1.x-b1.x-x,dz=a1.z-b1.z-z;
    const sq=dx*dx+dz*dz;
    const u=sq?Math.max(0,Math.min(1,-(x*dx+z*dz)/sq)):0;
    minimum=Math.min(minimum,Math.hypot(x+u*dx,z+u*dz));
  }
  return minimum;
}

/** Reserve whole trips before playback. Delays affect visualization only;
 * the source operation timestamps remain attached to each displayed job.
 */
export function reserveForkliftTraffic(source:TwinForkliftJob[],layout:TwinRack[]) {
  const reserved:TwinForkliftJob[]=[];
  const ordered=[...source].sort((a,b)=>a.startS-b.startS||a.id.localeCompare(b.id));
  for(const job of ordered) {
    const duration=Math.max(1,job.endS-job.startS);
    const ownEnd=Math.max(0,...reserved.filter(j=>j.forkliftId===job.forkliftId).map(j=>j.endS));
    const earliest=Math.max(job.startS,ownEnd);
    const latest=Math.max(earliest,...reserved.map(j=>j.endS))+4;
    let accepted=false;
    for(let start=earliest;start<=latest;start+=2) {
      const candidate={...job,sourceStartS:job.sourceStartS??job.startS,sourceEndS:job.sourceEndS??job.endS,startS:start,endS:start+duration};
      const proposed=[...reserved,candidate];
      if(FORKLIFT_IDS.filter(id=>id!==job.forkliftId).every(id=>minimumForkliftSeparation(job.forkliftId,id,start,start+duration,proposed,layout)>=FORKLIFT_SEPARATION)) {
        reserved.push(candidate);accepted=true;break;
      }
    }
    if(!accepted)throw new Error(`叉车 ${job.forkliftId} 的路线与停车位冲突，无法预约安全通道。`);
  }
  return reserved;
}

export const STAGE_LABELS: Record<ForkliftStage,string> = {
  waiting:'待命',yielding:'等待通道',to_rack:'前往库位',pickup:'取货举升',to_dock:'搬运至月台',dropoff:'月台卸货',returning:'返回充电区',done:'任务完成',
};
