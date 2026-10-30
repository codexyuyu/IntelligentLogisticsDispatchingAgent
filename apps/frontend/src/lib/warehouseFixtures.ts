import * as THREE from 'three';

function box(parent:THREE.Object3D,size:[number,number,number],position:[number,number,number],material:THREE.Material) {
  const mesh=new THREE.Mesh(new THREE.BoxGeometry(...size),material);mesh.position.set(...position);parent.add(mesh);return mesh;
}
function panel(text:string,colour='#bfe6d1') {
  const canvas=document.createElement('canvas');canvas.width=512;canvas.height=256;const ctx=canvas.getContext('2d')!;
  ctx.fillStyle='#182722';ctx.fillRect(0,0,512,256);ctx.fillStyle=colour;ctx.font='600 36px "Microsoft YaHei",sans-serif';
  text.split('\n').forEach((line,i)=>ctx.fillText(line,26,55+i*58));
  ctx.strokeStyle='#4b6f5a';ctx.lineWidth=2;for(let y=210;y<250;y+=10){ctx.beginPath();ctx.moveTo(26,y);ctx.lineTo(485,y);ctx.stroke();}
  const map=new THREE.CanvasTexture(canvas);map.colorSpace=THREE.SRGBColorSpace;
  return new THREE.MeshBasicMaterial({map,toneMapped:false});
}

export function createInspectionBench(steel:THREE.Material,dark:THREE.Material) {
  const root=new THREE.Group();root.name='quality-inspection-bench';
  box(root,[2.6,.12,1.1],[0,1,0],steel);
  for(const x of [-1.05,1.05])for(const z of [-.4,.4]) {
    box(root,[.08,.94,.08],[x,.5,z],steel);box(root,[.12,.04,.12],[x,.03,z],dark);
  }
  box(root,[2.3,.06,.8],[0,.34,0],steel);
  box(root,[.7,.08,.58],[-.55,1.1,0],dark);
  box(root,[.63,.035,.52],[-.55,1.16,0],steel);
  box(root,[.04,.37,.06],[-.22,1.28,-.25],steel);
  const display=box(root,[.24,.14,.06],[-.22,1.49,-.25],dark);
  const digits=new THREE.Mesh(new THREE.PlaneGeometry(.21,.1),panel('— kg'));digits.position.set(display.position.x,1.49,-.213);root.add(digits);
  box(root,[.08,.43,.08],[.7,1.23,-.28],steel);
  const monitor=box(root,[.7,.44,.08],[.7,1.62,-.28],dark);
  const screen=new THREE.Mesh(new THREE.PlaneGeometry(.61,.35),panel('QC / 质检\n演示工位\n扫码 · 复核'));screen.position.set(monitor.position.x,1.62,-.233);root.add(screen);
  box(root,[.55,.035,.22],[.66,1.085,.23],dark);
  for(let key=0;key<8;key++)box(root,[.035,.015,.13],[.43+key*.058,1.11,.23],steel);
  box(root,[.13,.06,.24],[1.05,1.09,.1],dark);
  const scanner=box(root,[.09,.2,.1],[1.05,1.2,.1],dark);scanner.rotation.x=-.25;
  box(root,[.055,.03,.1],[1.05,1.3,.095],new THREE.MeshStandardMaterial({color:0xb94434,emissive:0x46180c}));
  const control=box(root,[.5,.24,.34],[0,.54,0],dark);control.name='scale-control-box';
  return root;
}

export function createEvaporator(steel:THREE.Material,white:THREE.Material,dark:THREE.Material) {
  const root=new THREE.Group();root.name='cold-room-evaporator';
  // Powder-coated housing with recessed fan openings and a finned rear coil.
  box(root,[4.8,.09,1.12],[0,.55,-.1],white);
  box(root,[4.8,.09,1.12],[0,-.55,-.1],white);
  for(const x of [-2.34,2.34])box(root,[.12,1.1,1.12],[x,0,-.1],white);
  box(root,[.62,1.05,.1],[0,0,.45],white);
  for(const x of [-2.12,2.12])box(root,[.36,1.05,.1],[x,0,.45],white);
  for(const x of [-1.2,1.2]) {
    const face=new THREE.Shape();face.moveTo(-.92,-.52);face.lineTo(.92,-.52);face.lineTo(.92,.52);face.lineTo(-.92,.52);face.closePath();
    const hole=new THREE.Path();hole.absarc(0,0,.435,0,Math.PI*2,true);face.holes.push(hole);
    const plate=new THREE.Mesh(new THREE.ShapeGeometry(face),white);plate.position.set(x,0,.46);root.add(plate);
  }
  box(root,[4.45,.93,.08],[0,0,-.54],dark);
  const copper=new THREE.MeshStandardMaterial({color:0xb9794b,metalness:.75,roughness:.35});
  function pipe(points:number[][],radius:number,material:THREE.Material) {
    const curve=new THREE.CatmullRomCurve3(points.map(p=>new THREE.Vector3(...p as [number,number,number])));
    const mesh=new THREE.Mesh(new THREE.TubeGeometry(curve,24,radius,8,false),material);root.add(mesh);
  }
  pipe([[2.4,.28,-.2],[2.7,.28,-.2],[2.8,.5,-.3],[2.8,.9,-.65]],.045,copper);
  pipe([[2.4,-.12,-.25],[2.65,-.12,-.25],[2.8,.05,-.45],[2.8,.9,-.9]],.075,dark);
  box(root,[.28,.48,.45],[2.5,-.15,.08],white);
  for(const x of [-2.25,2.25])for(const y of [-.43,.43]) {
    const screw=new THREE.Mesh(new THREE.SphereGeometry(.025,6,4),steel);screw.position.set(x,y,.51);root.add(screw);
  }
  const badge=new THREE.Mesh(new THREE.PlaneGeometry(.55,.25),panel('COLDLINE\nDEMO UNIT'));
  badge.position.set(0,.14,.515);root.add(badge);
  // Removable tray with raised rim, slope and connected condensate drain.
  const tray=box(root,[4.7,.12,1.1],[0,-.64,-.04],white);tray.rotation.z=.018;
  box(root,[4.8,.13,.04],[0,-.57,.53],white);
  pipe([[-2.15,-.69,0],[-2.15,-1.15,0],[-1.95,-1.35,0],[-1.75,-1.15,0],[-1.75,-1.02,-.5],[-1.75,-1.02,-.85]],.04,white);
  box(root,[4.85,.12,.96],[0,-.63,.04],steel);
  for(let fin=0;fin<65;fin++)box(root,[.012,.9,.7],[-2.2+fin*.069,0,-.18],steel);
  const fans:THREE.Group[]=[];
  for(const x of [-1.2,1.2]) {
    const ring=new THREE.Mesh(new THREE.TorusGeometry(.43,.035,8,32),steel);ring.position.set(x,0,.46);root.add(ring);
    const rotor=new THREE.Group();rotor.position.set(x,0,.49);
    const hub=new THREE.Mesh(new THREE.CylinderGeometry(.12,.12,.08,16),dark);hub.rotation.x=Math.PI/2;rotor.add(hub);
    for(let blade=0;blade<5;blade++) {
      const a=blade*Math.PI*2/5;
      const vane=box(rotor,[.36,.13,.03],[Math.cos(a)*.2,Math.sin(a)*.2,0],dark);vane.rotation.z=a+.3;
    }
    root.add(rotor);fans.push(rotor);
    for(let wire=0;wire<6;wire++) {
      const guard=new THREE.Mesh(new THREE.TorusGeometry(.14+wire*.055,.006,4,32),steel);guard.position.set(x,0,.52);root.add(guard);
    }
    for(const a of [0,Math.PI/2]){const spoke=box(root,[.85,.012,.015],[x,0,.525],steel);spoke.rotation.z=a;}
  }
  // Bracket hangers, refrigerant line and a drain trap.
  for(const x of [-2.08,2.08]){box(root,[.09,2.85,.09],[x,1.98,-.2],steel);box(root,[.38,.06,.48],[x,.62,-.2],steel);}

  return {root,fans};
}

export function createReceivingDoor(steel:THREE.Material,dark:THREE.Material,white:THREE.Material) {
  const root=new THREE.Group();root.name='receiving-roller-shutter';
  for(const x of [-2.8,2.8])box(root,[.23,4.6,.22],[x,2.3,0],steel);
  box(root,[5.8,.35,.35],[0,4.65,0],white);
  // Raised shutter leaves clearance above the conveyor and incoming cartons.
  for(let slat=0;slat<7;slat++)box(root,[5.35,.2,.075],[0,2.8+slat*.235,.05],slat%2?white:steel);
  for(const x of [-2.55,2.55])box(root,[.18,.8,.28],[x,.48,.22],dark);
  box(root,[.75,.18,.1],[0,2.9,.15],dark);
  box(root,[.25,.45,.12],[3.15,1.35,.1],white);
  const sign=new THREE.Mesh(new THREE.PlaneGeometry(2.2,.6),panel('收货 / RECEIVING'));sign.position.set(0,5.18,.05);root.add(sign);
  return root;
}
