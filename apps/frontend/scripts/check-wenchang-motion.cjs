const fs=require('fs');
const ts=require('typescript');
const path=require('node:path').join(__dirname, '../src/lib/liuzhouDemoMap.ts');
const input=fs.readFileSync(path,'utf8');
const compiled=ts.transpileModule(input,{compilerOptions:{module:ts.ModuleKind.CommonJS,target:ts.ScriptTarget.ES2022}}).outputText;
const m={exports:{}};new Function('module','exports','require',compiled)(m,m.exports,require);
const {buildWenchangFourTruckShowcase,createDemoNodes,buildDemoMotion,sampleDemoMotion,visualMarkerOffset,assertDemoRouteIntegrity}=m.exports;
const routes=buildWenchangFourTruckShowcase(2620);
const nodes=createDemoNodes(routes);
let maxStep=0,maxBoundary=0,maxOffset=0;
for(let j=0;j<routes.length;j++){
 const r=routes[j],motion=buildDemoMotion(r,nodes);
 if(!assertDemoRouteIntegrity(r,motion))throw Error('integrity '+j);
 for(const leg of motion.legs){
   const at=sampleDemoMotion(motion,leg.toS),after=sampleDemoMotion(motion,leg.toS+.001);
   const delta=Math.hypot((at.point[0]-after.point[0])*111000,(at.point[1]-after.point[1])*101000); maxBoundary=Math.max(maxBoundary,delta);
 }
 for(let t=0;t<2620;t+=.05){
  const a=sampleDemoMotion(motion,t),b=sampleDemoMotion(motion,t+.05);
  let delta=Math.hypot((a.point[0]-b.point[0])*111000,(a.point[1]-b.point[1])*101000);
  maxStep=Math.max(maxStep,delta);
  const o=visualMarkerOffset(motion,t,j,4),p=visualMarkerOffset(motion,t+.05,j,4);
  maxOffset=Math.max(maxOffset,Math.hypot(o.x-p.x,o.y-p.y));
  if(!Number.isFinite(delta)||!Number.isFinite(o.x)||!Number.isFinite(o.y))throw Error('nonfinite '+j+' '+t);
 }
}
console.log('Wenchang 2D map playback PASS', JSON.stringify({vehicles:routes.length, samples:4*2620*20, max50msTravelMetres:maxStep,maxBoundaryDeltaM:maxBoundary,max50msOffsetPx:maxOffset},null,2));
if(maxStep>60||maxBoundary>1||maxOffset>1)process.exit(1);

const component=require('node:fs').readFileSync(require('node:path').join(__dirname,'../src/components/DigitalTwinMap2D.tsx'),'utf8');
if (/\bmarker\s*\.\s*setIcon\s*\(/.test(component)) throw Error('Do not replace marker DOM icons on every frame');
if (!component.includes('window.requestAnimationFrame(render)')) throw Error('RAF interpolation missing');
