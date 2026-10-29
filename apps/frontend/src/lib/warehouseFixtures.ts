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
  box(root,[4.8,1.15,.85],[0,0,0],white);
  box(root,[4.85,.12,.96],[0,-.63,.04],steel);
  for(let fin=0;fin<25;fin++)box(root,[.05,.84,.15],[-2.2+fin*.183,0,-.48],steel);
  const fans:THREE.Group[]=[];
  for(const x of [-1.2,1.2]) {
    const ring=new THREE.Mesh(new THREE.TorusGeometry(.43,.035,8,32),steel);ring.position.set(x,0,.46);root.add(ring);
    const rotor=new THREE.Group();rotor.position.set(x,0,.45);
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
  for(const x of [-2.08,2.08])box(root,[.09,.8,.09],[x,.88,-.2],steel);
  box(root,[.08,.08,1.2],[2.45,.2,-.5],steel);
  box(root,[.06,1.45,.06],[-2.3,-1.18,-.25],white);
  box(root,[.3,.06,.06],[-2.17,-1.9,-.25],white);
  return {root,fans};
}

export function createReceivingDoor(steel:THREE.Material,dark:THREE.Material,white:THREE.Material) {
  const root=new THREE.Group();root.name='receiving-roller-shutter';
  for(const x of [-2.8,2.8])box(root,[.23,4.6,.22],[x,2.3,0],steel);
  box(root,[5.8,.35,.35],[0,4.65,0],white);
  for(let slat=0;slat<18;slat++)box(root,[5.35,.2,.075],[0,.18+slat*.235,.05],slat%2?white:steel);
  for(const x of [-2.55,2.55])box(root,[.18,.8,.28],[x,.48,.22],dark);
  box(root,[.75,.18,.1],[0,.7,.15],dark);
  box(root,[.25,.45,.12],[3.15,1.35,.1],white);
  const sign=new THREE.Mesh(new THREE.PlaneGeometry(2.2,.6),panel('收货 / RECEIVING'));sign.position.set(0,5.18,.05);root.add(sign);
  return root;
}
