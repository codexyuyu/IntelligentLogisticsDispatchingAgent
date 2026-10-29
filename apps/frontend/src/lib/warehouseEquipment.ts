import * as THREE from 'three';
import { RoundedBoxGeometry } from 'three/examples/jsm/geometries/RoundedBoxGeometry.js';

type Material = THREE.Material | THREE.Material[];
type EquipmentMaterials = { steel: THREE.Material; dark: THREE.Material; pallet: THREE.Material; cartons: THREE.Material[] };

function box(parent: THREE.Object3D, size: [number,number,number], position: [number,number,number], material: Material, radius=0) {
  const geometry=radius ? new RoundedBoxGeometry(...size,2,radius) : new THREE.BoxGeometry(...size);
  const mesh=new THREE.Mesh(geometry,material);mesh.position.set(...position);parent.add(mesh);return mesh;
}
function rod(parent:THREE.Object3D,a:[number,number,number],b:[number,number,number],radius:number,material:THREE.Material) {
  const start=new THREE.Vector3(...a),end=new THREE.Vector3(...b),delta=end.clone().sub(start);
  const mesh=new THREE.Mesh(new THREE.CylinderGeometry(radius,radius,delta.length(),10),material);
  mesh.position.copy(start).add(end).multiplyScalar(.5);
  mesh.quaternion.setFromUnitVectors(new THREE.Vector3(0,1,0),delta.normalize());parent.add(mesh);return mesh;
}
function cable(parent:THREE.Object3D,points:[number,number,number][],radius:number,material:THREE.Material) {
  const curve=new THREE.CatmullRomCurve3(points.map(p=>new THREE.Vector3(...p)));
  const mesh=new THREE.Mesh(new THREE.TubeGeometry(curve,32,radius,7,false),material);parent.add(mesh);return mesh;
}
function plate(parent:THREE.Object3D,text:string,size:[number,number],position:[number,number,number],facing:'front'|'side'='front',colour='#dbe6df',background='#202a27') {
  const canvas=document.createElement('canvas');canvas.width=512;canvas.height=256;
  const ctx=canvas.getContext('2d')!;
  ctx.fillStyle=background;ctx.fillRect(0,0,512,256);
  ctx.fillStyle=colour;ctx.textAlign='center';ctx.textBaseline='middle';
  const lines=text.split('\n');ctx.font=`600 ${lines.length>2?36:48}px "Microsoft YaHei",sans-serif`;
  lines.forEach((line,i)=>ctx.fillText(line,256,128+(i-(lines.length-1)/2)*62,470));
  const map=new THREE.CanvasTexture(canvas);map.colorSpace=THREE.SRGBColorSpace;
  const material=new THREE.MeshBasicMaterial({map,toneMapped:false});
  const mesh=new THREE.Mesh(new THREE.PlaneGeometry(...size),material);mesh.position.set(...position);
  mesh.rotation.y=facing==='front'?Math.PI/2:0;parent.add(mesh);return mesh;
}

export function createDetailedForklift(index:number,materials:EquipmentMaterials) {
  const root=new THREE.Group();root.name=`forklift-${index+1}`;
  const paint=new THREE.MeshStandardMaterial({color:[0xeebd43,0xd2d6cc,0xf3953b][index%3],metalness:.25,roughness:.4});
  const black=new THREE.MeshStandardMaterial({color:0x222824,roughness:.85});
  const tyre=new THREE.MeshStandardMaterial({color:0x151a17,roughness:.98});
  const light=new THREE.MeshStandardMaterial({color:0xfff3cb,emissive:0xffda87,emissiveIntensity:.5});
  const red=new THREE.MeshStandardMaterial({color:0xb73227,emissive:0x50140d,emissiveIntensity:.4});
  const amber=new THREE.MeshStandardMaterial({color:0xffb12e,emissive:0xc8780e,emissiveIntensity:.5});

  // Rounded electric counterweight body, separate battery cover and service seams.
  box(root,[1.95,.39,1.08],[-.18,.48,0],materials.dark,.09);
  box(root,[1.2,.7,1.12],[-.67,.87,0],paint,.13);
  box(root,[.94,.09,1.02],[-.69,1.245,0],black,.025);
  box(root,[.34,.49,1.1],[.43,.72,0],paint,.055);
  box(root,[.11,.25,1.09],[-1.31,.55,0],black,.025);
  for(const side of [-1,1]) {
    for(let v=0;v<7;v++)box(root,[.3,.025,.018],[-.88,.79+v*.05,side*.565],black);
    box(root,[.6,.04,.035],[-.35,.63,side*.57],materials.steel);
    box(root,[.46,.06,.15],[.15,.37,side*.59],materials.steel);
    for(let tread=0;tread<5;tread++)box(root,[.025,.018,.15],[.0+tread*.07,.409,side*.59],black);
    box(root,[.09,.14,.21],[-1.372,.97,side*.36],red,.02);
    const name=plate(root,`FK-0${index+1}\nELECTRIC`,[.59,.26],[-.61,1.02,side*.574],'side','#292b22','#e7cd8c');
    if(side<0)name.rotation.y=Math.PI;
  }
  // Enclosed cold-store cab: glazing, seals, wiper and roof insulation.
  const glass=new THREE.MeshPhysicalMaterial({color:0xb6d9df,transparent:true,opacity:.22,roughness:.12,metalness:0,depthWrite:false});
  box(root,[.025,1.12,.94],[.59,1.88,0],glass);
  box(root,[.025,1.1,.94],[-.68,1.88,0],glass);
  for(const side of [-1,1]) {
    box(root,[1.16,1.13,.018],[-.04,1.88,side*.52],glass);
    box(root,[.24,.035,.04],[-.3,1.44,side*.55],black,.01);
    rod(root,[-.64,1.3,side*.52],[.55,1.3,side*.52],.025,black);
  }
  rod(root,[.615,1.35,-.3],[.615,2.15,.12],.014,black);
  box(root,[1.38,.065,1.05],[-.05,2.57,0],paint,.025);
  // Sculpted seat, backrest, arm supports and an accessible footwell.
  box(root,[.72,.11,.83],[.16,.88,0],black,.025);
  box(root,[.5,.17,.57],[-.3,1.12,0],black,.06);
  const back=box(root,[.15,.61,.59],[-.57,1.43,0],black,.05);back.rotation.z=-.12;
  for(const side of [-1,1])rod(root,[-.48,1.32,side*.32],[-.04,1.32,side*.32],.035,black);
  rod(root,[.18,1.0,0],[.4,1.49,0],.033,materials.steel);
  const steering=new THREE.Group();steering.position.set(.4,1.49,0);
  steering.quaternion.setFromUnitVectors(new THREE.Vector3(0,0,1),new THREE.Vector3(.22,.49,0).normalize());
  const ring=new THREE.Mesh(new THREE.TorusGeometry(.16,.022,8,24),black);steering.add(ring);
  for(let spoke=0;spoke<3;spoke++){const a=spoke*Math.PI*2/3;rod(steering,[0,0,0],[Math.cos(a)*.145,Math.sin(a)*.145,0],.012,materials.steel);}
  root.add(steering);
  box(root,[.2,.17,.3],[.4,1.28,-.35],black,.015);
  for(let lever=0;lever<3;lever++){
    rod(root,[.35+lever*.055,1.32,-.36],[.4+lever*.055,1.57,-.36],.014,materials.steel);
    const knob=new THREE.Mesh(new THREE.SphereGeometry(.033,8,6),black);knob.position.set(.4+lever*.055,1.57,-.36);root.add(knob);
  }
  // Overhead safety cage with cross-slats rather than a solid oversized roof.
  for(const x of [-.67,.58])for(const z of [-.52,.52])rod(root,[x,1.0,z],[x,2.48,z],.047,materials.dark);
  for(const z of [-.56,.56])box(root,[1.47,.1,.1],[-.05,2.5,z],materials.dark,.02);
  for(let slat=0;slat<7;slat++)box(root,[.055,.065,1.04],[-.65+slat*.2,2.52,0],materials.dark);
  for(const side of [-1,1]) {
    box(root,[.11,.13,.22],[.68,2.34,side*.42],black,.02);
    box(root,[.018,.09,.16],[.744,2.34,side*.42],light,.005);
    rod(root,[.57,2.19,side*.5],[.66,2.23,side*.69],.018,materials.steel);
    box(root,[.065,.18,.15],[.66,2.23,side*.69],black,.02);
  }
  const beacon=new THREE.Mesh(new THREE.CylinderGeometry(.075,.09,.14,16),amber);beacon.position.set(-.48,2.65,0);root.add(beacon);
  box(root,[.24,.04,.26],[-.48,2.555,0],black,.02);
  // Twin channel mast, hydraulic pistons, chain runs and a moving carriage.
  for(const side of [-1,1]) {
    box(root,[.12,2.76,.15],[1.02,1.5,side*.54],materials.dark);
    box(root,[.035,2.6,.085],[1.1,1.5,side*.54],materials.steel);
    rod(root,[.89,.45,side*.38],[.89,1.56,side*.38],.057,materials.dark);
    rod(root,[.89,1.5,side*.38],[.89,2.62,side*.38],.028,materials.steel);
    for(let link=0;link<17;link++)box(root,[.035,.065,.05],[1.13,.47+link*.12,side*.43],black);
  }
  box(root,[.15,.12,1.2],[1.02,2.85,0],materials.dark);
  const forks=new THREE.Group();forks.name='fork-carriage';root.add(forks);
  box(forks,[.15,.16,1.2],[1.17,.21,0],materials.steel);
  box(forks,[.1,.1,1.12],[1.18,1.03,0],materials.dark);
  for(const z of [-.52,-.26,0,.26,.52])box(forks,[.075,.87,.04],[1.18,.63,z],materials.dark);
  for(const side of [-1,1]) {
    box(forks,[.12,.55,.16],[1.21,.29,side*.34],materials.steel);
    box(forks,[1.15,.085,.16],[1.76,.045,side*.34],materials.steel,.018);
    const tip=box(forks,[.17,.048,.16],[2.31,.027,side*.34],materials.steel,.01);tip.rotation.z=-.05;
  }
  cable(root,[[.75,.58,-.32],[.71,1.75,-.32],[.97,2.45,-.32],[1.08,1.6,-.32]],.018,black);
  const cargo=new THREE.Group();cargo.name='carried-cargo';
  box(cargo,[.97,.13,.95],[2,.17,0],materials.pallet);
  box(cargo,[.86,.76,.78],[2,.62,0],materials.cartons);forks.add(cargo);
  // Axle-aligned wheel groups allow tread, hub and bolts to rotate together.
  const wheels:THREE.Group[]=[];
  for(const x of [-.86,.66])for(const side of [-1,1]) {
    const wheel=new THREE.Group();wheel.position.set(x,.36,side*.57);
    const tire=new THREE.Mesh(new THREE.CylinderGeometry(.31,.31,.21,24),tyre);tire.rotation.x=Math.PI/2;wheel.add(tire);
    for(let tread=0;tread<20;tread++) {
      const angle=tread*Math.PI/10;
      const groove=box(wheel,[.035,.035,.215],[Math.cos(angle)*.304,Math.sin(angle)*.304,0],black);
      groove.rotation.z=angle;
    }
    const hub=new THREE.Mesh(new THREE.CylinderGeometry(.17,.17,.225,20),materials.steel);hub.rotation.x=Math.PI/2;wheel.add(hub);
    for(let bolt=0;bolt<5;bolt++) {
      const a=bolt*Math.PI*2/5;
      const screw=new THREE.Mesh(new THREE.CylinderGeometry(.017,.017,.025,6),black);
      screw.rotation.x=Math.PI/2;screw.position.set(Math.cos(a)*.105,Math.sin(a)*.105,side*.125);wheel.add(screw);
    }
    root.add(wheel);wheels.push(wheel);
  }
  // Rear charging inlet and a recessed port cover.
  box(root,[.02,.2,.22],[-1.376,.91,0],materials.steel,.01);
  box(root,[.027,.13,.15],[-1.39,.91,0],black,.015);
  return {root,forks,cargo,wheels,amber};
}

export function createChargingStation(index:number,steel:THREE.Material,dark:THREE.Material) {
  const root=new THREE.Group();root.name=`charger-${index+1}`;
  const body=new THREE.MeshStandardMaterial({color:0xd3d8d0,metalness:.32,roughness:.47});
  const green=new THREE.MeshStandardMaterial({color:0x466c52,metalness:.24,roughness:.46});
  const black=new THREE.MeshStandardMaterial({color:0x171e1b,roughness:.94});
  const yellow=new THREE.MeshStandardMaterial({color:0xdcb64d,metalness:.16,roughness:.63});
  const status=new THREE.MeshStandardMaterial({color:0x69c97c,emissive:0x4aaa5e,emissiveIntensity:.7});
  box(root,[.98,.16,.86],[0,.08,0],steel,.04);
  const cabinet=box(root,[.78,1.95,.65],[0,1.12,0],body,.065);
  box(root,[.83,.13,.7],[0,2.1,0],green,.025);
  box(root,[.81,.3,.68],[0,.3,0],green,.025);
  box(root,[.025,1.52,.56],[.401,1.14,0],dark,.015);
  box(root,[.03,.46,.46],[.422,1.63,0],black,.015);
  const screen=plate(root,'待机\n演示设备',[.37,.33],[.442,1.65,0]);
  const chargingScreen=plate(root,'充电中\n演示设备',[.37,.33],[.444,1.65,0],'front','#b6f1c3');chargingScreen.visible=false;
  plate(root,`CH-0${index+1}\n电动叉车充电桩`,[.49,.24],[.443,1.25,0],'front','#e2e7dd','#3d5146');
  for(let vent=0;vent<8;vent++)box(root,[.022,.027,.4],[.44,.52+vent*.05,0],black);
  for(const side of [-1,1])for(let vent=0;vent<6;vent++)box(root,[.42,.025,.018],[0,1.05+vent*.055,side*.333],dark);
  box(root,[.04,.14,.035],[.45,1.02,-.2],steel,.008);
  for(const y of [.41,1.95])for(const z of [-.25,.25]) {
    const screw=new THREE.Mesh(new THREE.SphereGeometry(.018,6,4),steel);screw.position.set(.44,y,z);root.add(screw);
  }
  const stop=new THREE.Mesh(new THREE.CylinderGeometry(.065,.065,.05,16),new THREE.MeshStandardMaterial({color:0xbf3b2e,roughness:.6}));
  stop.rotation.z=Math.PI/2;stop.position.set(.455,1.08,.13);root.add(stop);
  const indicator=new THREE.Mesh(new THREE.CylinderGeometry(.04,.04,.025,12),status);
  indicator.rotation.z=Math.PI/2;indicator.position.set(.455,1.08,-.08);root.add(indicator);
  box(root,[.16,.08,.19],[.19,2.2,0],black,.015);
  const topLight=new THREE.Mesh(new THREE.CylinderGeometry(.045,.045,.17,12),status);topLight.position.set(.19,2.31,0);root.add(topLight);
  // A stowed cable loop remains visible when the truck is away.
  cable(root,[[.02,1.7,.37],[.06,1.3,.58],[.05,.6,.61],[.12,.41,.5],[.3,.7,.45],[.32,1.25,.4]],.035,black);
  box(root,[.09,.25,.1],[.32,1.35,.4],black,.025);
  box(root,[.12,.08,.13],[.32,1.49,.4],green,.02);
  // At home, the active lead reaches the forklift's rear inlet exactly.
  const lead=new THREE.Group();lead.name='connected-charge-lead';
  cable(lead,[[.43,1.05,.23],[.55,.4,.27],[.7,.25,.15],[.86,.91,0]],.034,black);
  box(lead,[.14,.1,.14],[.86,.91,0],black,.015);root.add(lead);
  for(const side of [-1,1]) {
    rod(root,[.64,.1,side*.55],[.64,.66,side*.55],.065,yellow);
    rod(root,[.64,.29,side*.55],[.64,.4,side*.55],.068,black);
  }
  return {root,cabinet,lead,status,screen,chargingScreen};
}
