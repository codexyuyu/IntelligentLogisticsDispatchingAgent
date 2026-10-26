/** R26: one inspectable cold-chain distribution center; deterministic forklift motion.
 * No fabricated live telemetry. This WebGL scene is a visual projection of
 * demo tasks or scheduling times, not a physics simulation.
 */
import { useEffect, useRef } from 'react';
import * as THREE from 'three';
import { OrbitControls } from 'three/examples/jsm/controls/OrbitControls.js';
import { CHARGING_POINTS, FORKLIFT_IDS, forkliftPose, type TwinWarehouseData } from '../lib/warehouseTwin';

export type WarehouseSelection = { kind: 'zone' | 'rack' | 'forklift' | 'dock'; id: string };
export type WarehouseCamera = 'isometric' | 'top' | 'dock';
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
    const mat=(c:number,metalness=0.12,roughness=0.7)=>new THREE.MeshStandardMaterial({color:c,metalness,roughness});
    const mats={ slab:mat(0x2b2d2a),wall:mat(0x353733),beam:mat(0x4b4e47,0.48),rack:mat(0x6b6f66,0.65),shelf:mat(0x474a44,0.5),
      carton:mat(0xb79b76),pallet:mat(0x7a6650),dock:mat(0x50544c),glass:mat(0xc2c6bc,0.6,0.15),yellow:mat(0xe3bf51),white:mat(0xe6e7e2)};
    function box(parent:THREE.Object3D, size:[number,number,number], pos:[number,number,number],material:THREE.Material, pick?:WarehouseSelection) {
      const o=new THREE.Mesh(new THREE.BoxGeometry(...size),material);o.position.set(...pos);
      if(pick)o.userData.pick=pick;parent.add(o);return o;
    }
    const pickables:THREE.Object3D[]=[];
    // Floor, perimeter, column grid, transparent roof: warehouse is visible in cutaway mode.
    box(scene,[69,0.5,48],[0,-0.26,0],mats.slab);
    const grid=new THREE.GridHelper(68,34,0x4a4d47,0x333530);grid.position.y=0.012;
    (grid.material as THREE.Material).transparent=true;(grid.material as THREE.Material).opacity=0.3;scene.add(grid);
    for(const px of [-33.6,33.6])for(const pz of [-22,22])box(scene,[0.65,8.5,0.65],[px,4.15,pz],mats.beam);
    for(const pz of [-22,22])box(scene,[68,0.42,0.5],[0,8.4,pz],mats.beam);
    for(const px of [-33.6,33.6])box(scene,[0.5,0.42,44],[px,8.4,0],mats.beam);
    box(scene,[68,3.3,0.28],[0,1.65,-22],mats.wall);
    box(scene,[0.28,3.3,44],[-33.6,1.65,0],mats.wall);
    // Right wall remains open at three vehicle loading docks; roof is toggleable.
    for(const z of [-20,-7,6,20])box(scene,[0.35,3.2,2.5],[33.6,1.6,z],mats.wall);
    const roofMaterial=new THREE.MeshStandardMaterial({color:0x9a9e94,transparent:true,opacity:0.25,metalness:0.55,roughness:0.35,depthWrite:false});
    const roof=box(scene,[68,0.25,44],[0,8.7,0],roofMaterial);roof.visible=roofRef.current;
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
      box(scene,[2.5,1.0,1.3],[-26+i*2.8,0.58,1+i*2.0],mats.beam);
    }
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
      const hit=box(g,[3.3,5.4,1.55],[0,2.7,0],new THREE.MeshBasicMaterial({transparent:true,opacity:0,depthWrite:false,colorWrite:false}),{kind:'rack',id:rack.id});
      pickables.push(hit);
      const sign=label(rack.id,rack.zone==='chilled'?'#9ED9AE':'#E6E7E2',2.5,29);
      sign.position.set(0,5.75,0);g.add(sign);
      scene.add(g);
    }
    const stamp=new THREE.Object3D();
    const putInstances=(geo:THREE.BoxGeometry,material:THREE.Material,offsetY:number,only?:'chilled'|'frozen')=>{
      const positions=only?occupiedCells.filter(p=>p.zone===only):occupiedCells;
      const mesh=new THREE.InstancedMesh(geo,material,positions.length);
      positions.forEach((p,i)=>{stamp.position.set(p.x,p.y+offsetY,p.z);stamp.rotation.set(0,0,0);stamp.updateMatrix();mesh.setMatrixAt(i,stamp.matrix);});
      mesh.instanceMatrix.needsUpdate=true;mesh.frustumCulled=false;scene.add(mesh);
    };
    putInstances(new THREE.BoxGeometry(0.86,0.12,1.04),mats.pallet,0.15);
    putInstances(new THREE.BoxGeometry(0.72,0.68,0.79),mats.carton,0.55);
    putInstances(new THREE.BoxGeometry(0.74,0.025,0.80),new THREE.MeshBasicMaterial({color:0x5cb882}),0.91,'chilled');
    putInstances(new THREE.BoxGeometry(0.74,0.025,0.80),new THREE.MeshBasicMaterial({color:0xe6e7e2}),0.91,'frozen');
    // Picking conveyor and staging pallets.
    for(let i=0;i<8;i++){
      const x=-13+i*3.4;
      box(scene,[2.85,0.56,1.7],[x,0.55,8],mats.beam);
      box(scene,[2.6,0.17,1.48],[x,0.95,8],mats.dock);
      if(i%2===0)box(scene,[1.1,0.75,1.0],[x,1.43,8],mats.carton);
    }
    for(let i=0;i<8;i++){
      const x=5+i%4*3.7,z=7+Math.floor(i/4)*4;
      box(scene,[1.55,0.19,1.35],[x,0.18,z],mats.pallet);
      box(scene,[1.33,0.85,1.15],[x,0.72,z],mats.carton);
    }
    // Three dock lanes and delivery-bay door frames, not three warehouses.
    for(let i=0;i<3;i++){
      const z=4+i*4.45;
      const plate=box(scene,[5.65,0.23,3.4],[28.2,0.22,z],mats.dock,{kind:'dock',id:`DOCK-${i+1}`});pickables.push(plate);
      box(scene,[0.26,4,3.65],[33.1,2.1,z],mat(0x575a53,0.42));
      const lane=label(`D0${i+1}`,'#D7E8DB',3.1,36);lane.position.set(30.9,4.65,z);scene.add(lane);
      for(let k=0;k<4;k++)box(scene,[0.3,0.03,0.33],[27+k*1.25,0.36,z-1.54],mats.yellow);
    }
    // Charging stations and battery panels.
    FORKLIFT_IDS.forEach((_,i)=>{
      const p=CHARGING_POINTS[i];
      box(scene,[2.8,0.1,2.5],[p.x,0.1,p.z],mat(0x5c5f58));
      box(scene,[0.7,1.75,0.42],[p.x-1.1,0.94,p.z+1.1],mat(0x4f8a5e,0.6));
    });
    // Forklift: raised forks + pallet, cab roll bar, visible wheels and steering turn.
    const actors=new Map<string,{root:THREE.Group;forks:THREE.Group;cargo:THREE.Group;wheels:THREE.Mesh[]}>();
    const tires=mat(0x202220,0,0.94);
    for(let i=0;i<3;i++){
      const id=FORKLIFT_IDS[i];
      const root=new THREE.Group();
      const frameMat=mat([0xf3bf49,0xd9dbd3,0xf39b4d][i],0.28,0.37);
      box(root,[2,0.75,1.05],[-0.2,0.68,0],frameMat);
      box(root,[0.65,0.8,0.99],[-1.01,0.88,0],mat(0x3d403a,0.25));
      for(const x of [-0.54,0.48])for(const z of [-0.43,0.43])box(root,[0.1,1.52,0.1],[x,1.72,z],mats.beam);
      box(root,[1.3,0.12,1.13],[-0.06,2.50,0],mats.beam);
      box(root,[0.18,2.8,1.35],[1.0,1.5,0],mats.beam);
      const forks=new THREE.Group();
      box(forks,[1.27,0.12,0.18],[1.66,0.05,-0.34],mats.white);
      box(forks,[1.27,0.12,0.18],[1.66,0.05,0.34],mats.white);
      const cargo=new THREE.Group();
      box(cargo,[0.97,0.13,0.95],[2.0,0.17,0],mats.pallet);
      box(cargo,[0.86,0.76,0.78],[2.0,0.62,0],mats.carton);
      forks.add(cargo);root.add(forks);
      const wheels:THREE.Mesh[]=[];
      for(const x of [-0.86,0.66])for(const z of [-0.58,0.58]){
        const wheel=new THREE.Mesh(new THREE.CylinderGeometry(0.31,0.31,0.18,14),tires);
        wheel.rotation.x=Math.PI/2;wheel.position.set(x,0.36,z);root.add(wheel);wheels.push(wheel);
      }
      const idLabel=label(id,'#f7e5a0',3.3,40);idLabel.position.set(-0.1,3.2,0);root.add(idLabel);
      const pickMesh=box(root,[2.2,2.8,1.8],[0,1.4,0],new THREE.MeshBasicMaterial({transparent:true,opacity:0,depthWrite:false,colorWrite:false}),{kind:'forklift',id});
      pickables.push(pickMesh);
      const p=CHARGING_POINTS[i];root.position.set(p.x,0.08,p.z);scene.add(root);
      actors.set(id,{root,forks,cargo,wheels});
    }
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
        else{desired.set(47,49,63);target.set(0,0,0);}
        camera.position.copy(desired);controls.target.copy(target);controls.update();
      }
      roof.visible=roofRef.current;
      const t=timeRef.current();
      actors.forEach((entry,id)=>{
        const pose=forkliftPose(id,t,data.jobs,data.racks);
        entry.root.position.set(pose.x,0.08,pose.z);
        entry.root.rotation.y=pose.heading;
        entry.forks.position.y=pose.lift;
        entry.cargo.visible=pose.carrying;
        if(pose.stage==='to_rack'||pose.stage==='to_dock'||pose.stage==='returning')
          for(const wheel of entry.wheels)wheel.rotation.z-=(Math.max(0,t-lastT))*0.08;
        entry.root.scale.setScalar(selectedRef.current?.kind==='forklift'&&selectedRef.current.id===id?1.15:1);
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
