const fs=require('node:fs');
const crypto=require('node:crypto');
const path=require('node:path');
const cacache=require('C:/Program Files/nodejs/node_modules/npm/node_modules/cacache');
const root='D:/Agent/DeepSeekHarness/IntelligentLogisticsDispatchingAgent';
const temp='C:/Users/30382/AppData/Local/Temp/IntelligentLogisticsDispatchingAgent-n05-r03-env';
const lock=JSON.parse(fs.readFileSync(path.join(root,'package-lock.json'),'utf8'));
(async()=>{
 const cases=[];
 for(const cache of ['C:/Users/30382/AppData/Local/Temp/IntelligentLogisticsDispatchingAgent-n05-r02-impact/npm-cache/_cacache',path.join(temp,'npm-cache/_cacache')]){
  const rows=[];
  for(const [name,pkg] of Object.entries(lock.packages)){
   if(!pkg.resolved?.startsWith('https://registry.npmjs.org/')||!pkg.integrity)continue;
   const result=await cacache.get(cache,'make-fetch-happen:request-cache:'+pkg.resolved);
   const integrity='sha512-'+crypto.createHash('sha512').update(result.data).digest('base64');
   if(integrity!==pkg.integrity)throw new Error('frozen lock integrity mismatch '+name);
   rows.push({package:name,integrity,bytes:result.data.length});
  }
  if(rows.length!==3)throw new Error('three tarballs required');
  cases.push({cache,packages:rows});
 }
 console.log(JSON.stringify({passed:true,network_requests:0,cache_writes:0,verified_at:new Date().toISOString(),cases}));
})().catch(e=>{console.error(e.stack);process.exitCode=1;});
