import * as THREE from 'three';

// Locally generated PBR colour maps: repeatable paper fibres, folds, tape and labels.
// No remote texture fetches; all cartons share the same six materials.
function texture(draw: (ctx: CanvasRenderingContext2D) => void) {
  const canvas = document.createElement('canvas'); canvas.width = canvas.height = 512;
  const ctx = canvas.getContext('2d')!; draw(ctx);
  const map = new THREE.CanvasTexture(canvas);
  map.colorSpace = THREE.SRGBColorSpace;
  map.anisotropy = 4;
  return map;
}

function cardboard(top: boolean) {
  return texture(ctx => {
    ctx.fillStyle = '#b99261'; ctx.fillRect(0,0,512,512);
    let random = 713;
    const next = () => { random = (random * 1664525 + 1013904223) >>> 0; return random / 4294967296; };
    for(let i=0;i<19000;i++) {
      const tone = next() > .5 ? '255,236,199' : '82,52,28';
      ctx.fillStyle = `rgba(${tone},${.035+next()*.1})`;
      ctx.fillRect(next()*512,next()*512,1+next()*3,.5+next());
    }
    ctx.strokeStyle='#80603c';ctx.lineWidth=3;ctx.strokeRect(6,6,500,500);
    ctx.strokeStyle='rgba(239,209,157,.55)';ctx.lineWidth=2;ctx.strokeRect(10,10,492,492);
    ctx.fillStyle='rgba(222,180,111,.7)';
    if(top) {
      ctx.fillRect(218,0,76,512);ctx.fillRect(0,234,512,44);
      ctx.strokeStyle='rgba(89,65,34,.45)';ctx.lineWidth=2;
      ctx.beginPath();ctx.moveTo(256,0);ctx.lineTo(256,512);ctx.stroke();
      ctx.font='bold 16px sans-serif';ctx.fillStyle='#725634';
      ctx.save();ctx.translate(252,55);ctx.rotate(Math.PI/2);ctx.fillText('COLD CHAIN  •  SEALED',0,0);ctx.restore();
    } else {
      ctx.fillRect(0,0,512,36);ctx.fillRect(0,482,512,30);
      ctx.fillStyle='#eee9db';ctx.fillRect(42,110,286,245);
      ctx.fillStyle='#28302c';ctx.font='bold 27px sans-serif';ctx.fillText('COLD CHAIN',58,148);
      ctx.font='17px monospace';ctx.fillText('FRESH PRODUCE',58,178);
      ctx.fillText('LOT 26-1029',58,205);
      ctx.fillText('KEEP UPRIGHT / DRY',58,232);
      for(let x=60;x<299;) { const width=1+Math.floor(next()*4);ctx.fillRect(x,257,width,57);x+=width+1+Math.floor(next()*3); }
      ctx.font='14px monospace';ctx.fillText('8  692026  102908',68,337);
      ctx.strokeStyle='#3f493d';ctx.lineWidth=7;
      for(const x of [379,440]) {
        ctx.beginPath();ctx.moveTo(x,233);ctx.lineTo(x,161);ctx.moveTo(x-15,178);ctx.lineTo(x,161);ctx.lineTo(x+15,178);ctx.stroke();
      }
      ctx.lineWidth=4;ctx.strokeRect(354,143,117,111);
      ctx.font='bold 19px sans-serif';ctx.fillText('HANDLE',357,303);ctx.fillText('WITH CARE',346,329);
    }
    // Soft wear along the cut edges without making the texture glossy.
    const edge=ctx.createLinearGradient(0,0,28,0);edge.addColorStop(0,'rgba(60,35,16,.22)');edge.addColorStop(1,'rgba(60,35,16,0)');
    ctx.fillStyle=edge;ctx.fillRect(0,0,28,512);
  });
}

export function cartonMaterials(): THREE.Material[] {
  const side = new THREE.MeshStandardMaterial({map:cardboard(false),roughness:.96,metalness:0});
  const top = new THREE.MeshStandardMaterial({map:cardboard(true),roughness:.84,metalness:0});
  return [side,side,top,top,side,side];
}

export function palletMaterial() {
  const map=texture(ctx=>{
    ctx.fillStyle='#8e7350';ctx.fillRect(0,0,512,512);
    for(let y=0;y<512;y+=3) {
      ctx.strokeStyle=`rgba(51,32,17,${.07+(y%19)/160})`;ctx.lineWidth=1;
      ctx.beginPath();ctx.moveTo(0,y);ctx.bezierCurveTo(140,y-8,350,y+7,512,y-3);ctx.stroke();
    }
    for(let y=0;y<512;y+=102) {ctx.fillStyle='#4d3e2c';ctx.fillRect(0,y,512,4);}
    ctx.fillStyle='#3f382e';for(const x of [30,480])for(const y of [35,150,250,350,470]){ctx.beginPath();ctx.arc(x,y,3,0,Math.PI*2);ctx.fill();}
  });
  return new THREE.MeshStandardMaterial({map,roughness:.94,metalness:0});
}

export function insulatedPanelMaterial() {
  const map=texture(ctx=>{
    ctx.fillStyle='#d9ded8';ctx.fillRect(0,0,512,512);
    for(let x=0;x<512;x+=64){ctx.fillStyle='#9ea9a2';ctx.fillRect(x,0,3,512);ctx.fillStyle='#f1f3ec';ctx.fillRect(x+4,0,2,512);}
    ctx.fillStyle='#acb5ae';ctx.fillRect(0,500,512,12);
  });
  return new THREE.MeshStandardMaterial({map,roughness:.62,metalness:.25});
}
