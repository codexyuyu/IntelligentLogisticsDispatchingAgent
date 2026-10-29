/** R26: one inspectable cold-chain distribution center; deterministic forklift motion.
 * No fabricated live telemetry. This WebGL scene is a visual projection of
 * demo tasks or scheduling times, not a physics simulation.
 */
import { useEffect, useRef } from 'react';
import * as THREE from 'three';
import { OrbitControls } from 'three/examples/jsm/controls/OrbitControls.js';
import { CHARGING_POINTS, FORKLIFT_IDS, forkliftPose, dockConveyorPosition, conveyorPosition,
  COLD_PARTITION_X, COLD_PARTITION_PANELS, QUALITY_SORTING_PATH, type TwinWarehouseData } from '../lib/warehouseTwin';
import { cartonMaterials, palletMaterial, insulatedPanelMaterial } from '../lib/warehouseMaterials';
import { createDetailedForklift, createChargingStation } from '../lib/warehouseEquipment';

export type WarehouseSelection = { kind: 'zone' | 'rack' | 'forklift' | 'dock' | 'charger'; id: string };
export type WarehouseCamera = 'isometric' | 'top' | 'dock' | 'equipment';
type Props = {
  data: TwinWarehouseData;
  getTime: () => number;
  cameraPreset: WarehouseCamera;
  showRoof: boolean;
  selected: WarehouseSelection | null;
  onSelect: (selection: WarehouseSelection) => void;
  height?: number;
};

const rgb = (n:number) => `#${n.toString(16).padStart(6,'0')}`;

function label(text: string, color='#E9EBE5', scale=3.2, fontSize=38): THREE.Sprite {
  const canvas=document.createElement('canvas');canvas.width=512;canvas.height=96;
  const ctx=canvas.getContext('2d')!;
  ctx.font=`600 ${fontSize}px 'Microsoft YaHei', 'Noto Sans CJK SC', sans-serif`;
  ctx.textAlign='center';ctx.textBaseline='middle';ctx.fillStyle=color;ctx.fillText(text,256,48,496);
  const map=new THREE.CanvasTexture(canvas);map.colorSpace=THREE.SRGBColorSpace;
  const result=new THREE.Sprite(new THREE.SpriteMaterial({map,transparent:true,depthWrite:false}));
  result.scale.set(scale,scale*0.25,1);
  return result;
}

export default function WarehouseTwin3D({data,getTime,cameraPreset,showRoof,selected,onSelect,height=640}:Props) {
  const mount=useRef<HTMLDivElement|null>(null);
  const timeRef=useRef(getTime);timeRef.current=getTime;
  const selectedRef=useRef(selected);selectedRef.current=selected;
  const cameraRef=useRef(cameraPreset);cameraRef.current=cameraPreset;
  const roofRef=useRef(showRoof);roofRef.current=showRoof;
  const onSelectRef=useRef(onSelect);onSelectRef.current=onSelect;
  useEffect(()=>{
    const container=mount.current;if(!container)return;
    const scene=new THREE.Scene();scene.background=new THREE.Color(0x1e201e);scene.fog=new THREE.Fog(0x1e201e,95,180);
    const w=container.clientWidth||1024,h=container.clientHeight||height;
    const camera=new THREE.PerspectiveCamera(43,w/h,0.1,300);
    camera.position.set(47,49,63);
    const renderer=new THREE.WebGLRenderer({antialias:true,powerPreference:'high-performance'});
    renderer.setPixelRatio(Math.min(window.devicePixelRatio||1,1.6));renderer.setSize(w,h);
    renderer.outputColorSpace=THREE.SRGBColorSpace;renderer.toneMapping=THREE.ACESFilmicToneMapping;
    renderer.toneMappingExposure=1.38;
    container.replaceChildren(renderer.domElement);
    const controls=new OrbitControls(camera,renderer.domElement);
    controls.enableDamping=true;controls.dampingFactor=0.065;controls.target.set(0,0,0);
    controls.maxPolarAngle=Math.PI*0.49;controls.minDistance=13;controls.maxDistance=120;
    scene.add(new THREE.HemisphereLight(0xeceee8,0x2a2c29,2.15));
    const sun=new THREE.DirectionalLight(0xfafaf6,2.3);sun.position.set(-18,52,28);scene.add(sun);
    const fill=new THREE.DirectionalLight(0xd9c9a3,1.0);fill.position.set(30,21,-22);scene.add(fill);
    const cartons=cartonMaterials();
    const mat=(c:number,metalness=0.12,roughness=0.7)=>new THREE.MeshStandardMaterial({color:c,metalness,roughness});
    const mats={ slab:mat(0x2b2d2a),wall:mat(0x353733),beam:mat(0x4b4e47,0.48),rack:mat(0x6b6f66,0.65),shelf:mat(0x474a44,0.5),
      pallet:palletMaterial(),dock:mat(0x50544c),glass:mat(0xc2c6bc,0.6,0.15),yellow:mat(0xe3bf51),white:mat(0xe6e7e2)};
    const steel=mat(0xb6bdb7,.76,.31),rubber=mat(0x252926,0,.95);
    function box(parent:THREE.Object3D, size:[number,number,number], pos:[number,number,number],material:THREE.Material|THREE.Material[], pick?:WarehouseSelection) {
      const o=new THREE.Mesh(new THREE.BoxGeometry(...size),material);o.position.set(...pos);
      if(pick)o.userData.pick=pick;parent.add(o);return o;
    }
    const pickables:THREE.Object3D[]=[];
    const cutawayStructure:THREE.Object3D[]=[];
    function bar(parent:THREE.Object3D,a:THREE.Vector3,b:THREE.Vector3,radius:number,material:THREE.Material) {
      const direction=b.clone().sub(a);
      const mesh=new THREE.Mesh(new THREE.CylinderGeometry(radius,radius,direction.length(),8),material);
      mesh.position.copy(a).add(b).multiplyScalar(.5);
      mesh.quaternion.setFromUnitVectors(new THREE.Vector3(0,1,0),direction.normalize());parent.add(mesh);return mesh;
    }
    function pallet(parent:THREE.Object3D,x:number,y:number,z:number,width=1.4,depth=1.2) {
      for(const dx of [-.38,0,.38])box(parent,[width*.18,.13,depth],[x+dx*width,y+.065,z],mats.pallet);
      for(let i=0;i<5;i++)box(parent,[width,.065,depth*.16],[x,y+.16,z-depth*.4+i*depth*.2],mats.pallet);
    }
    // Floor, perimeter, column grid, transparent roof: warehouse is visible in cutaway mode.
    box(scene,[69,0.5,48],[0,-0.26,0],mats.slab);
    const grid=new THREE.GridHelper(68,34,0x4a4d47,0x333530);grid.position.y=0.012;
    (grid.material as THREE.Material).transparent=true;(grid.material as THREE.Material).opacity=0.3;scene.add(grid);
    for(const px of [-33.6,33.6])for(const pz of [-22,22]){
      const column=box(scene,[0.65,8.5,0.65],[px,4.15,pz],mats.beam);
      if(pz===22)cutawayStructure.push(column);
    }
    for(const pz of [-22,22]){
      const beam=box(scene,[68,0.42,0.5],[0,8.4,pz],mats.beam);
      if(pz===22)cutawayStructure.push(beam);
    }
    for(const px of [-33.6,33.6]){
      const beam=box(scene,[0.5,0.42,44],[px,8.4,0],mats.beam);
      if(px>0)cutawayStructure.push(beam);
    }
    box(scene,[68,3.3,0.28],[0,1.65,-22],mats.wall);
    box(scene,[0.28,3.3,44],[-33.6,1.65,0],mats.wall);
    // East side is open except for the three outbound portals below.
    // No detached thin wall blocks between the exits.
    box(scene,[9,.22,16],[37.5,-.12,8.45],mats.slab);
    const roofMaterial=new THREE.MeshStandardMaterial({color:0x9a9e94,transparent:true,opacity:0.25,metalness:0.55,roughness:0.35,depthWrite:false});
    const roof=box(scene,[68,0.25,44],[0,8.7,0],roofMaterial);roof.visible=roofRef.current;
    // Insulated separation between chilled and frozen storage. The two 6 m
    // openings coincide with the actual cross aisles; the front aisle stays open.
    const panelMat=insulatedPanelMaterial();
    for(const section of COLD_PARTITION_PANELS) {
      const depth=section.endZ-section.startZ,center=(section.startZ+section.endZ)/2;
      box(scene,[.32,6.8,depth],[COLD_PARTITION_X,3.4,center],panelMat);
      box(scene,[.42,.2,depth],[COLD_PARTITION_X,.12,center],steel);
      box(scene,[.4,.16,depth],[COLD_PARTITION_X,6.8,center],steel);
    }
    for(const z of [-13.5,-6.5]) {
      box(scene,[.38,1.1,6],[COLD_PARTITION_X,6.25,z],panelMat);
      for(const side of [-3,3])box(scene,[.48,5.7,.12],[COLD_PARTITION_X,2.85,z+side],steel);
      // Upper air curtain leaves the complete forklift envelope unobstructed.
      const curtainMat=new THREE.MeshStandardMaterial({color:0xc9e1d4,transparent:true,opacity:.2,roughness:.3,side:THREE.DoubleSide,depthWrite:false});
      for(let strip=0;strip<12;strip++)box(scene,[.035,1.45,.46],[COLD_PARTITION_X,4.95,z-2.75+strip*.5],curtainMat);
    }
    const separationSign=label('冷藏  2–8°C   │   冷冻  −18°C','#e6eee8',9,32);
    separationSign.position.set(COLD_PARTITION_X,7.5,-10);scene.add(separationSign);
    // Functional zones and labels; slabs are click targets.
    const zonePlates=new Map<string,THREE.MeshStandardMaterial>();
    for(const z of data.zones){
      const floorMat=new THREE.MeshStandardMaterial({color:z.color,transparent:true,opacity:0.19,roughness:0.9});
      const p=box(scene,[z.width,0.09,z.depth],[z.x,0.04,z.z],floorMat,{kind:'zone',id:z.id});
      pickables.push(p);zonePlates.set(z.id,floorMat);
      const edges=new THREE.LineSegments(new THREE.EdgesGeometry(p.geometry),new THREE.LineBasicMaterial({color:z.color,transparent:true,opacity:0.65}));edges.position.copy(p.position);scene.add(edges);
      const caption=label(z.name,rgb(z.color),6.8,32);
      caption.position.set(z.x,5.8,z.z+z.depth*0.38);scene.add(caption);
      const stripe=box(scene,[z.width-0.5,0.025,0.11],[z.x,0.105,z.z-z.depth/2+0.36],new THREE.MeshBasicMaterial({color:z.color}));stripe.rotation.y=0;
    }
    // Warehouse road markings, receiving bays and quality benches.
    for(let i=0;i<3;i++) {
      box(scene,[4.7,0.08,2.7],[-27+i*3.0,0.14,-12],mats.dock);
    }
    // Quality inspection sits immediately behind sorting; leave the truck aisle clear.
    for(const x of [-4,0]) {
      box(scene,[2.6,.12,1.1],[x,1.0,4.6],steel);
      for(const side of [-1,1])for(const z of [4.2,5])box(scene,[.1,.95,.1],[x+side*1.05,.5,z],mats.beam);
      box(scene,[.7,.08,.55],[x,.11+1,4.6],mats.dock);
      box(scene,[.08,.36,.45],[x+.5,1.27,4.6],mats.beam);
    }
    const inspectionSign=label('到货质检 → 分拣复核','#e6d49b',6,30);inspectionSign.position.set(-8.7,3,4.8);scene.add(inspectionSign);
    for(let i=0;i<6;i++){
      const x=-16+i*5.9;
      box(scene,[0.2,0.03,2.5],[x,0.12,1.0],mats.yellow);
    }
    // 24 rack banks with instanced stock containers: one draw call per asset type.
    const occupiedCells:{x:number;y:number;z:number;zone:'chilled'|'frozen'}[]=[];
    for(const rack of data.racks){
      const g=new THREE.Group();g.position.set(rack.x,0,rack.z);
      const frame=mat(rack.zone==='frozen'?0x9a9d96:0x3f8a58,0.6);
      for(const x of [-1.45,1.45])for(const z of [-0.61,0.61])box(g,[0.12,5.25,0.12],[x,2.65,z],frame);
      for(let level=0;level<rack.levels;level++){
        const y=0.4+level*1.62;
        box(g,[3.05,0.13,1.45],[0,y,0],mats.shelf);
        for(let bay=0;bay<rack.bays;bay++) {
          const occupied=((level*7+bay*4+Math.round(rack.occupied*10))%10)<7;
          if(occupied) occupiedCells.push({x:rack.x-0.96+bay*0.96,y,z:rack.z,zone:rack.zone});
        }
      }
      for(const side of [-1,1]) {
        bar(g,new THREE.Vector3(side*1.45,.3,-.61),new THREE.Vector3(side*1.45,5.15,.61),.035,steel);
        bar(g,new THREE.Vector3(side*1.45,.3,.61),new THREE.Vector3(side*1.45,5.15,-.61),.035,steel);
        box(g,[.32,.08,1.6],[side*1.45,.06,0],mats.yellow);
      }
      const hit=box(g,[3.3,5.4,1.55],[0,2.7,0],new THREE.MeshBasicMaterial({transparent:true,opacity:0,depthWrite:false,colorWrite:false}),{kind:'rack',id:rack.id});
      pickables.push(hit);
      const sign=label(rack.id,rack.zone==='chilled'?'#9ED9AE':'#E6E7E2',2.5,29);
      sign.position.set(0,5.75,0);g.add(sign);
      scene.add(g);
    }
    const stamp=new THREE.Object3D();
    const putInstances=(geo:THREE.BoxGeometry,material:THREE.Material|THREE.Material[],offsetY:number,only?:'chilled'|'frozen')=>{
      const positions=only?occupiedCells.filter(p=>p.zone===only):occupiedCells;
      const mesh=new THREE.InstancedMesh(geo,material,positions.length);
      positions.forEach((p,i)=>{stamp.position.set(p.x,p.y+offsetY,p.z);stamp.rotation.set(0,0,0);stamp.updateMatrix();mesh.setMatrixAt(i,stamp.matrix);});
      mesh.instanceMatrix.needsUpdate=true;mesh.frustumCulled=false;scene.add(mesh);
    };
    putInstances(new THREE.BoxGeometry(0.86,0.12,1.04),mats.pallet,0.15);
    putInstances(new THREE.BoxGeometry(0.72,0.68,0.79),cartons,0.55);
    // Continuous roller conveyor: all motion follows the replay clock, including seeks.
    const conveyorRollers:THREE.Group[]=[];
    const conveyorCargo:THREE.Group[]=[];
    for(let segment=1;segment<QUALITY_SORTING_PATH.length;segment++) {
      const from=QUALITY_SORTING_PATH[segment-1],to=QUALITY_SORTING_PATH[segment];
      const length=Math.hypot(to.x-from.x,to.z-from.z);
      const line=new THREE.Group();line.position.set(from.x,0,from.z);
      line.rotation.y=Math.atan2(-(to.z-from.z),to.x-from.x);scene.add(line);
      box(line,[length,.56,1.7],[length/2,.55,0],mats.beam);
      box(line,[length,.17,1.48],[length/2,.95,0],mats.dock);
      const trimStart=segment>1?.9:0,trimEnd=segment<QUALITY_SORTING_PATH.length-1?.9:0;
      for(const side of [-1,1]) {
        box(line,[length-trimStart-trimEnd,.16,.09],[trimStart+(length-trimStart-trimEnd)/2,1.17,side*.92],steel);
        for(let x=.35;x<length;x+=2.6)box(line,[.09,.83,.09],[x,.46,side*.92],mats.beam);
      }
      const count=Math.ceil(length/.45);
      for(let i=0;i<count;i++) {
        const rotor=new THREE.Group();rotor.position.set((i+.5)*length/count,1.05,0);
        const roller=new THREE.Mesh(new THREE.CylinderGeometry(.105,.105,1.4,10),mats.shelf);
        roller.rotation.x=Math.PI/2;rotor.add(roller);
        box(rotor,[.045,.025,1.4],[0,.108,0],mats.white);
        line.add(rotor);conveyorRollers.push(rotor);
      }
    }
    // Ball-transfer corner tables bridge the belts without a gap or a blocking rail.
    for(const corner of QUALITY_SORTING_PATH.slice(1,-1)) {
      box(scene,[1.75,.14,1.75],[corner.x,.98,corner.z],steel);
      for(let x=-.6;x<=.6;x+=.3)for(let z=-.6;z<=.6;z+=.3) {
        const ball=new THREE.Mesh(new THREE.SphereGeometry(.09,8,6),steel);ball.position.set(corner.x+x,1.08,corner.z+z);scene.add(ball);
      }
    }
    for(let i=0;i<4;i++){
      const cargo=new THREE.Group();
      box(cargo,[1.1,0.65,1.0],[0,0.325,0],cartons);
      const initial=conveyorPosition(i,0);cargo.position.set(initial.x,1.18,initial.z);cargo.rotation.y=initial.heading;
      scene.add(cargo);conveyorCargo.push(cargo);
    }
    for(let i=0;i<8;i++){
      const x=5+i%4*3.7,z=7+Math.floor(i/4)*4;
      pallet(scene,x,.08,z,1.55,1.35);
      box(scene,[1.33,0.85,1.15],[x,0.72,z],cartons);
    }
    // Open outbound portals connected to continuous powered roller beds.
    const outboundRollers:THREE.Group[]=[];
    for(let i=0;i<3;i++){
      const z=4+i*4.45;
      const hit=box(scene,[12,.35,3.4],[32,.18,z],new THREE.MeshBasicMaterial({transparent:true,opacity:0,depthWrite:false,colorWrite:false}),{kind:'dock',id:`DOCK-${i+1}`});pickables.push(hit);
      box(scene,[12,.12,3.4],[32,.12,z],mats.beam);
      for(const side of [-1,1]) {
        box(scene,[12,.14,.12],[32,.39,z+side*1.74],steel);
        for(const x of [26.4,29.7,33,37.5])box(scene,[.16,.28,.16],[x,.12,z+side*1.48],mats.beam);
        // Portal posts flank the opening; no filled door slab.
        box(scene,[.45,4.9,.26],[33.5,2.45,z+side*1.87],panelMat);
        box(scene,[.55,4.55,.16],[33.45,2.3,z+side*1.66],rubber);
        box(scene,[.7,.85,.22],[33.15,.45,z+side*1.88],mats.yellow);
        box(scene,[.5,.16,.2],[33.13,.6,z+side*1.88],rubber);
      }
      box(scene,[.5,.5,4],[33.5,5.05,z],panelMat);
      const drum=new THREE.Mesh(new THREE.CylinderGeometry(.24,.24,3.4,16),steel);
      drum.rotation.x=Math.PI/2;drum.position.set(33.5,4.65,z);scene.add(drum);
      for(let slat=0;slat<3;slat++)box(scene,[.13,.12,3.2],[33.52,4.34+slat*.12,z],steel);
      const lane=label(`D0${i+1}  出口`,'#D7E8DB',4,36);lane.position.set(33.5,5.8,z);scene.add(lane);
      for(let k=0;k<29;k++) {
        const rotor=new THREE.Group();rotor.position.set(26.15+k*.415,.225,z);
        const cylinder=new THREE.Mesh(new THREE.CylinderGeometry(.11,.11,3.2,10),steel);
        cylinder.rotation.x=Math.PI/2;rotor.add(cylinder);
        box(rotor,[.04,.018,3.15],[0,.11,0],mats.white);
        scene.add(rotor);outboundRollers.push(rotor);
      }
      for(const x of [28,31,35,37]) {
        const arrow=label('››','#d6d9bf',1.4,40);arrow.rotation.x=-Math.PI/2;
        arrow.position.set(x,.47,z);scene.add(arrow);
      }
      // Drive motor, local controls and a small green running beacon.
      box(scene,[.65,.4,.45],[30.5,.38,z+1.97],mats.beam);
      box(scene,[.35,.55,.22],[32.5,1.1,z+1.97],panelMat);
      const light=new THREE.Mesh(new THREE.SphereGeometry(.075,8,6),new THREE.MeshStandardMaterial({color:0x68bd70,emissive:0x2a5c30}));
      light.position.set(32.3,1.22,z+1.97);scene.add(light);
    }
    // Detailed charging cabinets with a stowed hose and a connected lead only at home.
    const chargers=FORKLIFT_IDS.map((id,i)=>{
      const home=CHARGING_POINTS[i];
      box(scene,[3.3,.07,2.4],[home.x-.25,.07,home.z],mats.dock);
      for(const side of [-1,1])box(scene,[3.3,.015,.055],[home.x-.25,.115,home.z+side*1.2],mats.yellow);
      const station=createChargingStation(i,steel,mats.beam);
      station.root.position.set(home.x-2.25,.08,home.z);scene.add(station.root);
      station.cabinet.userData.pick={kind:'charger',id:`CH-0${i+1}`};pickables.push(station.cabinet);
      const stationLabel=label(`CH-0${i+1}`,'#cce4cd',2.2,32);
      stationLabel.position.set(home.x-2.25,3.05,home.z);scene.add(stationLabel);
      return {...station,forkliftId:id,home};
    });
    // Once lowered, cargo belongs to the dock, not to the departing forklift.
    const dockCargo=data.jobs.map(job=>{
      const cargo=new THREE.Group();
      box(cargo,[0.97,0.13,0.95],[0,0.17,0],mats.pallet);
      box(cargo,[0.86,0.76,0.78],[0,0.62,0],cartons);
      cargo.visible=false;scene.add(cargo);
      return {job,cargo};
    });
    // All detailed geometry stays inside the existing collision-clearance envelope.
    const actors=new Map<string,ReturnType<typeof createDetailedForklift>>();
    FORKLIFT_IDS.forEach((id,i)=>{
      const actor=createDetailedForklift(i,{steel,dark:mats.beam,pallet:mats.pallet,cartons});
      const idLabel=label(id,'#f7e5a0',2.2,36);idLabel.position.set(-.1,3.2,0);actor.root.add(idLabel);
      const pickMesh=box(actor.root,[2.6,2.8,1.65],[0,1.4,0],new THREE.MeshBasicMaterial({transparent:true,opacity:0,depthWrite:false,colorWrite:false}),{kind:'forklift',id});
      pickables.push(pickMesh);
      const p=CHARGING_POINTS[i];actor.root.position.set(p.x,.08,p.z);scene.add(actor.root);
      actors.set(id,actor);
    });
    // Click details via standard raycaster; supports rack, zone, vehicle and dock.
    const raycaster=new THREE.Raycaster(),pointer=new THREE.Vector2();
    function onClick(event:MouseEvent){
      const rect=renderer.domElement.getBoundingClientRect();if(!rect.width||!rect.height)return;
      pointer.x=((event.clientX-rect.left)/rect.width)*2-1;
      pointer.y=-((event.clientY-rect.top)/rect.height)*2+1;
      raycaster.setFromCamera(pointer,camera);
      const hits=raycaster.intersectObjects(pickables,false);
      for(const hit of hits){
        const pick=hit.object.userData.pick as WarehouseSelection|undefined;
        if(pick){onSelectRef.current(pick);break;}
      }
    }
    renderer.domElement.addEventListener('click',onClick);
    const target=new THREE.Vector3(),desired=new THREE.Vector3();
    let lastPreset:WarehouseCamera|null=null;
    let raf=0,lastT=0;
    const animate=(_now:number)=>{
      if(cameraRef.current!==lastPreset){
        lastPreset=cameraRef.current;
        if(lastPreset==='top'){desired.set(0,83,0.01);target.set(0,0,0);}
        else if(lastPreset==='dock'){desired.set(43,21,40);target.set(18,0,8);}
        else if(lastPreset==='equipment'){desired.set(-15,8.5,23);target.set(-25,1.2,13.1);}
        else{desired.set(47,49,63);target.set(0,0,0);}
        camera.position.copy(desired);controls.target.copy(target);controls.update();
      }
      roof.visible=roofRef.current;
      // A cutaway removes foreground roof supports as well as the roof itself.
      // Otherwise the front beam masks an entire forklift during dock departure.
      cutawayStructure.forEach(mesh=>{mesh.visible=roofRef.current;});
      const t=timeRef.current();
      conveyorCargo.forEach((cargo,i)=>{const p=conveyorPosition(i,t);cargo.position.set(p.x,1.18,p.z);cargo.rotation.y=p.heading;});
      const rollerAngle=conveyorPosition(0,t).rollerAngle;
      conveyorRollers.forEach(rotor=>{rotor.rotation.z=rollerAngle;});
      outboundRollers.forEach(rotor=>{rotor.rotation.z=rollerAngle;});
      dockCargo.forEach(({job,cargo})=>{
        const p=dockConveyorPosition(job,t,data.jobs);cargo.visible=p.visible;cargo.position.set(p.x,p.y,p.z);
      });
      chargers.forEach(station=>{
        const pose=forkliftPose(station.forkliftId,t,data.jobs,data.racks);
        const connected=(pose.stage==='waiting'||pose.stage==='yielding'||pose.stage==='done') && Math.hypot(pose.x-station.home.x,pose.z-station.home.z)<.05;
        station.lead.visible=connected;
        station.screen.visible=!connected;station.chargingScreen.visible=connected;
        station.status.emissiveIntensity=connected ? .65+.3*Math.sin(t*1.6) : .12;
      });
      actors.forEach((entry,id)=>{
        const pose=forkliftPose(id,t,data.jobs,data.racks);
        entry.root.position.set(pose.x,0.08,pose.z);
        entry.root.rotation.y=pose.heading;
        entry.forks.position.y=pose.lift;
        entry.cargo.visible=pose.carrying;
        entry.amber.emissiveIntensity=.5+.35*Math.sin(t*3.2);
        if(pose.stage==='to_rack'||pose.stage==='to_dock'||pose.stage==='returning')
          for(const wheel of entry.wheels)wheel.rotation.z-=(Math.max(0,t-lastT))*0.08;
        // Selection must not enlarge physical geometry into the neighbouring rack.
        entry.root.scale.setScalar(1);
      });
      lastT=t;
      zonePlates.forEach((material,id)=>{material.opacity=selectedRef.current?.kind==='zone'&&selectedRef.current.id===id?0.41:0.19;});
      controls.update();renderer.render(scene,camera);
      raf=requestAnimationFrame(animate);
    };
    raf=requestAnimationFrame(animate);
    const resize=()=>{const cw=container.clientWidth||w,ch=container.clientHeight||h;camera.aspect=cw/ch;camera.updateProjectionMatrix();renderer.setSize(cw,ch);};
    const observer=typeof ResizeObserver!=='undefined'?new ResizeObserver(resize):null;
    observer?.observe(container);window.addEventListener('resize',resize);
    return ()=>{
      cancelAnimationFrame(raf);observer?.disconnect();window.removeEventListener('resize',resize);
      renderer.domElement.removeEventListener('click',onClick);controls.dispose();
      const geometries=new Set<THREE.BufferGeometry>(),materials=new Set<THREE.Material>(),textures=new Set<THREE.Texture>();
      scene.traverse(o=>{
        const mesh=o as THREE.Mesh;
        if(mesh.geometry)geometries.add(mesh.geometry);
        if(mesh.material)for(const material of Array.isArray(mesh.material)?mesh.material:[mesh.material]){
          materials.add(material);
          const map=(material as THREE.MeshBasicMaterial).map;if(map)textures.add(map);
        }
      });
      geometries.forEach(g=>g.dispose());textures.forEach(t=>t.dispose());materials.forEach(m=>m.dispose());
      renderer.dispose();renderer.forceContextLoss();if(container.contains(renderer.domElement))container.removeChild(renderer.domElement);
    };
  },[data,height]); // Camera selection, roof, selection, and simulation time never recreate WebGL.
  return <div ref={mount} className="r26-warehouse-canvas" style={{height,minHeight:380}} aria-label="单仓冷链数字孪生 3D 场景" />;
}
