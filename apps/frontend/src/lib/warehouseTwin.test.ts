import { describe, expect, it } from 'vitest';
import { CHARGING_POINTS, FORKLIFT_IDS, FORKLIFT_CLEARANCE_RADIUS, RACK_HALF_DEPTH, RACK_HALF_WIDTH,
  forkliftPose, warehouseTwinData, depositedCargo, conveyorPosition, DOCK_TRANSFER_PROGRESS,
  COLD_PARTITION_X, COLD_PARTITION_PANELS, dockConveyorPosition, FORKLIFT_SEPARATION,
  reserveForkliftTraffic, minimumForkliftSeparation, QUALITY_SORTING_PATH, ZONES, type TwinForkliftJob } from './warehouseTwin';

const data = warehouseTwinData(null, null, 'showcase');
function rackDistance(x: number, z: number, rack: { x: number; z: number }) {
  return Math.hypot(Math.max(0, Math.abs(x - rack.x) - RACK_HALF_WIDTH),
    Math.max(0, Math.abs(z - rack.z) - RACK_HALF_DEPTH));
}

describe('叉车巷道避让', () => {
  it('所有货架和三台叉车的完整运动都留有含托盘的转向空间', () => {
    let closest = Infinity;
    for (const id of FORKLIFT_IDS) for (const rack of data.racks) {
      const job: TwinForkliftJob = { id: 'clearance', forkliftId: id, rackId: rack.id,
        batchId: 'lot', orderId: 'order', startS: 0, endS: 100, source: 'synthetic' };
      for (let step = 0; step <= 1000; step++) {
        const pose = forkliftPose(id, step / 10, [job], data.racks);
        for (const obstacle of data.racks) closest = Math.min(closest, rackDistance(pose.x, pose.z, obstacle));
      }
    }
    expect(closest).toBeGreaterThanOrEqual(FORKLIFT_CLEARANCE_RADIUS);
    // Actual rendered pallet's far corner is (2.485, 0.475), not just the cab.
    expect(FORKLIFT_CLEARANCE_RADIUS).toBeGreaterThan(Math.hypot(2.485, 0.475));
  });

  it('旧版沿库位中心线纵穿前排货架会触发碰撞，不能作为有效通路', () => {
    const front = data.racks.find(r => r.id === 'C-R3-B02')!;
    expect(rackDistance(front.x, front.z, front)).toBe(0);
    const pose = forkliftPose('FK-01', 0.28 * 380, data.jobs, data.racks);
    expect(data.racks.every(r => rackDistance(pose.x, pose.z, r) >= FORKLIFT_CLEARANCE_RADIUS)).toBe(true);
  });

  it('取货、运输、卸货和返回切换时位置连续，取货时货叉朝向货架', () => {
    for (const id of FORKLIFT_IDS) {
      const job = data.jobs.find(j => j.forkliftId === id)!;
      for (const boundary of [0, 0.28, 0.38, 0.76, DOCK_TRANSFER_PROGRESS, 0.84, 0.88, .96, 1]) {
        const t = job.startS + boundary * (job.endS - job.startS);
        const before = forkliftPose(id, t - 0.00001, [job], data.racks);
        const after = forkliftPose(id, t + 0.00001, [job], data.racks);
        expect(Math.hypot(after.x - before.x, after.z - before.z)).toBeLessThan(0.001);
      }
      const pickup = forkliftPose(id, job.startS + 0.33 * (job.endS - job.startS), [job], data.racks);
      expect(pickup.heading).toBe(Math.PI / 2);
      const idle = forkliftPose(id, -1, [], data.racks);
      expect({ x: idle.x, z: idle.z }).toEqual(CHARGING_POINTS[FORKLIFT_IDS.indexOf(id)]);
    }
  });

  it('货物交接前后位置一致，卸下后留在月台，回拖时间会撤回交接', () => {
    for (const job of data.jobs) {
      const transfer = job.startS + (job.endS-job.startS)*DOCK_TRANSFER_PROGRESS;
      const before = forkliftPose(job.forkliftId, transfer-0.000001, data.jobs, data.racks);
      const after = forkliftPose(job.forkliftId, transfer+0.000001, data.jobs, data.racks);
      const cargo = depositedCargo(job, transfer+0.000001, data.jobs);
      expect(before.carrying).toBe(true);
      expect(after.carrying).toBe(false);
      expect(cargo.visible).toBe(true);
      expect(cargo.x).toBeCloseTo(before.x+2, 5);
      expect(cargo.z).toBeCloseTo(before.z, 5);
      expect(cargo.y).toBeCloseTo(0.08+before.lift, 5);
      expect(depositedCargo(job, job.endS+100, data.jobs).visible).toBe(true);
      expect(depositedCargo(job, job.startS, data.jobs).visible).toBe(false);
      const reverseStart = job.startS + (job.endS-job.startS)*0.845;
      const reverseEnd = job.startS + (job.endS-job.startS)*0.875;
      expect(forkliftPose(job.forkliftId, reverseEnd, data.jobs, data.racks).x)
        .toBeLessThan(forkliftPose(job.forkliftId, reverseStart, data.jobs, data.racks).x);
    }
    const slots = data.jobs.map(job => depositedCargo(job, 1800, data.jobs));
    expect(new Set(slots.map(slot => `${slot.x},${slot.z}`)).size).toBe(data.jobs.length);
  });

  it('传送带箱体和滚筒随时间运动，暂停和倒放定位是确定的且不越出传送带', () => {
    expect(conveyorPosition(0, 0)).not.toEqual(conveyorPosition(0, 10));
    expect(conveyorPosition(0, 10)).toEqual(conveyorPosition(0, 10));
    const first = conveyorPosition(0, 0);
    // The continuous inspection + sorting line is now 28.4 units, at .12 units/s.
    expect(conveyorPosition(0, 28.4/.12).x).toBeCloseTo(first.x);
    expect(conveyorPosition(0, 28.4/.12).z).toBeCloseTo(first.z);
    for(let t=0;t<=1800;t++) for(let i=0;i<4;i++) {
      const position=conveyorPosition(i,t);
      expect(position.x).toBeGreaterThanOrEqual(-13.6);
      expect(position.x).toBeLessThan(11.6);
      const onLine=QUALITY_SORTING_PATH.slice(1).some((end,index)=>{
        const start=QUALITY_SORTING_PATH[index];
        return Math.abs(start.z-end.z)<1e-9
          ? Math.abs(position.z-start.z)<1e-9 && position.x>=start.x-1e-9 && position.x<=end.x+1e-9
          : Math.abs(position.x-start.x)<1e-9 && position.z>=start.z-1e-9 && position.z<=end.z+1e-9;
      });
      expect(onLine).toBe(true);
    }
  });

  it('新增隔墙为叉车横向巷道留足门洞净空', () => {
    let closest=Infinity;
    for(const id of FORKLIFT_IDS) for(const rack of data.racks) {
      const job: TwinForkliftJob={id:'partition',forkliftId:id,rackId:rack.id,batchId:'b',orderId:'o',startS:0,endS:100,source:'synthetic'};
      for(let step=0;step<=1000;step++) {
        const pose=forkliftPose(id,step/10,[job],data.racks);
        for(const panel of COLD_PARTITION_PANELS) {
          const dx=Math.max(0,Math.abs(pose.x-COLD_PARTITION_X)-.24);
          const dz=Math.max(panel.startZ-pose.z,0,pose.z-panel.endZ);
          closest=Math.min(closest,Math.hypot(dx,dz));
        }
      }
    }
    expect(closest).toBeGreaterThanOrEqual(FORKLIFT_CLEARANCE_RADIUS);
  });

  it('卸货后货物从同一交接位置沿滚筒线穿过出口，倒拖时间可复原', () => {
    const job=data.jobs[0];
    const transfer=job.startS+(job.endS-job.startS)*DOCK_TRANSFER_PROGRESS;
    const anchor=depositedCargo(job,transfer,data.jobs);
    expect(dockConveyorPosition(job,transfer,data.jobs)).toEqual(anchor);
    const inDoor=dockConveyorPosition(job,transfer+60,data.jobs);
    expect(inDoor.visible).toBe(true);
    expect(inDoor.x).toBeCloseTo(34.2);
    expect(inDoor.y).toBe(anchor.y);
    expect(dockConveyorPosition(job,transfer+100,data.jobs).visible).toBe(false);
    expect(dockConveyorPosition(job,transfer-1,data.jobs).visible).toBe(false);
  });

  it('整段演示中三台叉车的连续路径保持间隔，包括停车车辆与会车',()=>{
    const end=Math.max(...data.jobs.map(j=>j.endS));
    for(let a=0;a<3;a++)for(let b=a+1;b<3;b++) {
      expect(minimumForkliftSeparation(FORKLIFT_IDS[a],FORKLIFT_IDS[b],0,end+10,data.jobs,data.racks))
        .toBeGreaterThanOrEqual(FORKLIFT_SEPARATION-1e-9);
      // Independent dense sampling additionally checks that the rendering uses the same paths.
      for(let t=0;t<=end+10;t+=.25) {
        const p=forkliftPose(FORKLIFT_IDS[a],t,data.jobs,data.racks),q=forkliftPose(FORKLIFT_IDS[b],t,data.jobs,data.racks);
        expect(Math.hypot(p.x-q.x,p.z-q.z)).toBeGreaterThanOrEqual(FORKLIFT_SEPARATION-1e-9);
      }
    }
    expect(data.jobs.some(j=>j.startS>(j.sourceStartS??j.startS))).toBe(true);
    expect(data.jobs.some(a=>data.jobs.some(b=>a.forkliftId!==b.forkliftId && a.startS<b.endS && b.startS<a.endS))).toBe(true);
  });

  it('同一库位同时请求会车时预约等待，不改写原任务时间，回拖仍可复算',()=>{
    const source=FORKLIFT_IDS.map((forkliftId,i):TwinForkliftJob=>({id:`conflict-${i}`,forkliftId,rackId:data.racks[0].id,
      batchId:'b',orderId:'o',startS:0,endS:80,source:'planned_timing'}));
    const rawMinimum=minimumForkliftSeparation('FK-01','FK-02',0,80,source,data.racks);
    expect(rawMinimum).toBeLessThan(FORKLIFT_SEPARATION);
    const reserved=reserveForkliftTraffic(source,data.racks);
    expect(source.every(j=>j.startS===0&&j.endS===80)).toBe(true);
    for(const job of reserved) {
      expect(job.sourceStartS).toBe(0);expect(job.sourceEndS).toBe(80);
      expect(job.endS-job.startS).toBe(80);
    }
    const end=Math.max(...reserved.map(j=>j.endS));
    for(let a=0;a<3;a++)for(let b=a+1;b<3;b++)expect(minimumForkliftSeparation(FORKLIFT_IDS[a],FORKLIFT_IDS[b],0,end,reserved,data.racks)).toBeGreaterThanOrEqual(FORKLIFT_SEPARATION-1e-9);
    expect(reserveForkliftTraffic(source,data.racks)).toEqual(reserved);
    const delayed=reserved.find(j=>j.startS>0)!;
    expect(forkliftPose(delayed.forkliftId,delayed.startS/2,reserved,data.racks).stage).toBe('yielding');
  });

  it('质检区紧邻分拣区后侧，货物沿连通输送线跨区且没有位置跳跃',()=>{
    const quality=ZONES.find(z=>z.id==='quality')!,picking=ZONES.find(z=>z.id==='picking')!;
    expect(quality.z+quality.depth/2).toBe(picking.z-picking.depth/2);
    expect(quality.x).toBe(picking.x);
    const transition=QUALITY_SORTING_PATH[0];
    expect(transition.z).toBeGreaterThan(quality.z-quality.depth/2);
    expect(transition.z).toBeLessThan(quality.z+quality.depth/2);
    for(const seconds of [4.6/.12,7.8/.12]) {
      const before=conveyorPosition(0,seconds-.001),after=conveyorPosition(0,seconds+.001);
      expect(Math.hypot(before.x-after.x,before.z-after.z)).toBeLessThan(.001);
    }
    expect(conveyorPosition(0,70).z).toBeGreaterThan(picking.z-picking.depth/2);
  });
});
it('取货时先伸叉再举升，并在离架前收回',()=>{
  const job={...data.jobs[0],startS:0,endS:100};
  const pose=(t:number)=>forkliftPose(job.forkliftId,t,[job],data.racks);
  expect(pose(31).reach).toBeGreaterThan(0);
  expect(pose(31).carrying).toBe(false);
  expect(pose(34).reach).toBeCloseTo(1.5);
  expect(pose(34).carrying).toBe(true);
  expect(pose(37).reach).toBeLessThan(pose(34).reach!);
  expect(pose(38).reach??0).toBe(0);
  expect(pose(37.999).lift).toBeCloseTo(pose(38).lift);
});
