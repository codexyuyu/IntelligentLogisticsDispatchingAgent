import * as THREE from 'three';
import { afterEach, describe, expect, it, vi } from 'vitest';
import { createChargingStation, createDetailedForklift } from './warehouseEquipment';
import { FORKLIFT_CLEARANCE_RADIUS } from './warehouseTwin';

afterEach(()=>vi.restoreAllMocks());
function canvas() {
  vi.spyOn(HTMLCanvasElement.prototype,'getContext').mockReturnValue({
    fillStyle:'',textAlign:'',textBaseline:'',font:'',fillRect(){},fillText(){},
  } as unknown as CanvasRenderingContext2D);
}
function materials() {
  return {steel:new THREE.MeshStandardMaterial(),dark:new THREE.MeshStandardMaterial(),
    pallet:new THREE.MeshStandardMaterial(),cartons:[new THREE.MeshStandardMaterial()]};
}

describe('细化设备与既有运动几何的兼容性',()=>{
  it('三种叉车的实际模型顶点均留在原有货架避碰包络内',()=>{
    canvas();let furthest=0;
    for(let index=0;index<3;index++) {
      const actor=createDetailedForklift(index,materials());
      actor.forks.position.y=1.2;actor.root.updateMatrixWorld(true);
      actor.root.traverse(object=>{
        if(!(object instanceof THREE.Mesh))return;
        const position=object.geometry.getAttribute('position');
        const point=new THREE.Vector3();
        for(let i=0;i<position.count;i++) {
          point.fromBufferAttribute(position,i).applyMatrix4(object.matrixWorld);
          furthest=Math.max(furthest,Math.hypot(point.x,point.z));
        }
      });
      expect(actor.wheels).toHaveLength(4);
      expect(actor.cargo.parent).toBe(actor.forks);
      const cargoCenter=new THREE.Vector3();actor.cargo.getWorldPosition(cargoCenter);
      expect(cargoCenter.y).toBeCloseTo(1.2);
    }
    expect(furthest).toBeLessThanOrEqual(FORKLIFT_CLEARANCE_RADIUS);
  });

  it('充电机柜不与停车车身相交，连接端对准车尾插口',()=>{
    canvas();const m=materials();
    const station=createChargingStation(0,m.steel,m.dark);
    station.root.position.set(-2.25,.08,0);station.root.updateMatrixWorld(true);
    const cabinet=new THREE.Box3().setFromObject(station.cabinet);
    expect(cabinet.max.x).toBeLessThan(-1.403);
    const plug=station.lead.children.find(o=>o instanceof THREE.Mesh && Math.abs(o.position.x-.86)<.001)!;
    const position=new THREE.Vector3();plug.getWorldPosition(position);
    expect(position.x).toBeCloseTo(-1.39);
    expect(position.y).toBeCloseTo(.99);
    expect(position.z).toBeCloseTo(0);
    expect(station.chargingScreen.visible).toBe(false);
  });
});
